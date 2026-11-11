# FilaFácil Logística — Plano de Execução e Prompts

Nov 11, 2026 · @João

## Visão geral

O projeto troca o arquivo JSON da FilaFácil por um banco SQLite acessado via SQLAlchemy, com CRUD de coletas, filtros e três camadas, tudo num menu de terminal. São 4 fases, cerca de 6 horas no total, e cada fase termina com um commit.

| Item | Escolha |
| --- | --- |
| Linguagem | Python 3.11+ |
| Banco | SQLite (arquivo local `filafacil.db`, já vem com o Python) |
| ORM | SQLAlchemy 2.x (estilo `Mapped` / `mapped_column`) |
| Interface | Menu interativo em loop no terminal |
| Versionamento | Git + repositório remoto no GitHub |

**Fora do escopo (não fazer):** interface web, API, autenticação, permissões, mais de uma tabela, relacionamentos, joins, transações complexas e SQL escrito à mão.

### Como usar este documento

1. Siga as seções na ordem. Cada fase traz os passos, o prompt de implementação e o commit que fecha a fase.
2. Antes do primeiro prompt, cole o **prompt de contexto** abaixo no seu assistente de IA (Claude, Claude Code, Copilot Chat etc.). Ele fixa as regras do projeto para todas as etapas.
3. Depois de cada prompt, leia o código gerado, rode e teste antes de seguir. Você é quem entrega e explica o projeto.

### Prompt de contexto (cole uma vez, no início)

```text
Você vai me ajudar a construir um projeto de estudo chamado FilaFácil Logística, passo a passo.
Não gere nada além do que eu pedir em cada etapa.

Contexto: a empresa guardava solicitações de coleta num arquivo JSON local. Vamos migrar para um banco relacional local.

Stack obrigatória:
- Python 3.11+
- SQLite local (arquivo filafacil.db na raiz do projeto)
- SQLAlchemy 2.x com o estilo DeclarativeBase / Mapped / mapped_column
- Aplicação de terminal com menu interativo em loop

Arquitetura obrigatória (3 camadas):
- controller/: menu e leitura de entrada do usuário; chama apenas o service; nunca importa nada do banco
- service/: regras de negócio e validações; chama apenas o repository; sem nenhuma query
- repository/: ÚNICO lugar com Session, select, insert, update e delete do SQLAlchemy
- models/: a classe Pickup mapeada no ORM
- database.py: engine, fábrica de sessões e criação da tabela

Tabela única "pickups": id (PK inteiro autoincremento), customer_name (texto, obrigatório), address (texto, obrigatório), package_count (inteiro > 0, obrigatório), priority (low | medium | high), status (pending | in_transit | collected | canceled), created_at (data/hora gerada automaticamente).

Proibido: interface web, API, autenticação, permissões, múltiplas tabelas, relacionamentos, joins, SQL manual (text()), bibliotecas além do SQLAlchemy.

Regras de qualidade:
- Nunca aceitar campo obrigatório vazio ou só com espaços
- Antes de atualizar ou deletar, verificar se a coleta existe e avisar se não existir
- Entradas inválidas (letra onde se espera número) não podem derrubar o programa
- Identificadores em inglês (pastas, arquivos, classes, funções, variáveis, tabela, colunas e valores gravados no banco)
- Textos exibidos ao usuário (menu, mensagens, erros) em português; o menu pode mostrar rótulos em português para os valores em inglês (ex.: high = Alta)
- Código simples e legível, com docstrings curtas e type hints

Responda "Entendido" e aguarde a primeira etapa.
```

## Arquitetura e estrutura

Cada camada conversa só com a de baixo, e apenas o repository toca no banco. Essa regra vale a métrica de qualidade "100% da lógica de banco no repository".

&#91;embedded content: arquitetura em 3 camadas · do menu ao banco\]

Uma operação desce do menu até o banco e o resultado volta pelo mesmo caminho. Nenhuma camada pula a seguinte.

### Estrutura de pastas

