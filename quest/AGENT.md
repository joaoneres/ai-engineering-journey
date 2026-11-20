# Gerar a quest de um nível

A base visual é fixa. Esta execução só lê projetos e regrava o pacote local da pasta de nível recebida.

Não edite `quest/index.html`, `quest/styles.css`, `quest/game.js`, `quest/schema.json`, este arquivo, nem o `index.html` de nenhum nível.

## Entrada

A pasta de nível é uma destas:

- `quest/junior`
- `quest/mid-level`
- `quest/senior`
- `quest/staff`

Leia o `source.json` dessa pasta. O campo `projects` é o único conjunto de código permitido. Exemplo: `quest/junior/source.json` aponta para `projects/junior`.

## Leitura

1. Liste os diretórios de projeto que existem de verdade dentro de `projects`. Ignore um nome que apareça só num README se a pasta não existir.
2. Leia o README de cada projeto presente. Abra código, testes ou configuração só quando o README não bastar para uma pergunta fiel.
3. Se a pasta de projetos só tiver `.gitkeep`, pare. Não invente perguntas e não crie `local/pack.json`.

## Saída

Grave somente `quest/<nível>/local/pack.json`. Crie a pasta `local/` se ela não existir. Esse caminho está no `.gitignore`. Não faça `git add -f` nele.

Se já existir um pacote, leia os enunciados atuais. Não repita o mesmo enunciado. Reformule, troque os distratores e cubra um fato que a leva anterior não perguntou. Embaralhe a ordem dentro de cada banco.

O pacote novo tem um `campaignId` novo, em UTC (`YYYY-MM-DDTHH:MM:SSZ`). O jogo separa o `localStorage` por nível e por esse id, então a campanha começa zerada.

## Forma

O JSON obedece a `quest/schema.json`.

- `level` é o nome da pasta (`junior`, `mid-level`, `senior` ou `staff`).
- `projects` é o valor do `source.json`.
- Três bancos, quando houver matéria suficiente: **200** `concept`, **100** `technology`, **50** `usecase`.
- Cada pergunta tem quatro `choices`. `answer` é o índice `0`–`3` da alternativa certa, depois de embaralhar as alternativas.
- `project` é o nome da pasta do projeto, não o título do README.
- A explicação diz o fato e o projeto. Interface e enunciados em português.
- Um fato que os arquivos não mostram não vira pergunta.

`concept` pergunta a ideia: camada, regra, persistência, erro, limite. `technology` pergunta a ferramenta e o uso neste código. `usecase` pergunta o que a pessoa faz na tela ou no comando.

Reparta as perguntas entre os projetos presentes, para um módulo não ficar de fora. Se a matéria não chegar a 350 perguntas fiéis, pare e diga quantas faltam em vez de completar com trivia genérica.
