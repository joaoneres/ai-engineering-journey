# Pipeline

The CI/CD workflow of this project is
[`.github/workflows/simple-manifest-validator.yml`](../../../.github/workflows/simple-manifest-validator.yml).

**Why is it outside this folder?** GitHub Actions only runs workflow files that live in
`.github/workflows/` at the **repository root**. The repository holds several projects, so the
workflow is named after this folder, every job is prefixed with `simple-manifest-validator ·`, and it
only reacts to changes inside `projects/junior/simple-manifest-validator/` (plus the workflow file).

**Where to see the runs:** the *Actions* tab of the repository, workflow `simple-manifest-validator`,
or `gh run list --workflow simple-manifest-validator.yml`.

The jobs run in order. Deploy does not start unless Integration passed, and it does not run on a
pull request:

```
Integration ──► Deploy
```

Integration installs the pinned tools, checks formatting and lint, runs the tests, and runs the CLI
on both sample manifests. Deploy builds the wheel and the sdist, uploads that artifact, and, on a
tag `simple-manifest-vX.Y.Z`, publishes the GitHub Release.

The full description (triggers, the version tag, and the artifact) is in the [README](README.md).
