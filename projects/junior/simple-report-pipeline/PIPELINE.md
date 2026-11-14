# Pipeline

The CI/CD workflow of this project is
[`.github/workflows/simple-report-pipeline.yml`](../../../.github/workflows/simple-report-pipeline.yml).

**Why is it outside this folder?** GitHub Actions only runs workflow files that live in
`.github/workflows/` at the **repository root**. The repository holds several projects, so the
workflow is named after this folder, every job is prefixed with `simple-report-pipeline ·`, and it
only reacts to changes inside `projects/junior/simple-report-pipeline/` (plus the workflow file).

**Where to see the runs:** the *Actions* tab of the repository, workflow `simple-report-pipeline`,
or `gh run list --workflow simple-report-pipeline.yml`.

The jobs run in order and each one needs the previous one:

```
Qualidade ──► Testes (py 3.11 e 3.13) ──► Build ──► Publicar
```

The full description (triggers, environments, secrets, artifact, failure diagnosis) is in the
[README](README.md).
