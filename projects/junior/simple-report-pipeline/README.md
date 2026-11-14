# simple-report-pipeline

[![pipeline](https://github.com/joaoneres/ai-engineering-journey/actions/workflows/simple-report-pipeline.yml/badge.svg)](https://github.com/joaoneres/ai-engineering-journey/actions/workflows/simple-report-pipeline.yml)

FilaFácil Logística, CI/CD module. The application is deliberately small (an operational report
for pickups); the point of the project is the **automated delivery**: format check, lint, static
analysis, tests, build, a versioned and traceable artifact, and a publication that only happens when
every previous step passed.

## 1. The problem and the solution

Builds and releases were manual: inconsistent validations, wrong artifacts and no trace of which
version was built, tested and published. This project replaces that with a GitHub Actions pipeline
whose jobs depend on each other, so a failure in any step blocks everything after it.

## 2. Technologies

- Python 3.11+ (tested on 3.11 and 3.13), standard library only at runtime
- GitHub Actions (the only CI/CD provider)
- Dev tools, pinned in `requirements-dev.txt`: `ruff` (format and lint), `build`, `twine`
- Release scripts in `scripts/` use only the standard library

## 3. Project structure

```
.github/workflows/simple-report-pipeline.yml   # the workflow (repository root: a GitHub requirement)
projects/junior/simple-report-pipeline/
├── pyproject.toml            # metadata, version (single source of truth), ruff config
├── requirements-dev.txt      # ruff, build, twine with fixed versions
├── src/simple_report_pipeline/
│   ├── formatting.py         # status/priority labels and summary text (reusable utility)
│   ├── report.py             # pure rules: validate records, build the summary
│   └── cli.py                # `simple-report pickups.json [--format text|json]`
├── scripts/
│   ├── check_version.py      # semantic version, and tag == version on tag builds
│   ├── build_manifest.py     # writes dist/manifest.json
│   ├── publish.py            # checksums, secrets, no-duplicate publication, Release
│   └── run_local.py          # runs the whole pipeline on this machine
├── config/{dev,homolog,prod}.env   # per-environment settings (never secrets)
├── samples/pickups.json
├── tests/                    # 21 unittest tests
├── PIPELINE.md               # where the workflow lives and why
└── README.md
```

## 4. Running locally

```bash
cd projects/junior/simple-report-pipeline
python3.13 -m venv .venv && source .venv/bin/activate      # any Python 3.11+
pip install -r requirements-dev.txt && pip install -e .

simple-report samples/pickups.json                  # text report
simple-report samples/pickups.json --format json    # JSON report
simple-report --version

python -m unittest discover -s tests -t .           # tests
ruff format --check . && ruff check .               # format and lint
```

### Simulating the whole pipeline locally

The workflow only orchestrates: every step runs a command that also runs on your machine.

```bash
python scripts/run_local.py --env homolog      # Qualidade -> Testes -> Build -> Publicar
python scripts/run_local.py --stage qualidade  # a single stage
python scripts/run_local.py --env prod         # fails: PUBLISH_TOKEN is required in prod
PUBLISH_TOKEN=any-value python scripts/run_local.py --env prod
```

It prints the same job names as GitHub, stops at the first failure and marks the next stages as
`PULADO`. Publishing locally writes to `registry/<env>/<id>/` (ignored by git).

What only exists on GitHub: the triggers, the Environments, the automatic `GITHUB_TOKEN`, artifact
upload/download, the Release, `concurrency` and the run summary.

## 5. Pipeline

```
Qualidade ──► Testes (3.11 e 3.13) ──► Build ──► Publicar
```

| Job | What it does | Blocks when |
| --- | --- | --- |
| `Qualidade` | install dependencies, `ruff format --check`, `ruff check`, `compileall` | formatting, lint or static error |
| `Testes` | `pip install -e .`, unit tests, runs the CLI end to end (3.11 and 3.13) | any test fails |
| `Build` | version check (and tag), `python -m build`, `twine check --strict`, `manifest.json`, stores the artifact | invalid version, build or metadata |
| `Publicar` | verifies checksums, checks secrets, skips duplicates, publishes, writes the run summary | missing secret, checksum, publication failure |

Every job is named `simple-report-pipeline · <Job>`, and `needs` makes the dependency explicit.

### Triggers

| Event | Runs | Publishes? |
| --- | --- | --- |
| push to `feature/**`, `fix/**`, `chore/**`, `docs/**`, `ci/**` | Qualidade, Testes, Build | no |
| pull request to `main` | Qualidade, Testes, Build | no |
| push to `main` | everything | yes, **homolog** (artifact `registry-...`) |
| tag `simple-report-vX.Y.Z` | everything | yes, **prod** (GitHub Release with wheel, sdist and manifest) |
| manual run (`workflow_dispatch`, input `environment`) | everything | `dev` from any branch; `homolog`/`prod` only from `main` or a tag |

The workflow only reacts to changes under `projects/junior/simple-report-pipeline/` and to the
workflow file itself. The tag carries the project prefix because the repository holds many projects.

## 6. Environments, variables and secrets

| Environment | `config/*.env` | `PUBLISH_TOKEN` required |
| --- | --- | --- |
| `dev` | `RUN_MODE=validate` | no |
| `homolog` | `RUN_MODE=publish` | no |
| `prod` | `RUN_MODE=release` | **yes** |

- Workflow-level variables: `PROJECT_NAME`, `PROJECT_DIR`, `ARTIFACT_DIR`. Per-environment
  variables come from `config/<env>.env`. These files never hold secrets.
- The three GitHub Environments (`dev`, `homolog`, `prod`) were created by the first runs that
  referenced them.
- `GITHUB_TOKEN` is provided by GitHub and is used to create the Release.
- `PUBLISH_TOKEN` simulates the credential of a registry. To enable `prod`: repository *Settings →
  Environments → prod → Environment secrets → Add secret* named `PUBLISH_TOKEN` (any value; nothing
  real is called).
- `scripts/publish.py` prints only the **name** of a secret and whether it exists, never its value.
  Nothing sensitive is in the code, in the workflow or in the logs.
- **Least privilege:** the workflow runs with `contents: read`. Only `Publicar` also gets
  `contents: write` (create the Release) and `actions: read` (look for an existing publication).
  Third-party actions are pinned to the commit SHA.

## 7. Artifact and traceability

Every build produces `dist-<version>-<sha7>` with the wheel, the source distribution and
`manifest.json`:

```json
{
  "project": "simple-report-pipeline",
  "version": "1.0.0",
  "commit": "<full commit sha>",
  "environment": "dev",
  "published_at": null,
  "status": "built",
  "files": { "<file name>": "<sha256>" }
}
```

On publication the manifest is rewritten with `status: "published"` and `published_at` (UTC), and
stored next to the files as `registry-<environment>-<version>-<sha7>`. For tags, the same files are
attached to the GitHub Release. Version is the single source of truth in `pyproject.toml`; a tag
build fails if `simple-report-vX.Y.Z` does not match it.

## 8. Re-running without duplicating

The publication id is `<environment>-<version>-<sha7>`. Before publishing, `publish.py` looks for an
existing artifact with that id (and for an existing Release when there is a tag). If it exists, the
job succeeds saying `já publicado; nada a fazer (sem duplicar)`. `concurrency` queues publications of
the same environment instead of running them in parallel. Re-running jobs or dispatching again never
creates a second artifact.

## 9. Diagnosing failures

Each failure below was reproduced in a real run (the throwaway branches were deleted afterwards).
In every case the next jobs show as *skipped* and `Publicar` never runs.

| Failure | Fails in | Log signal | Run |
| --- | --- | --- | --- |
| Installation | `Qualidade` › *Instalar dependências* | pip: `Could not find a version that satisfies the requirement ruff==...` | [run](https://github.com/joaoneres/ai-engineering-journey/actions/runs/43541011818) |
| Lint | `Qualidade` › *Lint (ruff check)* | ``F401 `os` imported but unused`` | [run](https://github.com/joaoneres/ai-engineering-journey/actions/runs/43541015460) |
| Test | `Testes` › *Testes unitários* (both Pythons) | `FAIL: test_empty_list_gives_zeroes` | [run](https://github.com/joaoneres/ai-engineering-journey/actions/runs/43541018159) |
| Build | `Build` › *Checar versão* | `[build] versão inválida: versão '1.0' não é semântica` | [run](https://github.com/joaoneres/ai-engineering-journey/actions/runs/43541358325) |
| Publication | `Publicar` › *Publicar...* | `[publicar] ERRO: checksum diverge ...` (exit code 4) | [run](https://github.com/joaoneres/ai-engineering-journey/actions/runs/43541050588) |
| Missing secret | `Publicar` › *Publicar...* | `[publicar] ERRO: secret ausente: PUBLISH_TOKEN` (exit code 3) | [run](https://github.com/joaoneres/ai-engineering-journey/actions/runs/43541053269) |

How to read a failed run: open the run, find the red job, open the red step. `scripts/publish.py`
exit codes: 2 bad manifest, 3 secret missing, 4 checksum mismatch, 5 publication failed.
Reproduce any of them with `python scripts/run_local.py`.

## 10. Releasing a version

1. Change `version` in `pyproject.toml` and merge it to `main` (publishes to homolog).
2. Create the tag and push it:
   ```bash
   git tag simple-report-v1.0.0 && git push origin simple-report-v1.0.0
   ```
3. The pipeline runs against `prod`, needs the `PUBLISH_TOKEN` secret (section 6) and creates the
   GitHub Release with the wheel, the sdist and `manifest.json`.

## 11. Making the checks block merges (one-time repository setting)

The pipeline reports the checks, but only the repository settings can *enforce* them: *Settings →
Branches → Add rule for `main` → Require status checks* and select `simple-report-pipeline ·
Qualidade`, `· Testes (3.11)`, `· Testes (3.13)` and `· Build`. Note that the workflow only runs for
changes in this project, so a required check would stay pending on pull requests that touch only
other projects; add a path-independent job or use a ruleset if that becomes a problem.

## 12. Restrictions respected

No real deployment, no Kubernetes, a single CI/CD provider, no paid or external registry, no
secrets in the repository and a small test suite.

## 13. Author

João Vitor
