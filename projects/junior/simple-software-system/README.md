# FilaFácil Logística

## 1. The problem and the solution

The company used to receive pickup requests by message and write everything down in manual spreadsheets, which caused mistakes and made it hard to know what was still pending.
FilaFácil is a terminal system that registers, lists, filters, updates and summarizes pickups, keeping everything in a single local file.

## 2. Technologies

- Python 3.11+
- Standard library only: `json`, `pathlib`, `logging` and `functools`
- No database, no frameworks and no external dependencies

## 3. Project structure

```
simple-software-system/
├── main.py        # menu loop and calls to the actions
├── pickups.py     # business rules (no input/print)
├── storage.py     # the only module that reads and writes pickups.json
├── cli.py         # terminal input and output (validated reading, table, summary)
├── constants.py   # priorities, statuses, Portuguese labels and file names
├── pickups.json   # data (created automatically)
└── filafacil.log  # technical logs (created automatically)
```

| File | Responsibility |
| --- | --- |
| `main.py` | Shows the menu, reads the option and calls the actions. No business rules. |
| `pickups.py` | Register, list, filter, update status and summarize. Never uses `input()` or `print()`. |
| `storage.py` | Reads and writes `pickups.json`. No other module touches the file. |
| `cli.py` | Reads numbers and text with validation and prints messages, tables and the summary. |
| `constants.py` | `PRIORITIES`, `STATUSES`, Portuguese labels and file names. |

## 4. How to run

There is nothing to install. You only need Python 3.11 or newer.

```bash
git clone https://github.com/joaoneres/ai-engineering-journey.git
cd ai-engineering-journey/projects/junior/simple-software-system
```

Linux and macOS:

```bash
python3 main.py
```

Windows:

```bat
python main.py
```

## 5. How to use

The user interface is in Portuguese, so the examples below show the program output exactly as it appears on screen. The menu loops until you choose `0`:

```
=== FilaFácil Logística ===
1. Cadastrar coleta        (Register pickup)
2. Listar coletas          (List pickups)
3. Filtrar por status      (Filter by status)
4. Filtrar por prioridade  (Filter by priority)
5. Atualizar status        (Update status)
6. Resumo operacional      (Operational summary)
0. Sair                    (Quit)
```

The English notes in parentheses are only for this README; the program does not print them.

**1. Register pickup**: asks for the customer name, address, package count and priority.

```
Nome do cliente: Maria Souza
Endereço: Rua das Flores, 123
Quantidade de pacotes: 3
Prioridade:
1. Baixa
2. Média
3. Alta
Escolha uma opção: 3
>> Coleta #1 cadastrada
```

**2. List pickups**: shows all pickups, sorted by ID.

```
ID   | Cliente              | Endereço                       | Pacotes | Prioridade | Status
------------------------------------------------------------------------------------------------
1    | Maria Souza          | Rua das Flores, 123            |       3 | Alta       | Pendente
2    | João Lima            | Av. Brasil, 45                 |      10 | Baixa      | Pendente
```

**3. Filter by status**: choose a status and see only its pickups.

```
Status:
1. Pendente
2. Em rota
3. Concluída
Escolha uma opção: 3
>> Nenhuma coleta encontrada
```

**4. Filter by priority**: choose `3` (Alta) and the table shows only pickup #1.

**5. Update status**: enter the ID, see the current pickup and choose the new status.

```
ID da coleta: 1
(table with pickup #1)
Novo status:
1. Pendente
2. Em rota
3. Concluída
Escolha uma opção: 2
>> Status da coleta #1 atualizado para Em rota
```

**6. Operational summary**

```
===== Resumo operacional =====
Total de coletas: 2 | Total de pacotes: 13
Por prioridade: Alta 1 | Média 0 | Baixa 1
Por status: Pendente 1 | Em rota 1 | Concluída 0
```

**0. Quit**: prints `>> Até logo!` and exits.

## 6. Data and persistence

The data lives in `pickups.json`, in the project folder. The file is created automatically on the first registration.

```json
[
  {
    "id": 1,
    "customer_name": "Maria Souza",
    "address": "Rua das Flores, 123",
    "package_count": 3,
    "priority": "high",
    "status": "pending"
  }
]
```

The file stores English values and the menu shows Portuguese labels:

| Field | Stored value | Shown in the menu |
| --- | --- | --- |
| `priority` | `low` | Baixa |
| `priority` | `medium` | Média |
| `priority` | `high` | Alta |
| `status` | `pending` | Pendente |
| `status` | `in_transit` | Em rota |
| `status` | `completed` | Concluída |

Every pickup starts with status `pending`. The `id` is generated locally (highest existing id + 1).

## 7. Where map, filter and reduce are used

| Function | Where | Why |
| --- | --- | --- |
| `filter` | `filter_by_status`, `filter_by_priority` | It only decides whether each pickup stays in or out of the list. |
| `filter` + `next` | `find_by_id` | Stops at the first pickup with the requested id and returns `None` if there is none. |
| `map` | `print_table` (with `to_display_row`) | Turns each pickup into a line of text. |
| `map` | `update_status` | Changes the status only of the pickup with the requested id and keeps the others, without changing the original list. |
| `map` | `load_pickups` (with `is_valid_pickup`) | Validates each record read from the file. |
| `reduce` | `build_summary` (`total_packages`) | Adds up the packages of all pickups into a single number. |
| `reduce` | `count_by` (`by_priority`, `by_status`) | Accumulates a dictionary of counts that already includes the categories with 0. |

## 8. Validation and error handling

- Name and address never accept empty text or only spaces. The text is saved without leading or trailing spaces.
- The package count must be an integer greater than zero. Letters, negative numbers and huge numbers are rejected with a message.
- A nonexistent option, or a letter where a number is expected, shows a message and asks again.
- Priority and status only accept the values defined in `constants.py`.
- A nonexistent ID, or a new status equal to the current one, shows a message and changes nothing.
- First run without a file, an empty file, invalid JSON, records in the wrong format or an unreadable file: the system starts with an empty list instead of crashing.
- If writing the file fails, the user gets a warning and the pickup is not added to the in-memory list.
- `Ctrl+C` and end of input (`Ctrl+D`) exit with a friendly message and no traceback.

## 9. Logs

Technical logs go only to `filafacil.log` (never to the terminal), with date, time, level and message. The following is recorded:

- `Sistema iniciado` and `Sistema encerrado` (system started and stopped)
- Data file not found (INFO) or invalid (WARNING)
- The number of pickups saved on every write
- Every registration, with id and customer
- Every update, with id, previous status and new status
- Failures when writing the file (ERROR), with the error details

## 10. Author

João França
