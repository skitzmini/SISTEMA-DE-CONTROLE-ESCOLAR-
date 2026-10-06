# Etapa 1 — Planejamento e modelagem inicial

## Escopo desta etapa

Este documento define uma estrutura inicial para o Sistema de Controle de Frequência Escolar e descreve as tabelas e seus relacionamentos. Nenhum modelo executável, rota ou tela é criado nesta etapa; isso fica para as etapas seguintes.

## Tecnologias e organização previstas

- **Backend:** Python com Flask.
- **Banco de dados:** SQLite na primeira versão, por ser simples de instalar e suficiente para desenvolvimento e demonstração local.
- **Acesso a dados:** SQLAlchemy e Flask-SQLAlchemy nas etapas de implementação, mantendo as tabelas e relações explícitas nos modelos Python.
- **Interface:** templates HTML do Flask, CSS e JavaScript simples.
- **Senhas:** hash com Werkzeug (`generate_password_hash` e `check_password_hash`); nunca salvar senha original.

```text
sistema_frequencia/
├── app.py                    # Inicializa e configura a aplicação
├── config.py                 # Configurações, incluindo caminho do banco
├── extensions.py             # Instância compartilhada do SQLAlchemy
├── models/                   # Classes que representam as tabelas
├── routes/                   # Rotas organizadas por área e perfil
├── templates/                # Páginas HTML e componentes reutilizáveis
├── static/
│   ├── css/
│   ├── js/
│   └── images/
├── database/                 # Arquivo SQLite local e dados de demonstração
├── planejamento/
│   └── etapa-1-modelagem.md
├── requirements.txt
└── README.md
```

O arquivo do banco local e segredos de configuração não devem ser enviados ao GitHub. A configuração deverá permitir trocar a chave secreta por variável de ambiente antes de qualquer uso fora do ambiente local.

## Modelo de dados inicial

### `usuarios`

Guarda as credenciais e o perfil de acesso comum a todos os tipos de usuário.

| Campo | Tipo conceitual | Regra |
|---|---|---|
| id | inteiro | Chave primária |
| nome | texto | Obrigatório |
| email | texto | Obrigatório e único; usado no login |
| senha_hash | texto | Obrigatório; nunca contém a senha original |
| perfil | texto | `administrador`, `professor` ou `aluno` |
| ativo | booleano | Permite desativar acesso sem apagar histórico |

### `alunos`

Perfil acadêmico de um usuário aluno. `usuario_id` é chave estrangeira única para `usuarios.id`.

| Campo | Tipo conceitual | Regra |
|---|---|---|
| id | inteiro | Chave primária |
| usuario_id | inteiro | Obrigatório, único, FK para `usuarios.id` |
| matricula | texto | Obrigatória e única |

### `professores`

Perfil de um usuário professor. `usuario_id` é chave estrangeira única para `usuarios.id`.

| Campo | Tipo conceitual | Regra |
|---|---|---|
| id | inteiro | Chave primária |
| usuario_id | inteiro | Obrigatório, único, FK para `usuarios.id` |
| registro | texto | Opcional; se utilizado, deve ser único |

O perfil administrador fica diretamente em `usuarios`, sem uma tabela de perfil adicional nesta versão.

### `turmas`

| Campo | Tipo conceitual | Regra |
|---|---|---|
| id | inteiro | Chave primária |
| nome | texto | Obrigatório, por exemplo `ADS — 2º semestre` |
| ano_letivo | inteiro | Obrigatório |
| ativa | booleano | Indica se a turma está em andamento |

### `disciplinas`

| Campo | Tipo conceitual | Regra |
|---|---|---|
| id | inteiro | Chave primária |
| nome | texto | Obrigatório |
| codigo | texto | Opcional; único quando informado |

### `matriculas`

Associa alunos às turmas. A combinação aluno e turma deve ser única para impedir matrícula duplicada.

| Campo | Tipo conceitual | Regra |
|---|---|---|
| id | inteiro | Chave primária |
| aluno_id | inteiro | Obrigatório, FK para `alunos.id` |
| turma_id | inteiro | Obrigatório, FK para `turmas.id` |
| data_matricula | data | Obrigatória |
| ativa | booleano | Permite encerrar matrícula sem apagar o histórico |

### `professor_disciplina`

