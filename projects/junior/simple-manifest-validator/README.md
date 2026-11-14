# simple-manifest-validator

[![pipeline](https://github.com/joaoneres/ai-engineering-journey/actions/workflows/simple-manifest-validator.yml/badge.svg)](https://github.com/joaoneres/ai-engineering-journey/actions/workflows/simple-manifest-validator.yml)

FilaFácil Logística, basic CI/CD case. The application validates a local cargo manifest. The point of the project is the delivery path around it: one integration job, then one deploy job that publishes an artifact only after integration passes.

`simple-report-pipeline` is a separate, larger pipeline study. This project does not change it.

## 1. The problem and the solution

Before a route leaves the distribution center, an analyst used to check the cargo manifest by hand: duplicate packages, empty routes, and records with no vehicle or no responsible person. A small change to that check had no automated way to be tested and published.

This project replaces the manual check with a terminal command, and replaces the manual release with a GitHub Actions workflow.

## 2. Technologies

- Python 3.11+, standard library only at runtime
- GitHub Actions (the only CI/CD provider)
- Dev tools, pinned in `requirements-dev.txt`: `ruff` (format and lint), `build`, `twine`

## 3. Project structure

```
.github/workflows/simple-manifest-validator.yml   # the workflow (repository root: a GitHub requirement)
projects/junior/simple-manifest-validator/
├── pyproject.toml                 # metadata and version (single source of truth)
├── requirements-dev.txt           # ruff, build, twine with fixed versions
├── src/simple_manifest_validator/
│   ├── manifest.py                # read JSON or CSV, validate, build the report data
│   ├── formatting.py              # render the report as text
│   └── cli.py                     # `simple-manifest manifest.json|csv [--output file]`
├── scripts/
│   ├── check_version.py           # semantic version, and tag == version on tag builds
│   └── run_local.py               # runs integration and build on this machine
├── samples/manifest.json
├── samples/manifest.csv
├── tests/
├── PIPELINE.md
└── README.md
```

## 4. What the validator checks

Each record has five text fields: `package`, `route`, `vehicle`, `responsible`, and `status`. `vehicle` is the vehicle assigned to carry that package, such as `Van 02`. The field only has to be present and non-blank. There is no fleet list and no closed list of statuses.

| Problem | Message |
| --- | --- |
| Package missing or blank | `missing package` |
| Same package on a later record | `duplicate package PKG-1` |
| Route missing or blank | `empty route` |
| Vehicle missing or blank | `missing vehicle` |
| Responsible person missing or blank | `missing responsible` |
| Status missing or blank | `missing status` |

The first copy of a package is kept. A rejected manifest still prints a report and exits 0. Exit code 1 means the file itself could not be read (missing file, invalid JSON, CSV without the required header, or a file that is neither JSON nor CSV).

```
===== Validation report =====
Records: 2
Errors: 0
Problems:
- none
Final status: approved
```

## 5. Running locally

```bash
cd projects/junior/simple-manifest-validator
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt && pip install -e .

simple-manifest samples/manifest.json
simple-manifest samples/manifest.csv --output report.txt
simple-manifest --version

python -m unittest discover -s tests -t . -v
ruff format --check . && ruff check .
```

`scripts/run_local.py` runs the same stages as the workflow, in order, and stops at the first failure. The next stage is marked `SKIPPED`.

```bash
python scripts/run_local.py                 # integration, then build
python scripts/run_local.py --stage integration
python scripts/run_local.py --install       # pip install the pinned tools first
```

The GitHub Release is the only step that does not run on this machine.

## 6. Pipeline

```
Integration ──► Deploy
```

| Job | When it runs | What it does |
| --- | --- | --- |
| Integration | push and pull request | install tools, formatting, lint, tests, CLI on both samples |
| Deploy | push to `main`, or a version tag, after Integration | version check, wheel and sdist, upload the artifact, and on a tag create the Release |

Push is limited to `main` and to branches named `feature/**`, `fix/**`, `chore/**`, `docs/**`, or `ci/**`. The workflow only reacts to changes under this project and to the workflow file itself. There is one environment. Nothing is deployed to a server.

The artifact is `simple-manifest-<version>-<sha7>` and contains the wheel, the sdist, and `validation-report.txt` from `samples/manifest.json`. The same report is written to the run summary. A tag `simple-manifest-vX.Y.Z` must match `version` in `pyproject.toml`, or Deploy fails. Re-running a tag that already has a Release does not create a second one.

How to see a run: the *Actions* tab, workflow `simple-manifest-validator`, or `gh run list --workflow simple-manifest-validator.yml`. Open the run, then the job. A failed step is red, and Deploy does not run when Integration fails.

## 7. Releasing a version

1. Set `version` in `pyproject.toml` and merge it to `main`. That push builds the artifact and does not create a Release.
2. Tag the merge commit and push the tag:

```bash
git tag simple-manifest-v1.0.0
git push origin simple-manifest-v1.0.0
```

3. Deploy runs again and creates the GitHub Release with the wheel, the sdist, and `validation-report.txt`.

The tag carries the project prefix because this repository holds more than one project.

## 8. Restrictions respected

No web interface, no database, no authentication, no Kubernetes, no cloud, and no second environment. The pipeline is two jobs. Runtime code uses the standard library only.

## 9. Author

João Vitor
