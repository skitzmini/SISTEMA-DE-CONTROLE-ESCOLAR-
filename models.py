from datetime import date, datetime

from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db


class Usuario(db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), unique=True, nullable=False, index=True)
    senha_hash = db.Column(db.String(255), nullable=False)
    perfil = db.Column(db.String(20), nullable=False)
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    aluno = db.relationship("Aluno", back_populates="usuario", uselist=False)
    professor = db.relationship("Professor", back_populates="usuario", uselist=False)

    def definir_senha(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def verificar_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)


class Aluno(db.Model):
    __tablename__ = "alunos"
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), unique=True, nullable=False)
    matricula = db.Column(db.String(40), unique=True, nullable=False)
    usuario = db.relationship("Usuario", back_populates="aluno")


class Professor(db.Model):
    __tablename__ = "professores"
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), unique=True, nullable=False)
    registro = db.Column(db.String(40), unique=True)
    usuario = db.relationship("Usuario", back_populates="professor")


class Turma(db.Model):
    __tablename__ = "turmas"
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    ano_letivo = db.Column(db.Integer, nullable=False)
    ativa = db.Column(db.Boolean, nullable=False, default=True)


class Disciplina(db.Model):
    __tablename__ = "disciplinas"
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    codigo = db.Column(db.String(30), unique=True)


class Matricula(db.Model):
    __tablename__ = "matriculas"
    __table_args__ = (db.UniqueConstraint("aluno_id", "turma_id", name="uq_matricula_aluno_turma"),)
    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey("alunos.id"), nullable=False)
    turma_id = db.Column(db.Integer, db.ForeignKey("turmas.id"), nullable=False)
    data_matricula = db.Column(db.Date, nullable=False, default=date.today)
    ativa = db.Column(db.Boolean, nullable=False, default=True)
    aluno = db.relationship("Aluno")
    turma = db.relationship("Turma")


class ProfessorDisciplina(db.Model):
    __tablename__ = "professor_disciplina"
    __table_args__ = (db.UniqueConstraint("professor_id", "disciplina_id", "turma_id", name="uq_prof_disc_turma"),)
    id = db.Column(db.Integer, primary_key=True)
    professor_id = db.Column(db.Integer, db.ForeignKey("professores.id"), nullable=False)
    disciplina_id = db.Column(db.Integer, db.ForeignKey("disciplinas.id"), nullable=False)
    turma_id = db.Column(db.Integer, db.ForeignKey("turmas.id"), nullable=False)
    professor = db.relationship("Professor")
    disciplina = db.relationship("Disciplina")
    turma = db.relationship("Turma")


class Aula(db.Model):
    __tablename__ = "aulas"
    id = db.Column(db.Integer, primary_key=True)
    professor_disciplina_id = db.Column(db.Integer, db.ForeignKey("professor_disciplina.id"), nullable=False)
    data_hora = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    conteudo = db.Column(db.String(250))
    chamada_salva = db.Column(db.Boolean, nullable=False, default=False)
    professor_disciplina = db.relationship("ProfessorDisciplina")


class Frequencia(db.Model):
    __tablename__ = "frequencias"
    __table_args__ = (db.UniqueConstraint("aula_id", "aluno_id", name="uq_frequencia_aula_aluno"),)
    id = db.Column(db.Integer, primary_key=True)
    aula_id = db.Column(db.Integer, db.ForeignKey("aulas.id"), nullable=False)
    aluno_id = db.Column(db.Integer, db.ForeignKey("alunos.id"), nullable=False)
    situacao = db.Column(db.String(20), nullable=False)
    justificativa = db.Column(db.String(300))
    atualizado_em = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    aula = db.relationship("Aula")
    aluno = db.relationship("Aluno")