```text
filafacil/
├── main.py                          # ponto de entrada: cria a tabela e abre o menu
├── database.py                      # engine, SessionLocal, Base, create_tables()
├── models/
│   ├── __init__.py
│   └── pickup.py                    # classe Pickup + constantes PRIORITIES/STATUSES
├── repository/
│   ├── __init__.py
│   └── pickup_repository.py         # todas as operações via ORM
├── service/
│   ├── __init__.py
│   └── pickup_service.py            # validações e regras de negócio
├── controller/
│   ├── __init__.py
│   └── pickup_controller.py         # menu, entrada e saída no terminal
├── requirements.txt
├── .gitignore
└── README.md
```

### Tabela `pickups`

| Coluna | Tipo SQLAlchemy | Regras |
| --- | --- | --- |
| id | `Integer` | Chave primária, autoincremento |
| customer\_name | `String(100)` | Obrigatório, `nullable=False` |
| address | `String(200)` | Obrigatório, `nullable=False` |
| package\_count | `Integer` | Obrigatório, maior que 0 |
| priority | `String(10)` | `low`, `medium` ou `high`; padrão `medium` |
| status | `String(20)` | `pending`, `in_transit`, `collected` ou `canceled`; padrão `pending` |
| created\_at | `DateTime` | Preenchido automaticamente na inserção |

Os valores válidos ficam nas constantes `PRIORITIES` e `STATUSES` em `models/pickup.py`, e o banco grava sempre o valor em inglês. O controller mostra rótulos em português (ex.: `high` = Alta, `in_transit` = Em rota) por meio de dicionários `PRIORITY_LABELS` e `STATUS_LABELS`.

### Menu final esperado

```text
===== FilaFácil Logística =====
1. Cadastrar coleta
2. Listar coletas
3. Filtrar coletas
4. Atualizar status
5. Deletar coleta
0. Sair
```

## Pré-requisitos e setup (≈15 min)

Você precisa de Python 3.11+, Git, uma conta no GitHub e um editor (VS Code recomendado). Confira as versões com `python --version` e `git --version`.

1. Crie um repositório vazio no GitHub chamado `filafacil-logistica`, sem README nem .gitignore.
2. Crie a pasta do projeto e o ambiente virtual:

```bash
mkdir filafacil && cd filafacil
python -m venv .venv

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
# Linux / macOS
source .venv/bin/activate

pip install "sqlalchemy>=2.0"
pip freeze > requirements.txt
```

3. Crie o `.gitignore`:

```text
.venv/
__pycache__/
*.pyc
filafacil.db
.vscode/
```

4. Inicialize o Git e conecte ao remoto:

```bash
git init
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/filafacil-logistica.git
git add .gitignore requirements.txt
git commit -m "chore: setup inicial do projeto"
git push -u origin main
```

O `filafacil.db` fica fora do Git de propósito: o banco é recriado automaticamente na primeira execução, e o README explica isso.

## Fase 1: Banco e ORM (≈1h)

No fim desta fase, rodar `python main.py` cria o arquivo `filafacil.db` com a tabela `pickups` e as colunas certas. Esta parte tem o maior peso na avaliação (\~20%).

### Passos

1. Crie as pastas `models/`, `repository/`, `service/` e `controller/`, cada uma com um `__init__.py` vazio.
2. Rode o **Prompt 1.1** para gerar `database.py` e `models/pickup.py`.
3. Rode o **Prompt 1.2** para gerar um `main.py` provisório que só cria a tabela.
4. Execute `python main.py` e confira que `filafacil.db` apareceu.
5. Valide a tabela com o comando de verificação abaixo.

### Prompt 1.1: conexão e model

