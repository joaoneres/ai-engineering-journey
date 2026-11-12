# FilaFácil Logística (Module 3: layered architecture)

## 1. The problem and the solution

FilaFácil is a terminal system that registers, lists, filters, updates and summarizes pickups, keeping everything in a single local file.

The first version (`simple-software-system`) worked, but menu, business rules, error handling and file access were mixed in the same functions: `create_pickup` read the terminal, applied the rules and wrote the file at the same time. Every change touched several places.

This version is a **pure refactor**. It reorganizes the same code into three layers, **Controller → Service → Repository**, without adding features. The menu, the messages and the `pickups.json` format are exactly the same as in Module 1, and a smoke test proves it (section 6).

## 2. Technologies

- Python 3.11+
- Standard library only: `json`, `pathlib`, `logging`, `functools`
- No database, no frameworks, no API and no external dependencies

## 3. Project structure

```
simple-software-system-v3/
├── main.py              # entry point: configures logging and starts the controller
├── controller.py        # CONTROLLER: menu, reads the terminal, calls the service
├── service.py           # SERVICE: business rules and use cases
├── repository.py        # REPOSITORY: the only module that touches pickups.json
├── cli.py               # terminal input/output helpers (validated reading, table, summary)
├── constants.py         # priorities, statuses, Portuguese labels and file names
├── smoke_test.py        # runs the real app with scripted input and compares the output
├── smoke_expected.txt   # reference output recorded from Module 1
├── pickups.json         # data (created automatically)
└── filafacil.log        # technical logs (created automatically)
```

| File | Layer | Responsibility | Never does |
| --- | --- | --- | --- |
| `controller.py` | Controller | Shows the menu, reads the option and the fields (through `cli`), calls the service and prints the result. | Business rules, file access, logging. |
| `service.py` | Service | Validates, registers, filters, updates status and summarizes. Decides what is valid and saves through the repository. | `input()`, `print()`, knowing the file format. |
| `repository.py` | Repository | Reads and writes `pickups.json`. | Business rules, terminal. |
| `cli.py` | Interface helper | Reads numbers and text with validation, prints messages, table and summary. | Rules, files. |
| `main.py` | Entry | Configures logging and calls `controller.run()`. | Everything else. |

### How the layers talk

```
main.py ──► controller.py ──► service.py ──► repository.py ──► pickups.json
               │
               └──► cli.py   (terminal input and output)
```

- Each layer only knows the one directly below it. The controller never imports `repository`.
- Errors cross the layers in a controlled way: the repository raises `RepositoryError`, the service turns it into `SaveError` (and raises `ValueError`/`LookupError` for invalid data), and the controller turns all of them into messages. The terminal never shows a traceback.
- Replacing the JSON file by another storage would only change `repository.py`.

### Example: registering a pickup

1. `controller.create_pickup` reads name, address, packages and priority through `cli`.
2. It calls `service.register_pickup(...)`.
3. The service loads the pickups, validates the data, builds the new pickup, saves it through the repository and logs it.
4. The controller prints `>> Coleta #N cadastrada`, or the error message if something failed.

## 4. How to run

There is nothing to install. You only need Python 3.11 or newer.

```bash
git clone https://github.com/joaoneres/ai-engineering-journey.git
cd ai-engineering-journey/projects/junior/simple-software-system-v3
python3 main.py        # Linux and macOS
python main.py         # Windows
```

## 5. How to use

The interface is in Portuguese and identical to Module 1. The menu loops until you choose `0`:

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

The English notes in parentheses are only for this README. Examples of every screen are in the Module 1 README.

## 6. How to verify that the behavior did not change

```bash
python3 smoke_test.py
```

It runs the real `main.py` from a temporary copy (your `pickups.json` and `filafacil.log` are never touched) in four scripted sessions: registrations with invalid inputs, filters, status updates (nonexistent id, same status), summary, a second run that loads the saved data, a corrupted `pickups.json`, and an input that ends without `0` (like `Ctrl+D`). The terminal output is compared with `smoke_expected.txt`, which was recorded from the Module 1 code. `OK` means the refactor kept the behavior.

You can also run it against another folder: `python3 smoke_test.py ../simple-software-system`.

## 7. Data and persistence

Same as Module 1: `pickups.json` in the project folder, created on the first registration, with English stored values (`low/medium/high`, `pending/in_transit/completed`) and Portuguese labels in the menu. A file created by Module 1 loads without any migration. The `id` is generated locally (highest existing id + 1).

The service reads the file on each operation instead of keeping a list in memory, so the controller holds no state.

## 8. Where map, filter and reduce are used

| Function | Where | Why |
| --- | --- | --- |
| `filter` | `filter_by` | One function now filters by status or priority (it replaced two near-identical ones). |
| `filter` + `next` | `find_by_id` | Stops at the first pickup with the requested id. |
| `map` | `with_new_status` | Changes only the pickup with the requested id, without altering the original list. |
| `map` | `load_pickups` (with `is_valid_pickup`) | Validates each record read from the file. |
| `map` | `cli.print_table` | Turns each pickup into a line of text. |
| `reduce` | `build_summary`, `count_by` | Adds up packages and accumulates counts per category (including categories with 0). |

## 9. Validation and error handling

- Name and address never accept empty text; the package count must be an integer greater than zero; priority and status only accept the values in `constants.py`.
- A nonexistent option, ID, or a new status equal to the current one shows a message and changes nothing.
- Missing file, empty file, invalid JSON or records in the wrong format: the system starts with an empty list.
- If writing the file fails, the user gets a warning and nothing is saved.
- `Ctrl+C` and end of input exit with a friendly message and no traceback.

## 10. Logs

Technical logs go only to `filafacil.log`: start and stop, file problems, every write, every registration and every status update (the service logs them, since they are business events).

## 11. What changed from Module 1

| Module 1 | Module 3 |
| --- | --- |
| `main.py` with menu, handlers, rules calls, saving and logging (131 lines) | `main.py` (24 lines) + `controller.py` |
| `pickups.py` (rules only, state kept by `main.py`) | `service.py` (rules + use cases that load, save and log) |
| `storage.py` called by the interface | `repository.py` called only by the service |
| `filter_by_status` + `filter_by_priority`, `show_by_status` + `show_by_priority` | `filter_by`, `show_filtered` |
| Save-or-warn block repeated in two handlers | One `save_pickups` in the service, one `SaveError` handling in the controller |
| `if/elif` chain in the menu loop | `ACTIONS` table |

## 12. Author

João Vitor
