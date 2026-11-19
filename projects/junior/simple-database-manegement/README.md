# simple-database-manegement

FilaFácil Logística, relational database module. A terminal application that stores pickup requests in a local SQLite database, through a 3-layer architecture and an ORM.

## 1. The problem and the solution

The earlier pickup system kept every request in a local JSON file. Every read loaded the whole file, every change rewrote it, and filtering was done by hand in Python. Nothing stopped an invalid or missing field from being saved.

This project moves those requests into one typed table. There is no web interface and no API.

## 2. Technologies

- Python 3.11+
- SQLite (local file `filafacil.db`)
- SQLAlchemy 2.x (`DeclarativeBase` / `Mapped` / `mapped_column` style)

## 3. Project structure

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

## 4. How to run

```bash
cd projects/junior/simple-database-manegement
python3 -m venv .venv              # Windows: python -m venv .venv
source .venv/bin/activate          # Windows (PowerShell): .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

Python 3.11 or newer. After the virtual environment is active, `python` is the interpreter inside it.

### Tests

This project has no automated test suite.

## 5. How to use

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

## 6. Data

Single table: `pickups`, in the local file `filafacil.db`. The file is created automatically on the first run. To reset the database, delete the file; it is recreated on the next run.

| Column | Type | Rules |
|---|---|---|
| `id` | Integer | Primary key, autoincrement |
| `customer_name` | String(100) | Required |
| `address` | String(200) | Required |
| `package_count` | Integer | Required, must be greater than 0 |
| `priority` | String(10) | `low`, `medium` or `high`; default `medium` |
| `status` | String(20) | `pending`, `in_transit`, `collected` or `canceled`; default `pending` |
| `created_at` | DateTime | Filled automatically on insert |

The table also has `CHECK` constraints, so the database itself rejects `package_count <= 0` and any `priority` or `status` outside the accepted values, even for inserts that bypass the application.

The database always stores the English values. The menu shows Portuguese labels:

| `priority` | Menu label | | `status` | Menu label |
|---|---|---|---|---|
| `low` | Baixa | | `pending` | Pendente |
| `medium` | Média | | `in_transit` | Em rota |
| `high` | Alta | | `collected` | Coletada |
| | | | `canceled` | Cancelada |

This status set is not the Module 1 set. Module 1 uses `pending`, `in_transit` and `completed`. This project uses `pending`, `in_transit`, `collected` and `canceled`.

## 7. Validations

- Required text fields (`customer_name`, `address`) cannot be empty or contain only spaces; leading and trailing spaces are trimmed.
- `package_count` must be an integer greater than 0. Non-numeric input is reported and the user returns to the menu.
- `priority` and `status` must be one of the accepted values (case-insensitive in the service).
- The ID typed for update and delete must be a number, and the pickup must exist; otherwise a message is shown (`Coleta #id não encontrada`).
- Deleting asks for confirmation (`s/n`) before removing the record.
- Invalid menu options and invalid ordering/filter choices show a message and never crash the program.
- Validation errors are raised as `ValueError`, and missing records as `LookupError`, both caught in the controller.

## 8. SQL equivalents

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

## 9. JSON vs. relational database

With the JSON file, every read loaded the whole file into memory, and every change rewrote it. Filtering and sorting were done by hand in Python, and nothing prevented invalid or missing fields from being saved.
The relational database stores each pickup as a row in a typed table, with a primary key, required columns and defaults enforced by the schema. Queries (`WHERE`, `ORDER BY`) run inside the database, and the ORM maps rows to Python objects, so the code does not write SQL by hand.
Separating the code into controller, service and repository also isolates the database access in one place, which makes it easier to change or test.

## 10. Restrictions

No web interface and no API. The database is a local SQLite file. The project has no secrets.

## 11. Author

João França
