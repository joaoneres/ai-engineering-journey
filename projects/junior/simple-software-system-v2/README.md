# FilaFácil Logística — Module 2

## 1. The problem and the solution

Module 1 worked, but the code was concentrated in a few files, with long functions, duplicated logic, no tests, no shared state and no external integration.
Module 2 evolves the same terminal system: it is split into layers, calls a REST API (ViaCEP) when a pickup is registered, keeps a central application state, handles errors by origin and has unit tests for the business rules.

Still a local terminal application: no web interface, no database, no authentication, no heavy framework.

## 2. Technologies

- Python 3.11+
- Standard library only: `asyncio`, `urllib`, `json`, `dataclasses`, `logging`, `unittest`
- External API: **ViaCEP** (public, no key): `https://viacep.com.br/ws/{cep}/json/`

## 3. Project structure

```
simple-software-system-v2/
├── main.py                       # entry point
├── constants.py                  # priorities, statuses, labels, API settings
├── errors.py                     # InputError, FileError, ApiError (+ NotFoundError)
├── domain/pickups.py             # pure business rules (no input, print, file or network)
├── state/app_state.py            # central immutable state
├── storage/json_storage.py       # async, atomic read/write of pickups.json
├── integrations/cep_client.py    # ViaCEP client (isolated, with timeout and typed errors)
├── services/pickup_service.py    # use cases: API -> rules -> save -> log
├── ui/cli.py                     # terminal input/output helpers
├── ui/menu.py                    # menu loop and actions
├── tests/                        # unit tests
├── pickups.json                  # data (created automatically)
└── filafacil.log                 # technical logs (created automatically)
```

| Layer | Responsibility | Knows about |
| --- | --- | --- |
| `ui` | Reads input, prints output, updates the state | state, services, domain |
| `services` | Orchestrates one use case: call the API, apply the rule, save, log | domain, integrations, storage |
| `state` | Holds the list of pickups, loading flag, last error and active filters | domain |
| `integrations` | The only code that talks to the REST API | domain (CEP format), errors |
| `storage` | The only code that touches `pickups.json` | domain (validation), errors |
| `domain` | Pure functions: validate, create, filter, update, summarize | errors, constants |

## 4. How to run

No installation needed, only Python 3.11 or newer.

```bash
git clone https://github.com/joaoneres/ai-engineering-journey.git
cd ai-engineering-journey/projects/junior/simple-software-system-v2
python3 main.py          # Windows: python main.py
```

## 5. How to run the tests

```bash
python3 -m unittest discover -s tests -t .
```

The tests use no network and never touch the real `pickups.json` (fake API transport and temporary files).

| File | What it covers |
| --- | --- |
| `test_pickups.py` | creation, validation, CEP format, filters, status update, summary |
| `test_state.py` | state transitions, errors by origin, combined filters, immutability |
| `test_cep_client.py` | API response parsing, unknown CEP, invalid JSON, network failure |
| `test_storage.py` | missing/invalid file, round trip, failed write keeps the previous file |
| `test_service.py` | registration with/without API data, API and file failures |

## 6. How to use

```
=== FilaFácil Logística ===
1. Cadastrar coleta
2. Listar coletas
3. Filtrar por status
4. Filtrar por prioridade
5. Atualizar status
6. Resumo operacional
7. Limpar filtros
0. Sair
```

**1. Register pickup**: asks for name, address, an optional CEP (press Enter to skip), package count and priority.

```
Nome do cliente: Maria Souza
Endereço: Rua das Flores, 123
CEP (Enter para pular): 01001-000
Quantidade de pacotes: 3
Prioridade: 3 (Alta)
>> Consultando CEP...
>> Coleta #1 cadastrada
```

**2. List pickups** shows the pickups that match the active filters (all of them if there are none), sorted by ID, with the city/UF returned by the API.

```
ID   | Cliente      | Endereço            | Cidade/UF    | Pacotes | Prioridade | Status
1    | Maria Souza  | Rua das Flores, 123 | São Paulo/SP |       3 | Alta       | Pendente
```

**3 and 4. Filters** by status and by priority. They are stored in the state, so they combine (status **and** priority) and stay active for the option 2 listing until **7. Limpar filtros**.

**5. Update status**, **6. Operational summary** and **0. Quit** work as in Module 1.

## 7. REST API and async flow

- API used: **ViaCEP** (`GET https://viacep.com.br/ws/{cep}/json/`). The JSON response gives `logradouro`, `bairro`, `localidade` and `uf`.
- Registration `await`s the API **before** saving: a pickup is never finalized before the response arrives or the failure is handled.
- The blocking `urllib` call (and the file I/O) runs in `asyncio.to_thread`, so the code uses `async/await` end to end. Timeout: 5 seconds.
- If the API fails (no network, timeout, HTTP error, unknown CEP, invalid JSON), the user sees a clear message and chooses: register **without** CEP data (`"enriched": false`) or cancel. The system never crashes.
- The client accepts an injectable `transport`, which is how the tests simulate the API offline.

Stored data (CEP fields appear only when the API answered):

```json
{
  "id": 1, "customer_name": "Maria Souza", "address": "Rua das Flores, 123",
  "package_count": 3, "priority": "high", "status": "pending",
  "enriched": true, "cep": "01001-000", "street": "Praça da Sé",
  "neighborhood": "Sé", "city": "São Paulo", "state": "SP"
}
```

Files created by Module 1 keep working: the CEP fields are optional.

## 8. Application state

`state/app_state.py` defines an immutable `AppState` with:

| Field | Meaning |
| --- | --- |
| `pickups` | list of pickups |
| `loading` | `True` while an action (file or API call) is running |
| `last_error` | `{"kind": "input" \| "file" \| "api", "message": ...}` or `None` |
| `filters` | active filters, e.g. `{"status": "pending", "priority": "high"}` |

Every transition (`set_pickups`, `set_loading`, `set_error`, `clear_error`, `set_filter`, `clear_filters`) returns a new state, and `visible_pickups` applies the filters.

## 9. Error handling

| Origin | Error | Example | Behavior |
| --- | --- | --- | --- |
| User input / rules | `InputError`, `NotFoundError` | empty name, invalid CEP, unknown ID | message, state unchanged |
| Data file | `FileError` | disk full, no permission | message, pickup not added; the previous file stays intact (atomic write) |
| REST API | `ApiError` | no network, timeout, CEP not found | message, register without CEP data or cancel |

A missing, empty or corrupted `pickups.json` at startup makes the system start with an empty list. `Ctrl+C` and `Ctrl+D` exit with a friendly message. Technical details go to `filafacil.log`.

## 10. Git workflow

Work done on branch `feature/module-2-refactor-api-tests`, with one commit per phase (refactor, API + async, state + errors, tests + docs), then a Pull Request merged into `main`.

## 11. Author

João França