```text
Etapa 1.1 - Banco e model.

Crie dois arquivos:

1) database.py
- DATABASE_URL = "sqlite:///filafacil.db"
- engine com create_engine (echo=False)
- SessionLocal com sessionmaker(bind=engine, expire_on_commit=False)
- class Base(DeclarativeBase)
- função create_tables() que importa models.pickup e chama Base.metadata.create_all(engine)

2) models/pickup.py
- constantes PRIORITIES = ("low", "medium", "high") e STATUSES = ("pending", "in_transit", "collected", "canceled")
- dicionários PRIORITY_LABELS = {"low": "Baixa", "medium": "Média", "high": "Alta"} e
  STATUS_LABELS = {"pending": "Pendente", "in_transit": "Em rota", "collected": "Coletada", "canceled": "Cancelada"}
- classe Pickup(Base), __tablename__ = "pickups", usando Mapped e mapped_column:
  id: int, primary_key, autoincrement
  customer_name: str, String(100), nullable=False
  address: str, String(200), nullable=False
  package_count: int, Integer, nullable=False
  priority: str, String(10), nullable=False, default "medium"
  status: str, String(20), nullable=False, default "pending"
  created_at: datetime, DateTime, nullable=False, default=datetime.now
- método __repr__ legível

Não crie repository, service nem controller ainda. Explique em 3 linhas por que cada tipo foi escolhido.
```

### Prompt 1.2: main provisório

```text
Etapa 1.2 - Crie um main.py provisório que chama create_tables() de database.py
e imprime "Banco pronto: filafacil.db". Nada além disso.
```

### Verificação

```bash
python main.py
python -c "import sqlite3; c = sqlite3.connect('filafacil.db'); print(c.execute('PRAGMA table_info(pickups)').fetchall())"
```

A saída deve listar as 7 colunas com seus tipos. Se faltar alguma, ajuste o model, apague o `filafacil.db` e rode de novo, porque o `create_all` não altera tabelas que já existem.

### Commit

```bash
git add .
git commit -m "feat: configura SQLite + SQLAlchemy e cria model Coleta"
git push
```

## Fase 2: Insert e Select (≈1h30)

No fim desta fase, dá para cadastrar e listar coletas pelo menu, e os dados continuam lá depois de fechar e abrir o programa. A fase passa pelas três camadas, de baixo para cima.

### Passos

1. **Prompt 2.1**: repository com `create` e `list_all`.
2. **Prompt 2.2**: service com validação de campos obrigatórios.
3. **Prompt 2.3**: controller com menu em loop (opções 1, 2 e 0) e `main.py` definitivo.
4. Teste de persistência: cadastre 3 coletas, saia com 0, rode de novo e liste.
5. Teste de validação: tente cadastrar com nome vazio, só espaços, pacotes = 0 e pacotes = "abc".

### Prompt 2.1: repository (insert e select)

```text
Etapa 2.1 - Crie repository/pickup_repository.py com a classe PickupRepository.

Regras:
- É a ÚNICA camada que usa SessionLocal e o SQLAlchemy (select, session.add, commit).
- Cada método abre a sessão com "with SessionLocal() as session:".
- Sem validação de negócio e sem print aqui.

Métodos:
- create(customer_name, address, package_count, priority, status) -> Pickup
  cria o objeto, add, commit, refresh e retorna a coleta com id preenchido
- list_all(order_by: str = "id") -> list[Pickup]
  usa select(Pickup).order_by(...); aceita "id" (crescente) ou "date" (created_at, mais recente primeiro)

Mostre o arquivo completo.
```

### Prompt 2.2: service (validações)

```text
Etapa 2.2 - Crie service/pickup_service.py com a classe PickupService, que recebe um PickupRepository no __init__.

Regras:
- Nenhum import de SQLAlchemy ou SessionLocal nesta camada.
- Erros de validação geram ValueError com mensagem clara em português.

Métodos:
- register(customer_name, address, package_count, priority, status="pending") -> Pickup
  - aplica strip() nos textos; customer_name e address não podem ficar vazios
  - package_count precisa ser int maior que 0
  - priority em PRIORITIES e status em STATUSES (importados de models.pickup), sem diferenciar maiúsculas
  - só então chama repository.create
- list_all(order_by="id") -> list[Pickup]
  valida que order_by é "id" ou "date" e delega ao repository

Mostre o arquivo completo.
```

### Prompt 2.3: controller, menu e main

