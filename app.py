from datetime import date, datetime
from functools import wraps
from pathlib import Path

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import func

from config import Config
from extensions import db
from models import (
    Aluno, Aula, Disciplina, Frequencia, Matricula, Professor, ProfessorDisciplina,
    Turma, Usuario,
)

csrf = CSRFProtect()
SITUACOES = {"presente", "ausente", "justificada"}
LIMITE_ATENCAO = 80
LIMITE_CRITICO = 75


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(app.root_path, "database").mkdir(parents=True, exist_ok=True)
    db.init_app(app)
    csrf.init_app(app)

    @app.context_processor
    def dados_comuns():
        return {
            "usuario_logado": Usuario.query.get(session.get("usuario_id")) if session.get("usuario_id") else None,
            "now": datetime.now(),
            "status_frequencia": status_frequencia,
            "aluno_matriculas": lambda aluno_id: Matricula.query.filter_by(aluno_id=aluno_id, ativa=True).all(),
        }

    def login_obrigatorio(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            usuario = Usuario.query.get(session.get("usuario_id")) if session.get("usuario_id") else None
            if not usuario or not usuario.ativo:
                session.clear()
                flash("Faça login para continuar.", "erro")
                return redirect(url_for("login"))
            return view(*args, **kwargs)
        return wrapper

    def exige_perfil(*perfis):
        def decorator(view):
            @wraps(view)
            @login_obrigatorio
            def wrapper(*args, **kwargs):
                usuario = Usuario.query.get(session["usuario_id"])
                if usuario.perfil not in perfis:
                    abort(403)
                return view(*args, **kwargs)
            return wrapper
        return decorator

    def calcular_frequencia(aluno_id, professor_disciplina_id=None):
        consulta = db.session.query(Frequencia).join(Aula).filter(
            Frequencia.aluno_id == aluno_id, Aula.chamada_salva.is_(True)
        )
        if professor_disciplina_id:
            consulta = consulta.filter(Aula.professor_disciplina_id == professor_disciplina_id)
        registros = consulta.all()
        total = len(registros)
        presentes = sum(1 for item in registros if item.situacao == "presente")
        justificadas = sum(1 for item in registros if item.situacao == "justificada")
        percentual = round(presentes / total * 100, 1) if total else None
        return {"total": total, "presentes": presentes, "faltas": total - presentes, "justificadas": justificadas, "percentual": percentual}

    def status_frequencia(percentual):
        if percentual is None:
            return "Sem aulas"
        if percentual < LIMITE_CRITICO:
            return "Alerta — frequência crítica"
        if percentual <= LIMITE_ATENCAO:
            return "Atenção — frequência baixa"
        return "Situação normal"

    @app.get("/")
    def inicio():
        return redirect(url_for("painel")) if session.get("usuario_id") else redirect(url_for("login"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            senha = request.form.get("senha", "")
            usuario = Usuario.query.filter(func.lower(Usuario.email) == email).first()
            if usuario and usuario.ativo and usuario.verificar_senha(senha):
                session.clear()
                session["usuario_id"] = usuario.id
                return redirect(url_for("painel"))
            flash("E-mail ou senha inválidos.", "erro")
        return render_template("login.html")

    @app.post("/sair")
    @login_obrigatorio
    def sair():
        session.clear()
        return redirect(url_for("login"))

    @app.get("/painel")
    @login_obrigatorio
    def painel():
        usuario = Usuario.query.get(session["usuario_id"])
        if usuario.perfil == "administrador":
            alunos = Aluno.query.count()
            professores = Professor.query.count()
            turmas = Turma.query.count()
            disciplinas = Disciplina.query.count()
            frequencias = Frequencia.query.join(Aula).filter(Aula.chamada_salva.is_(True)).all()
            media = round(sum(1 for f in frequencias if f.situacao == "presente") / len(frequencias) * 100, 1) if frequencias else None
            resumo = {"alunos": alunos, "professores": professores, "turmas": turmas, "disciplinas": disciplinas, "media": media}
            abaixo_80 = abaixo_75 = 0
            for aluno in Aluno.query.all():
                percentual = calcular_frequencia(aluno.id)["percentual"]
                if percentual is not None and percentual < LIMITE_ATENCAO:
                    abaixo_80 += 1
                if percentual is not None and percentual < LIMITE_CRITICO:
                    abaixo_75 += 1
            return render_template("admin.html", resumo=resumo, abaixo_80=abaixo_80, abaixo_75=abaixo_75)
        if usuario.perfil == "professor":
            professor = Professor.query.filter_by(usuario_id=usuario.id).first_or_404()
            vinculos = ProfessorDisciplina.query.filter_by(professor_id=professor.id).all()
            aulas = Aula.query.join(ProfessorDisciplina).filter(
                ProfessorDisciplina.professor_id == professor.id
            ).order_by(Aula.data_hora.desc()).limit(8).all()
            baixa = []
            for vinculo in vinculos:
                for matricula in Matricula.query.filter_by(turma_id=vinculo.turma_id, ativa=True).all():
                    dados = calcular_frequencia(matricula.aluno_id, vinculo.id)
                    if dados["percentual"] is not None and dados["percentual"] <= LIMITE_ATENCAO:
                        baixa.append((matricula.aluno, vinculo, dados))
            return render_template("professor.html", vinculos=vinculos, aulas=aulas, baixa=baixa)
        aluno = Aluno.query.filter_by(usuario_id=usuario.id).first_or_404()
        matriculas = Matricula.query.filter_by(aluno_id=aluno.id, ativa=True).all()
        dados = []
        for matricula in matriculas:
            vinculos = ProfessorDisciplina.query.filter_by(turma_id=matricula.turma_id).all()
            for vinculo in vinculos:
                resumo = calcular_frequencia(aluno.id, vinculo.id)
                historico = db.session.query(Frequencia).join(Aula).filter(
                    Frequencia.aluno_id == aluno.id,
                    Aula.professor_disciplina_id == vinculo.id,
                    Aula.chamada_salva.is_(True),
                ).order_by(Aula.data_hora.desc()).all()
                dados.append((matricula.turma, vinculo, resumo, historico))
        return render_template("aluno.html", dados=dados)

    @app.route("/admin/cadastros", methods=["GET", "POST"])
    @exige_perfil("administrador")
    def cadastros():
        acao = request.form.get("acao", "")
        if request.method == "POST":
            try:
                if acao in {"aluno", "professor", "administrador"}:
                    nome = request.form.get("nome", "").strip()
                    email = request.form.get("email", "").strip().lower()
                    senha = request.form.get("senha", "")
                    if not nome or "@" not in email or len(senha) < 8:
                        raise ValueError("Informe nome, e-mail válido e senha com pelo menos 8 caracteres.")
                    if Usuario.query.filter(func.lower(Usuario.email) == email).first():
                        raise ValueError("Este e-mail já está cadastrado.")
                    usuario = Usuario(nome=nome, email=email, perfil=acao)
                    usuario.definir_senha(senha)
                    db.session.add(usuario)
                    db.session.flush()
                    if acao == "aluno":
                        matricula = request.form.get("matricula", "").strip()
                        turma_id = request.form.get("turma_id", type=int)
                        if not matricula or Aluno.query.filter_by(matricula=matricula).first():
                            raise ValueError("Informe uma matrícula válida e ainda não utilizada.")
                        aluno = Aluno(usuario_id=usuario.id, matricula=matricula)
                        db.session.add(aluno)
                        if turma_id:
                            if not Turma.query.get(turma_id):
                                raise ValueError("Turma inválida.")
                            db.session.flush()
                            db.session.add(Matricula(aluno=aluno, turma_id=turma_id))
                    elif acao == "professor":
                        registro = request.form.get("registro", "").strip() or None
                        db.session.add(Professor(usuario_id=usuario.id, registro=registro))
                elif acao == "turma":
                    nome = request.form.get("nome", "").strip()
                    ano = request.form.get("ano_letivo", type=int)
                    if not nome or not ano:
                        raise ValueError("Informe nome e ano letivo da turma.")
                    db.session.add(Turma(nome=nome, ano_letivo=ano))
                elif acao == "disciplina":
                    nome = request.form.get("nome", "").strip()
                    codigo = request.form.get("codigo", "").strip() or None
                    if not nome:
                        raise ValueError("Informe o nome da disciplina.")
                    db.session.add(Disciplina(nome=nome, codigo=codigo))
                elif acao == "vinculo":
                    professor_id = request.form.get("professor_id", type=int)
                    disciplina_id = request.form.get("disciplina_id", type=int)
                    turma_id = request.form.get("turma_id", type=int)
                    if not all([Professor.query.get(professor_id), Disciplina.query.get(disciplina_id), Turma.query.get(turma_id)]):
                        raise ValueError("Selecione professor, disciplina e turma válidos.")
                    if ProfessorDisciplina.query.filter_by(professor_id=professor_id, disciplina_id=disciplina_id, turma_id=turma_id).first():
                        raise ValueError("Este vínculo já existe.")
                    db.session.add(ProfessorDisciplina(professor_id=professor_id, disciplina_id=disciplina_id, turma_id=turma_id))
                elif acao == "matricula":
                    aluno_id = request.form.get("aluno_id", type=int)
                    turma_id = request.form.get("turma_id", type=int)
                    if not Aluno.query.get(aluno_id) or not Turma.query.get(turma_id):
                        raise ValueError("Selecione um aluno e uma turma válidos.")
                    existente = Matricula.query.filter_by(aluno_id=aluno_id, turma_id=turma_id).first()
                    if existente and existente.ativa:
                        raise ValueError("Este aluno já está matriculado nesta turma.")
                    if existente:
                        existente.ativa = True
                        existente.data_matricula = date.today()
                    else:
                        db.session.add(Matricula(aluno_id=aluno_id, turma_id=turma_id))
                else:
                    raise ValueError("Ação inválida.")
                db.session.commit()
                flash("Cadastro salvo com sucesso.", "sucesso")
            except (ValueError, TypeError) as erro:
                db.session.rollback()
                flash(str(erro), "erro")
            except Exception:
                db.session.rollback()
                flash("Não foi possível salvar. Verifique se os dados já existem.", "erro")
            return redirect(url_for("cadastros"))
        return render_template("cadastros.html", alunos=Aluno.query.all(), professores=Professor.query.all(), turmas=Turma.query.all(), disciplinas=Disciplina.query.all(), vinculos=ProfessorDisciplina.query.all(), usuarios=Usuario.query.order_by(Usuario.nome).all())

    @app.route("/admin/usuarios/<int:usuario_id>/editar", methods=["GET", "POST"])
    @exige_perfil("administrador")
    def editar_usuario(usuario_id):
        usuario = Usuario.query.get_or_404(usuario_id)
        if request.method == "POST":
            nome = request.form.get("nome", "").strip()
            email = request.form.get("email", "").strip().lower()
            senha = request.form.get("senha", "")
            repetido = Usuario.query.filter(func.lower(Usuario.email) == email, Usuario.id != usuario.id).first()
            if not nome or "@" not in email or repetido or (senha and len(senha) < 8):
                flash("Revise nome, e-mail e senha (mínimo de 8 caracteres, se alterada).", "erro")
                return render_template("editar_usuario.html", usuario=usuario)
            if usuario.aluno:
                matricula = request.form.get("matricula", "").strip()
                duplicada = Aluno.query.filter(Aluno.matricula == matricula, Aluno.id != usuario.aluno.id).first()
                if not matricula or duplicada:
                    flash("Informe uma matrícula válida e ainda não utilizada.", "erro")
                    return render_template("editar_usuario.html", usuario=usuario)
                usuario.aluno.matricula = matricula
            if usuario.professor:
                registro = request.form.get("registro", "").strip() or None
                if registro and Professor.query.filter(Professor.registro == registro, Professor.id != usuario.professor.id).first():
                    flash("Este registro de professor já está em uso.", "erro")
                    return render_template("editar_usuario.html", usuario=usuario)
                usuario.professor.registro = registro
            usuario.nome = nome
            usuario.email = email
            usuario.ativo = request.form.get("ativo") == "sim"
            if senha:
                usuario.definir_senha(senha)
            db.session.commit()
            flash("Usuário atualizado.", "sucesso")
            return redirect(url_for("cadastros"))
        return render_template("editar_usuario.html", usuario=usuario)

    @app.route("/professor/aulas/nova", methods=["GET", "POST"])
    @exige_perfil("professor")
    def nova_aula():
        professor = Professor.query.filter_by(usuario_id=session["usuario_id"]).first_or_404()
        vinculos = ProfessorDisciplina.query.filter_by(professor_id=professor.id).all()
        if request.method == "POST":
            vinculo = ProfessorDisciplina.query.filter_by(id=request.form.get("vinculo_id", type=int), professor_id=professor.id).first()
            if not vinculo:
                abort(403)
            conteudo = request.form.get("conteudo", "").strip()
            aula = Aula(professor_disciplina_id=vinculo.id, conteudo=conteudo or None)
            db.session.add(aula)
            db.session.commit()
            return redirect(url_for("chamada", aula_id=aula.id))
        return render_template("nova_aula.html", vinculos=vinculos)

    def aula_do_professor(aula_id):
        professor = Professor.query.filter_by(usuario_id=session["usuario_id"]).first_or_404()
        aula = Aula.query.join(ProfessorDisciplina).filter(
            Aula.id == aula_id, ProfessorDisciplina.professor_id == professor.id
        ).first_or_404()
        return professor, aula

    @app.route("/professor/chamada/<int:aula_id>", methods=["GET", "POST"])
    @exige_perfil("professor")
    def chamada(aula_id):
        professor, aula = aula_do_professor(aula_id)
        vinculo = aula.professor_disciplina
        matriculas = Matricula.query.filter_by(turma_id=vinculo.turma_id, ativa=True).all()
        if request.method == "POST":
            if not matriculas:
                flash("Não há alunos matriculados nesta turma.", "erro")
                return redirect(url_for("chamada", aula_id=aula.id))
            for matricula in matriculas:
                situacao = request.form.get(f"situacao_{matricula.aluno_id}")
                if situacao not in SITUACOES:
                    flash("Selecione uma situação válida para cada aluno.", "erro")
                    return redirect(url_for("chamada", aula_id=aula.id))
            try:
                Frequencia.query.filter_by(aula_id=aula.id).delete()
                for matricula in matriculas:
                    justificativa = request.form.get(f"justificativa_{matricula.aluno_id}", "").strip() or None
                    situacao = request.form[f"situacao_{matricula.aluno_id}"]
                    if situacao == "justificada" and not justificativa:
                        raise ValueError("Informe a justificativa das faltas marcadas como justificadas.")
                    db.session.add(Frequencia(aula_id=aula.id, aluno_id=matricula.aluno_id, situacao=situacao, justificativa=justificativa))
                aula.chamada_salva = True
                db.session.commit()
                flash("Chamada salva. Você pode reabri-la para corrigir registros.", "sucesso")
                return redirect(url_for("chamada", aula_id=aula.id))
            except ValueError as erro:
                db.session.rollback()
                flash(str(erro), "erro")
            except Exception:
                db.session.rollback()
                flash("Erro ao salvar a chamada.", "erro")
        existentes = {item.aluno_id: item for item in Frequencia.query.filter_by(aula_id=aula.id).all()}
        return render_template("chamada.html", aula=aula, matriculas=matriculas, existentes=existentes)

    @app.get("/professor/historico")
    @exige_perfil("professor")
    def historico_professor():
        professor = Professor.query.filter_by(usuario_id=session["usuario_id"]).first_or_404()
        aulas = Aula.query.join(ProfessorDisciplina).filter(
            ProfessorDisciplina.professor_id == professor.id, Aula.chamada_salva.is_(True)
        ).order_by(Aula.data_hora.desc()).all()
        return render_template("historico.html", aulas=aulas)

    @app.get("/admin/relatorios")
    @exige_perfil("administrador")
    def relatorios():
        linhas = []
        for aluno in Aluno.query.all():
            for matricula in Matricula.query.filter_by(aluno_id=aluno.id, ativa=True).all():
                for vinculo in ProfessorDisciplina.query.filter_by(turma_id=matricula.turma_id).all():
                    resumo = calcular_frequencia(aluno.id, vinculo.id)
                    linhas.append((aluno, matricula.turma, vinculo.disciplina, resumo, status_frequencia(resumo["percentual"])))
        return render_template("relatorios.html", linhas=linhas)

    @app.errorhandler(403)
    def proibido(_erro):
        return render_template("erro.html", codigo=403, mensagem="Seu perfil não tem acesso a esta página."), 403

    @app.errorhandler(404)
    def nao_encontrado(_erro):
        return render_template("erro.html", codigo=404, mensagem="A página ou registro não foi encontrado."), 404

    with app.app_context():
        db.create_all()
        criar_dados_demo()

    return app


def criar_dados_demo():
    """Cria uma base de demonstração apenas quando o banco ainda está vazio."""
    if Usuario.query.first():
        return
    admin = Usuario(nome="Administradora", email="admin@escola.local", perfil="administrador")
    admin.definir_senha("Admin123!")
    prof_usuario = Usuario(nome="Mariana Costa", email="professor@escola.local", perfil="professor")
    prof_usuario.definir_senha("Professor123!")
    db.session.add_all([admin, prof_usuario])
    db.session.flush()
    professor = Professor(usuario_id=prof_usuario.id, registro="PROF001")
    turma = Turma(nome="ADS — 2º semestre", ano_letivo=datetime.now().year)
    disciplina = Disciplina(nome="Programação Orientada a Objetos", codigo="POO")
    db.session.add_all([professor, turma, disciplina])
    db.session.flush()
    vinculo = ProfessorDisciplina(professor_id=professor.id, turma_id=turma.id, disciplina_id=disciplina.id)
    db.session.add(vinculo)
    db.session.flush()
    nomes = ["João Silva", "Maria Souza", "Carlos Santos", "Ana Oliveira", "Pedro Lima", "Beatriz Alves", "Lucas Ferreira", "Julia Martins", "Rafael Costa", "Camila Rocha"]
    alunos = []
    for posicao, nome in enumerate(nomes, start=1):
        conta = Usuario(nome=nome, email=f"aluno{posicao}@escola.local", perfil="aluno")
        conta.definir_senha("Aluno123!")
        db.session.add(conta)
        db.session.flush()
        aluno = Aluno(usuario_id=conta.id, matricula=f"2026{posicao:04d}")
        db.session.add(aluno)
        db.session.flush()
        db.session.add(Matricula(aluno_id=aluno.id, turma_id=turma.id))
        alunos.append(aluno)
    for dia in range(1, 11):
        aula = Aula(professor_disciplina_id=vinculo.id, data_hora=datetime.now().replace(hour=8, minute=0, second=0, microsecond=0), conteudo=f"Aula de demonstração {dia}", chamada_salva=True)
        db.session.add(aula)
        db.session.flush()
        for indice, aluno in enumerate(alunos):
            situacao = "ausente" if (
                (indice == 0 and dia <= 4)
                or (indice == 1 and dia <= 3)
                or (indice >= 2 and (indice + dia) % 17 == 0)
            ) else "presente"
            db.session.add(Frequencia(aula_id=aula.id, aluno_id=aluno.id, situacao=situacao))
    db.session.commit()


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
