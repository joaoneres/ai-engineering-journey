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

Se já existir um pacote, leia os enunciados. Uma campanha nova reformula e troca os distratores. Se os enunciados atuais forem detalhe de implementação, substitua o conjunto: não preserve esse tipo de pergunta só para não repetir a frase. Embaralhe a ordem dentro de cada banco.

O pacote novo tem um `campaignId` novo, em UTC (`YYYY-MM-DDTHH:MM:SSZ`). O jogo separa o `localStorage` por nível e por esse id, então a campanha começa zerada.

## Nome

A quest não tem um produto global. O nome da tela é Quest. FilaFácil é o nome de alguns projetos dentro de `projects/junior`, não o nome do jogo e não o nome dos outros níveis.

No enunciado, na alternativa e na explicação, use o nome que o próprio projeto mostra: título da interface, módulo ou arquivo. Se o projeto não se chama FilaFácil, a pergunta também não se chama.

## Forma

O JSON obedece a `quest/schema.json`.

- `level` é o nome da pasta (`junior`, `mid-level`, `senior` ou `staff`).
- `projects` é o valor do `source.json`.
- Três bancos: `concept`, `technology` e `usecase`. A quantidade é a de ideias distintas que os projetos sustentam. Não complete até um número redondo com pergunta miúda.
- Cada pergunta tem quatro `choices`. `answer` é o índice `0`–`3` da alternativa certa, depois de embaralhar as alternativas.
- `project` é o nome da pasta do projeto, não o título do README.
- A explicação diz a ideia. Interface e enunciados em português.
- Um fato que os arquivos não mostram não vira pergunta.

A pergunta é conceitual. Ela cobra a decisão que o projeto demonstra: o problema, a responsabilidade de uma camada, a garantia, o limite, o que a pessoa consegue fazer. Alguém que entendeu o projeto responde. Alguém que só memorizou o código não precisa responder.

Não pergunte número de opção de menu, tecla, nome de arquivo, versão de linguagem, nome de função, lista de argumentos nem comportamento de um atalho. "Ctrl+C mostra traceback?" não é uma pergunta desta quest.

`concept` pergunta a ideia. `technology` pergunta por que a ferramenta está aqui e o que ela faz ou deixa de fazer neste projeto, não a versão nem o nome do método. `usecase` pergunta o que a pessoa realiza, não o que uma opção numerada imprime.

Reparta as perguntas entre os projetos presentes, para um módulo não ficar de fora. Distrator é uma ideia plausível e errada, não uma palavra solta.
