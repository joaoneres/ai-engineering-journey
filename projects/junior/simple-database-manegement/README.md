# FilaFácil Logística

A study project that migrates a logistics company's pickup requests from a local JSON file to a local relational database.
It is a terminal application built with a 3-layer architecture and an ORM, with no web interface or API.

## Technologies

- Python 3.11+
- SQLite (local file `filafacil.db`)
- SQLAlchemy 2.x (`DeclarativeBase` / `Mapped` / `mapped_column` style)

## Project structure

```
simple-database-manegement/
├── main.py                       # entry point: creates the table and opens the menu
├── database.py                   # engine, SessionLocal, Base, create_tables()
├── models/
│   └── pickup.py                 # Pickup model + PRIORITIES/STATUSES constants and labels
├── repository/
│   └── pickup_repository.py      # all database operations via the ORM
├── service/
│   └── pickup_service.py         # validations and business rules
├── controller/
│   └── pickup_controller.py      # menu, input and output in the terminal
├── requirements.txt
└── README.md
```

Each layer talks only to the one below it:

| Layer | Role |
|---|---|
| `controller` | Shows the menu, reads user input and prints results. Calls only the service. Never touches the database. |
| `service` | Business rules and validations. Calls only the repository. Contains no queries. |
| `repository` | The only place that uses `Session`, `select`, `add`, `delete` and `commit`. |

`models/` holds the ORM class and `database.py` holds the engine and session factory.

## Database

Single table: `pickups`.

| Column | Type | Rules |
|---|---|---|
| `id` | Integer | Primary key, autoincrement |
| `customer_name` | String(100) | Required |
| `address` | String(200) | Required |
| `package_count` | Integer | Required, must be greater than 0 |
| `priority` | String(10) | `low`, `medium` or `high`; default `medium` |
| `status` | String(20) | `pending`, `in_transit`, `collected` or `canceled`; default `pending` |
| `created_at` | DateTime | Filled automatically on insert |

The database always stores the English values. The menu shows Portuguese labels:

| `priority` | Menu label | | `status` | Menu label |
|---|---|---|---|---|
| `low` | Baixa | | `pending` | Pendente |
| `medium` | Média | | `in_transit` | Em rota |
| `high` | Alta | | `collected` | Coletada |
| | | | `canceled` | Cancelada |

The file `filafacil.db` is created automatically on the first run. To reset the database, just delete the file; it is recreated on the next run.

## Setup and run

```bash
git clone https://github.com/joaoneres/ai-engineering-journey.git
cd ai-engineering-journey/projects/junior/simple-database-manegement
```

Create and activate a virtual environment (Python 3.11 or newer):

```bash
# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate

# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Install the dependencies and run:

```bash
pip install -r requirements.txt
python main.py
```

## Usage

```
===== FilaFácil Logística =====
1. Cadastrar coleta
2. Listar coletas
3. Filtrar coletas
4. Atualizar status
5. Deletar coleta
0. Sair
```

**1. Cadastrar coleta** (register a pickup)
```
Nome do cliente: Ana Souza
Endereço: Rua das Flores, 10
Quantidade de pacotes: 3
Prioridade:
  1. Baixa
  2. Média
  3. Alta
Escolha uma opção: 3
Coleta #1 cadastrada.
```

**2. Listar coletas** (list, ordered by ID or by date, newest first)
```
Ordenar por (1) ID ou (2) Data? 1

ID | Cliente   | Endereço           | Pacotes | Prioridade | Status   | Criado em
---+-----------+--------------------+---------+------------+----------+-----------------
1  | Ana Souza | Rua das Flores, 10 | 3       | Alta       | Pendente | 11/11/2026 19:06
```

**3. Filtrar coletas** (filter by status, priority or customer name; the name search is partial and case-insensitive)
```
Filtrar por:
  1. Status
  2. Prioridade
  3. Nome do cliente
  0. Voltar
Escolha uma opção: 3
Nome (ou parte do nome) do cliente: ana
```
Prints the matching rows in the same table, or `Nenhuma coleta encontrada para esse filtro.`

**4. Atualizar status** (update the status of an existing pickup)
```
ID da coleta: 1
Coleta atual:
...
Novo status:
  1. Pendente
  2. Em rota
  3. Coletada
  4. Cancelada
Escolha uma opção: 2
Status da coleta #1 alterado para Em rota.
```

**5. Deletar coleta** (delete, with confirmation)
```
ID da coleta: 1
Coleta encontrada:
...
Deseja realmente deletar? (s/n): s
Coleta #1 deletada.
```

**0. Sair** exits the program. Ctrl+C also exits with a friendly message.

## Validations

- Required text fields (`customer_name`, `address`) cannot be empty or contain only spaces; leading and trailing spaces are trimmed.
- `package_count` must be an integer greater than 0. Non-numeric input is reported and the user returns to the menu.
- `priority` and `status` must be one of the accepted values (case-insensitive in the service).
- The ID typed for update and delete must be a number, and the pickup must exist; otherwise a message is shown (`Coleta #id não encontrada`).
- Deleting asks for confirmation (`s/n`) before removing the record.
- Invalid menu options and invalid ordering/filter choices show a message and never crash the program.
- Validation errors are raised as `ValueError`, and missing records as `LookupError`, both caught in the controller.

## SQL equivalents

| Repository method | Equivalent SQL |
|---|---|
| `create(...)` | `INSERT INTO pickups (customer_name, address, package_count, priority, status, created_at) VALUES (?, ?, ?, ?, ?, ?)` |
| `list_all("id")` | `SELECT * FROM pickups ORDER BY id` |
| `list_all("date")` | `SELECT * FROM pickups ORDER BY created_at DESC` |
| `get_by_id(id)` | `SELECT * FROM pickups WHERE id = ?` |
| `filter_by_status(status)` | `SELECT * FROM pickups WHERE status = ? ORDER BY id` |
| `filter_by_priority(priority)` | `SELECT * FROM pickups WHERE priority = ? ORDER BY id` |
| `filter_by_name(term)` | `SELECT * FROM pickups WHERE lower(customer_name) LIKE lower('%term%') ORDER BY id` |
| `update_status(id, status)` | `UPDATE pickups SET status = ? WHERE id = ?` (after a `SELECT` by id) |
| `delete(id)` | `DELETE FROM pickups WHERE id = ?` (after a `SELECT` by id) |

## JSON vs. relational database

With the JSON file, every read loaded the whole file into memory, and every change rewrote it. Filtering and sorting were done by hand in Python, and nothing prevented invalid or missing fields from being saved.
The relational database stores each pickup as a row in a typed table, with a primary key, required columns and defaults enforced by the schema. Queries (`WHERE`, `ORDER BY`) run inside the database, and the ORM maps rows to Python objects, so the code does not write SQL by hand.
Separating the code into controller, service and repository also isolates the database access in one place, which makes it easier to change or test.

## Author

João Vitor