Associa professores e disciplinas a uma turma. A combinação professor, disciplina e turma deve ser única. Esta tabela representa quem pode dar aula daquela disciplina naquela turma.

| Campo | Tipo conceitual | Regra |
|---|---|---|
| id | inteiro | Chave primária |
| professor_id | inteiro | Obrigatório, FK para `professores.id` |
| disciplina_id | inteiro | Obrigatório, FK para `disciplinas.id` |
| turma_id | inteiro | Obrigatório, FK para `turmas.id` |

### `aulas`

Cada aula pertence a uma associação professor-disciplina-turma. A chamada será ligada à aula, o que permite manter histórico por data.

| Campo | Tipo conceitual | Regra |
|---|---|---|
| id | inteiro | Chave primária |
| professor_disciplina_id | inteiro | Obrigatório, FK para `professor_disciplina.id` |
| data_hora | data e hora | Obrigatória |
| conteudo | texto | Opcional; assunto ou observação da aula |

### `frequencias`

Um registro para cada aluno em cada aula. A combinação aula e aluno deve ser única. A situação aceita inicialmente `presente`, `ausente` ou `justificada`.

| Campo | Tipo conceitual | Regra |
|---|---|---|
| id | inteiro | Chave primária |
| aula_id | inteiro | Obrigatório, FK para `aulas.id` |
| aluno_id | inteiro | Obrigatório, FK para `alunos.id` |
| situacao | texto | Obrigatório; valor validado no backend |
| justificativa | texto | Opcional; motivo informado para falta justificada |
| atualizado_em | data e hora | Data da gravação ou correção |

## Relacionamentos

```text
usuarios 1 ── 0..1 alunos
usuarios 1 ── 0..1 professores
alunos 1 ── N matriculas N ── 1 turmas
professores 1 ── N professor_disciplina N ── 1 disciplinas
turmas 1 ── N professor_disciplina
professor_disciplina 1 ── N aulas
aulas 1 ── N frequencias N ── 1 alunos
```

Um aluno pode estar em turmas diferentes ao longo do tempo, e uma turma pode ter vários alunos. Uma turma pode ter várias disciplinas e professores. Cada aula pertence a uma combinação específica de turma, disciplina e professor; cada frequência pertence a um aluno e àquela aula.

## Regras para os cálculos

- Total de aulas consideradas para um aluno = aulas registradas para a turma/disciplina em que o aluno tinha matrícula ativa na data da aula e para as quais há chamada registrada.
- Presença = registros com situação `presente`.
- Falta = registros com situação `ausente` ou `justificada`.
- Percentual de presença = presenças ÷ total de chamadas registradas × 100. Se não houver chamadas, exibir `Sem aulas registradas`, sem dividir por zero.
- Falta justificada continua contando como falta para o percentual. A justificativa é uma informação separada; se a instituição decidir outra regra, ela deve ser alterada de forma explícita.
- Os limites de alerta (80% e 75%) serão constantes centralizadas na aplicação, não repetidas nas telas ou consultas.

## Controles de integridade e acesso previstos

- Usar chaves estrangeiras e restrições únicas para impedir referências inválidas e duplicações comuns.
- Validar no servidor campos obrigatórios, perfil permitido, situação da frequência e existência de matrícula compatível com a aula.
- Proteger rotas por perfil no backend: aluno consulta apenas os próprios dados; professor opera apenas aulas das associações atribuídas a ele; administrador gerencia a estrutura.
- Não permitir que uma chamada crie frequência para aluno não matriculado na turma da aula.
- Preservar aulas e frequências já registradas ao desativar usuários, matrículas ou turmas.

## Decisões para confirmar durante a implementação

1. O cadastro permitirá mais de um administrador; todos terão perfil `administrador` em `usuarios`.
2. A frequência justificada será exibida separadamente, mas contará como falta no percentual.
3. Uma chamada iniciada pelo professor criará a aula e os registros dos alunos matriculados; a gravação deverá ser validada no servidor.
4. A primeira versão usará SQLite local. Se houver necessidade de uso simultâneo por uma instituição, a escolha do banco e a implantação deverão ser revistas antes de produção.

## Próxima etapa

Na Etapa 2, criar o banco SQLite e os modelos Python correspondentes a este planejamento. A Etapa 1 não implementa autenticação, telas, rotas nem cadastros.