```text
Etapa 2.3 - Crie controller/pickup_controller.py e reescreva main.py.

controller/pickup_controller.py, classe PickupController(service):
- run(): menu em loop com as opções (textos em português)
  1. Cadastrar coleta | 2. Listar coletas | 0. Sair
  (deixe as opções 3, 4 e 5 visíveis com a mensagem "Em breve")
- register(): pede nome do cliente, endereço, quantidade de pacotes e prioridade
  (mostrando as opções numeradas com PRIORITY_LABELS e convertendo para o valor em inglês).
  Se a quantidade não for número, avisa e volta ao menu sem quebrar.
  Chama service.register e mostra "Coleta #id cadastrada".
  Captura ValueError e mostra a mensagem ao usuário.
- list_pickups(): pergunta se ordena por ID ou data; mostra uma tabela alinhada no terminal
  (ID | Cliente | Endereço | Pacotes | Prioridade | Status | Criado em dd/mm/aaaa hh:mm),
  usando PRIORITY_LABELS e STATUS_LABELS para exibir em português.
  Use um método auxiliar print_table(pickups) para reaproveitar depois.
  Se não houver coletas, mostra "Nenhuma coleta cadastrada".
- O controller NÃO importa SQLAlchemy, SessionLocal nem o repository.

main.py:
- chama create_tables()
- monta repository -> service -> controller (injeção simples pelo construtor)
- chama controller.run() dentro de if __name__ == "__main__"
- Ctrl+C encerra com uma mensagem amigável, sem traceback

Mostre os dois arquivos completos.
```

### Commit

```bash
git add .
git commit -m "feat: cadastro e listagem de coletas com validação"
git push
```

## Fase 3: Filtros, Update e Delete (≈1h45)

No fim desta fase, as opções 3, 4 e 5 do menu funcionam, e ID inexistente gera aviso, não erro. Filtros e deleção somam cerca de 30% da nota.

### Passos

1. **Prompt 3.1**: métodos novos no repository (WHERE via ORM).
2. **Prompt 3.2**: métodos novos no service, com verificação de existência.
3. **Prompt 3.3**: opções 3, 4 e 5 no controller.
4. Teste cada filtro, atualize um status, delete uma coleta e tente as duas operações com ID 999.
5. Faça um commit por funcionalidade, se quiser um histórico mais detalhado.

### Prompt 3.1: repository (WHERE, update, delete)

```text
Etapa 3.1 - Adicione ao PickupRepository (sem alterar os métodos existentes):

- get_by_id(pickup_id: int) -> Pickup | None  -> session.get(Pickup, pickup_id)
- filter_by_status(status: str) -> list[Pickup]  -> select(...).where(Pickup.status == status).order_by(Pickup.id)
- filter_by_priority(priority: str) -> list[Pickup]  -> mesmo padrão
- filter_by_name(term: str) -> list[Pickup]  -> where(Pickup.customer_name.ilike(f"%{term}%")), busca parcial sem diferenciar maiúsculas
- update_status(pickup_id: int, new_status: str) -> Pickup | None
  busca com session.get; se None retorna None; senão altera, commit, refresh e retorna
- delete(pickup_id: int) -> bool
  busca com session.get; se None retorna False; senão session.delete, commit e retorna True

Nada de SQL manual. Mostre o arquivo completo atualizado e, em comentário,
o SQL equivalente de cada filtro (ex.: SELECT * FROM pickups WHERE status = ?).
```

### Prompt 3.2: service (regras e existência)

```text
Etapa 3.2 - Adicione ao PickupService:

- get_by_id(pickup_id) -> Pickup: se o repository retornar None, lança LookupError("Coleta #id não encontrada")
- filter(field: str, value: str) -> list[Pickup]
  field é "status", "priority" ou "name"; aplica strip; value não pode ser vazio;
  status e priority devem estar em STATUSES/PRIORITIES (ValueError se não estiverem); delega ao método certo do repository
- update_status(pickup_id, new_status) -> Pickup
  valida new_status; chama get_by_id ANTES (garante a existência); depois repository.update_status
- delete(pickup_id) -> None
  chama get_by_id antes; depois repository.delete

Continua sem nenhum import de SQLAlchemy. Mostre o arquivo completo atualizado.
```

