# EduFrequência — Sistema de Controle de Frequência Escolar

Aplicação web de demonstração para organizar alunos, professores, turmas, disciplinas, aulas e chamadas em um só lugar. O objetivo é reduzir erros de registros manuais e facilitar a consulta ao histórico e à frequência.

## Tecnologias

- Python 3.10 ou superior
- Flask e Flask-SQLAlchemy
- SQLite para execução local
- HTML, CSS e JavaScript

O projeto mantém o fluxo em rotas Flask comuns e modelos SQLAlchemy simples para ser estudado por quem está começando.

## Estrutura

```text
app.py                  Inicialização, rotas, permissões e regras principais
config.py               Configuração do banco e da chave de sessão
extensions.py           Instância compartilhada do SQLAlchemy
models.py               Modelos das tabelas e senha com hash
templates/              Páginas HTML renderizadas pelo Flask
static/css/style.css    Estilos responsivos
static/js/app.js        Interações simples
database/                Banco SQLite local criado automaticamente
planejamento/            Documento de modelagem da Etapa 1
requirements.txt         Dependências Python
```

## Instalação e execução

No terminal, dentro da pasta do projeto:

```bash
python -m venv .venv
```

Ative o ambiente virtual:

```bash
# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# macOS ou Linux
source .venv/bin/activate
```

Instale as dependências e inicie o servidor:

```bash
python -m pip install -r requirements.txt
python app.py
```

Abra `http://127.0.0.1:5000` no navegador. O banco `database/frequencia.sqlite3` e os dados demonstrativos são criados automaticamente na primeira execução. Para reiniciar a demonstração do zero, pare o servidor e remova esse arquivo local.

## Contas de demonstração

| Perfil | E-mail | Senha |
|---|---|---|
| Administrador | `admin@escola.local` | `Admin123!` |
| Professor | `professor@escola.local` | `Professor123!` |
| Aluno | `aluno1@escola.local` | `Aluno123!` |

Há dez alunos fictícios. As outras contas de aluno seguem `aluno2@escola.local` a `aluno10@escola.local`, com a mesma senha `Aluno123!`. Os dados só são inseridos quando o banco ainda não contém usuários.

## Funcionalidades disponíveis

- Login e saída com senha armazenada como hash, proteção CSRF e separação de acesso por perfil.
- Administrador cadastra alunos, professores, administradores, turmas e disciplinas, atribui professor a uma turma e disciplina, edita contas e desativa acessos.
- Professor vê seus vínculos, cria aula, realiza e corrige chamadas, consulta histórico e identifica alunos com frequência baixa.
- Aluno consulta frequência por disciplina, faltas e histórico; não consegue editar registros.
- Painel administrativo resume cadastros, frequência média e alunos abaixo dos limites.
- Relatório de frequência por aluno, turma e disciplina, com opção de impressão pelo navegador.
- Dez aulas fictícias com frequências para preencher os painéis na primeira execução.

## Regras de frequência

Frequência = presenças ÷ chamadas registradas × 100. Situações permitidas: presente, ausente e justificada. A falta justificada é identificada separadamente no histórico, mas conta como falta no cálculo. Aulas ainda sem chamada salva não entram na conta. Sem registros, o sistema mostra que ainda não há aulas.

Os limites ficam centralizados em `app.py`: acima de 80% é situação normal; de 75% a 80%, atenção; abaixo de 75%, crítica.

## Modelo do banco

As tabelas são `usuarios`, `alunos`, `professores`, `turmas`, `disciplinas`, `matriculas`, `professor_disciplina`, `aulas` e `frequencias`. O documento [planejamento da Etapa 1](planejamento/etapa-1-modelagem.md) descreve as relações, restrições de duplicidade e decisões de modelagem.

## Configuração e segurança

O padrão é SQLite local. `DATABASE_URL` pode apontar para outro banco compatível com SQLAlchemy. Defina uma variável de ambiente `SECRET_KEY` própria antes de qualquer implantação; a chave padrão serve apenas para desenvolvimento local. Não publique o arquivo SQLite, credenciais de demonstração nem segredos. Em PowerShell, por exemplo:

```powershell
$env:SECRET_KEY = "substitua-por-um-valor-aleatorio-local"
python app.py
```

Esta versão usa o servidor de desenvolvimento do Flask e contas de demonstração conhecidas. Não é uma configuração pronta para produção. Para uso real, configure servidor WSGI, HTTPS, segredo forte, política de cópias de segurança e revisão operacional do banco e das contas.

## Próximas possibilidades

QR Code por aula, notificações, e-mail de alerta, aplicativo móvel, integração acadêmica, PDF, exportação Excel, painel para responsáveis, controle de horários e API REST podem ser avaliados em etapas futuras.
