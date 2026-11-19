# Documentation guide

Every project in `projects/junior/` has one `README.md`. This file is the pattern. A new project copies it. An edit to an existing README keeps the same order.

`README.md` in this folder is the index, not a project README. It does not use the skeleton below. When a project is added, add one row there.

## Language

- The README is in English.
- Quote the program interface in Brazilian Portuguese, exactly as printed.
- Stored values stay in English (`pending`, not `Pendente`).
- An English gloss in parentheses belongs only in the README. One sentence says the program does not print that gloss.

## Files

- Path: `projects/junior/<folder>/README.md`.
- The H1 is the folder name, including a spelling that already shipped. Do not invent a prettier title.
- One extra document is allowed when a tool requires a file outside the project folder. `simple-report-pipeline/PIPELINE.md` exists because GitHub Actions only reads workflows from the repository root. That file says where the external file lives and why. The README still holds the full description.
- A status badge sits on the line under the H1 when the project has a public check the reader needs. The CI badge on `simple-report-pipeline` is the example.

## Opening

```markdown
# <folder-name>

FilaFácil Logística, <module>. <One sentence: what the program does.>
```

The module is `Module 1`, `Module 2`, `Module 3`, or a short name such as `CI/CD module`. The sentence states what this program does. The problem stays in section 1.

## Required sections, in this order

```markdown
## 1. The problem and the solution
## 2. Technologies
## 3. Project structure
## 4. How to run
### Tests
## 5. How to use
## 6. Data
## 7. …module-specific sections…
## N-1. Restrictions
## N. Author
```

Sections 1 to 6 use these titles. Module-specific sections keep a descriptive title, sit between Data and Restrictions, and follow the path a reader takes. Restrictions is always the penultimate section. Author is always the last. Renumber when a section is inserted, and update every `section N` reference, including references from a side file such as `PIPELINE.md`.

### 1. The problem and the solution

What was wrong, and what this project does about it. Name the earlier project when this one continues it.

### 2. Technologies

A bullet list: language, runtime version, libraries, and what is deliberately absent when that absence is part of the exercise (no database, no framework, no paid service).

### 3. Project structure

A fenced tree rooted at the project folder. Comment each entry. Add a responsibility table when the project is split into layers.

### 4. How to run

The first command is from the repository root:

```bash
cd projects/junior/<folder>
```

Do not repeat `git clone`. The reader is already in the repository.

Then the commands that install, only when the project has dependencies, and the command that starts the program. Show a Windows command on the same line when the command actually differs, as in the virtualenv activate path. `python3` versus `python` is a note on the run line, not a second block.

Document environment variables here: name, default, meaning. Never paste a real secret. Point at `.env.example` when it exists. A longer credentials explanation can be its own module section. How to run still names the variables.

#### Tests

Always present, as `### Tests`.

```bash
<the command>
```

One or two sentences on what the tests touch and what they avoid (network, the real data file). When there is no suite, write this sentence and nothing else:

```markdown
This project has no automated test suite.
```

A smoke script counts as the test command. Put the explanation under `### Tests`.

### 5. How to use

The menu, the page, or the CLI, in the order a person meets it. Keep the recorded examples. For a page with no menu, this section describes the fields and the actions.

### 6. Data

Where the data lives, a short example, and the stored-value / label table when the screen and the file differ. Say how the file or database is created and how to reset it.

The terminal pickup system stores status as `pending`, `in_transit`, and `completed`. A project that uses another set says so in this section.

### Module-specific sections

Keep the technical sections the project already needs: pipeline, rubrics, cost, logs, SQL, layers. Do not drop a fact to fit this guide. Do not add a section that repeats How to run or Data.

### Restrictions

The limits the exercise keeps on purpose: no real customer data, no secrets in the repository, no paid plan, no deployment, standard library only. When another section already holds the detail, this section is a short list and points at that section.

### Author

The body is exactly:

```markdown
João França
```

## Checklist

- H1 is the folder name.
- The opening line names FilaFácil Logística, the module, and what the program does.
- Sections 1 to 6 use the titles above, in that order.
- `### Tests` is present under How to run.
- The first command is `cd projects/junior/<folder>`.
- The README does not start with `git clone`.
- Restrictions is penultimate. Author is last and reads `João França`.
- A status set other than `pending` / `in_transit` / `completed` is called out in Data.
- `projects/junior/README.md` has a row for the project.