### Prompt 3.3: controller (opções 3, 4 e 5)

```text
Etapa 3.3 - Complete o PickupController:

- filter_pickups() - opção 3 "Filtrar coletas": submenu 1. Por status | 2. Por prioridade | 3. Por nome do cliente | 0. Voltar.
  Para status/prioridade, mostre as opções numeradas com STATUS_LABELS/PRIORITY_LABELS e envie o valor em inglês.
  Reaproveite print_table(). Sem resultados: "Nenhuma coleta encontrada para esse filtro".
- update_status() - opção 4 "Atualizar status": pede o ID (validando que é número), mostra a coleta atual,
  lista os status válidos, pede o novo e confirma a alteração.
- delete_pickup() - opção 5 "Deletar coleta": pede o ID, mostra a coleta encontrada e pede confirmação (s/n) antes de deletar.
- Captura ValueError e LookupError e mostra as mensagens; nunca deixa um traceback chegar ao usuário.
- Remova as mensagens "Em breve".

Mostre o arquivo completo atualizado.
```

### Commit

```bash
git add .
git commit -m "feat: filtros por status/prioridade/nome, atualização de status e deleção"
git push
```

## Fase 4: Camadas, README e entrega (≈1h)

No fim desta fase, as camadas estão limpas, o README permite que qualquer pessoa rode o projeto do zero, e o push final está feito. Git + README valem cerca de 15% da nota.

### Passos

1. Confira as camadas você mesmo com os comandos de busca abaixo e depois rode o **Prompt 4.1**.
2. Rode o **Prompt 4.2** para gerar o README.
3. Faça o teste de "clone limpo" descrito no fim desta seção.
4. Faça o commit final e o push.

### Verificação rápida das camadas

```bash
# Deve aparecer SOMENTE em repository/, database.py e models/
grep -rn "sqlalchemy\|SessionLocal\|session\." --include=*.py . | grep -v .venv

# Windows (PowerShell)
Get-ChildItem -Recurse -Filter *.py | Where-Object FullName -notmatch '\.venv' | Select-String "sqlalchemy|SessionLocal|session\."
```

Se aparecer alguma ocorrência em `service/` ou `controller/`, há lógica de banco no lugar errado.

### Prompt 4.1: revisão de arquitetura

```text
Etapa 4.1 - Revisão. Vou colar todos os arquivos do projeto abaixo.
Analise e responda em lista:
1. Existe algum uso de SQLAlchemy/SessionLocal fora de repository/, database.py e models/?
2. O controller chama apenas o service? O service chama apenas o repository?
3. Algum caminho permite salvar campo obrigatório vazio ou package_count <= 0?
4. update_status e delete verificam a existência antes de agir?
5. Alguma entrada do usuário pode gerar traceback?
6. Há código morto, duplicado, identificador em português ou nome inconsistente?
Para cada problema, mostre só o trecho corrigido. Não adicione funcionalidades novas.

[cole aqui: database.py, models/pickup.py, repository/pickup_repository.py,
service/pickup_service.py, controller/pickup_controller.py, main.py]
```

### Prompt 4.2: README

```text
Etapa 4.2 - Escreva o README.md do projeto em português, com estas seções:
1. FilaFácil Logística - descrição em 2 linhas (migração de JSON para banco relacional com ORM)
2. Tecnologias - Python 3.11+, SQLite, SQLAlchemy 2.x
3. Estrutura do projeto - árvore de pastas e o papel de cada camada (controller, service, repository)
4. Banco de dados - tabela pickups com colunas, tipos, regras e os valores aceitos de priority e status
   (com a tradução exibida no menu); explique que filafacil.db é criado automaticamente na primeira
   execução e que, para zerar o banco, basta apagar o arquivo
5. Como configurar e executar - git clone, venv (Windows e Linux/macOS), pip install -r requirements.txt, python main.py
6. Como usar - cada opção do menu com um exemplo curto de entrada e saída
7. Validações implementadas
8. Equivalentes SQL - tabela com cada método do PickupRepository e o SQL correspondente (INSERT, SELECT ... ORDER BY,
   SELECT ... WHERE, UPDATE ... WHERE id, DELETE ... WHERE id)
9. JSON x banco relacional - 3 a 4 linhas sobre o que mudou e por quê
10. Autor - [SEU NOME]

Use a estrutura e os nomes reais do projeto (cole o main.py e o models/pickup.py abaixo).
```

A seção 9 do README mostra o conceito de banco relacional, uma das 6 hard skills avaliadas.

### Teste de clone limpo e entrega

```bash
git add .
git commit -m "docs: README com setup do banco e uso do sistema"
git push

# em outra pasta
git clone https://github.com/SEU_USUARIO/filafacil-logistica.git teste-clone
cd teste-clone
python -m venv .venv && source .venv/bin/activate   # ou .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

Se rodar e criar o banco sozinho, a entrega está pronta. Depois apague a pasta `teste-clone`.

## Testes manuais e checklist de entrega

Rode este roteiro com o banco zerado (apague `filafacil.db`) antes do push final. Cada linha corresponde a um critério de sucesso do case.

| # | Ação | Resultado esperado |
| --- | --- | --- |
| 1 | Cadastrar "Mercado Bom Preço", 5 pacotes, Alta (`high`) | "Coleta #1 cadastrada" |
| 2 | Cadastrar "Farmácia Vida", 2 pacotes, Baixa (`low`) | "Coleta #2 cadastrada" |
| 3 | Cadastrar "Mercado Central", 10 pacotes, Média (`medium`) | "Coleta #3 cadastrada" |
| 4 | Cadastrar com nome vazio ou só espaços | Mensagem de erro, nada salvo |
| 5 | Cadastrar com pacotes = 0 e pacotes = "abc" | Mensagem de erro, sem traceback |
| 6 | Listar por ID e depois por data | Ordens diferentes e corretas |
| 7 | Sair (0), rodar `python main.py` de novo e listar | As 3 coletas continuam lá |
| 8 | Filtrar por nome "mercado" | Coletas #1 e #3 |
| 9 | Filtrar por prioridade Alta (`high`) | Coleta #1 |
| 10 | Atualizar #2 para Em rota (`in_transit`) e filtrar por esse status | Coleta #2 |
| 11 | Atualizar a coleta #999 | "Coleta #999 não encontrada" |
| 12 | Deletar #3, confirmar com "s" e listar | Sobram #1 e #2 |
| 13 | Deletar a coleta #999 | "Coleta #999 não encontrada" |
| 14 | Apertar Ctrl+C no menu | Encerramento sem traceback |

### Checklist dos critérios de sucesso

- [ ] Tabela `pickups` com chave primária e tipos coerentes, mapeada no SQLAlchemy
- [ ] Cadastro valida campos obrigatórios: zero campos vazios aceitos
- [ ] Listagem ordenada por ID ou data
- [ ] Filtros por status, prioridade e nome usando `.where()` do ORM
- [ ] Atualização de status pelo ID, com verificação de existência
- [ ] Deleção com verificação de existência e confirmação
- [ ] Dados persistem entre execuções
- [ ] 100% da lógica de banco no repository (verificado com o grep da Fase 4)
- [ ] Menu interativo em loop, sem traceback em entradas inválidas
- [ ] Nenhum item proibido: sem web, API, autenticação, segunda tabela, join ou SQL manual
- [ ] README com configuração do banco, execução e uso do menu
- [ ] Pelo menos 5 commits com mensagens claras e push no remoto
- [ ] Teste de clone limpo passou

### Se algo der errado

- **Os dados somem ao reiniciar:** falta `session.commit()` no repository, ou o caminho do banco muda conforme a pasta de onde você roda. Execute sempre a partir da raiz do projeto.
- **`DetachedInstanceError` ao exibir uma coleta:** confirme `expire_on_commit=False` no `sessionmaker`.
- **Coluna nova não aparece:** o `create_all` não altera tabela existente. Apague o `filafacil.db` e rode de novo.
- **`ModuleNotFoundError: models`:** rode `python main.py` da raiz e confira os `__init__.py` nas pastas.