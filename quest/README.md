# Quest

Jogo de perguntas sobre os projetos da FilaFácil. A tela é fixa. As perguntas ficam num pacote local, por nível, e não entram no Git.

## 1. Como abrir

Na raiz do repositório:

```bash
python3 -m http.server
```

Abra `http://127.0.0.1:8000/quest/`.

Escolha o nível. O junior já tem pacote, em `quest/junior/local/pack.json`. Mid-level, senior e staff abrem a tela e avisam que ainda não há pacote.

O navegador precisa desse servidor. Abrir o `index.html` direto no disco bloqueia a leitura do pacote.

## 2. Como jogar

Cada nível tem três quests: Conceitos (200), Tecnologias (100) e Casos de uso (50). Uma sessão traz 10 perguntas ainda não acertadas. Acerto vale 10 XP e sobe a sequência. Erro zera a sequência e mostra a explicação. O progresso fica no navegador. "Zerar esta campanha" apaga só esse nível.

## 3. Como gerar de novo

Aponte um agente para [AGENT.md](AGENT.md) e para a pasta do nível, por exemplo `quest/junior`. Ele lê o `source.json` dessa pasta, olha só os projetos ligados e regrava `quest/<nível>/local/pack.json`.

| Nível | Projetos | Pacote |
| --- | --- | --- |
| `quest/junior` | `projects/junior` | `quest/junior/local/pack.json` |
| `quest/mid-level` | `projects/mid-level` | `quest/mid-level/local/pack.json` |
| `quest/senior` | `projects/senior` | `quest/senior/local/pack.json` |
| `quest/staff` | `projects/staff` | `quest/staff/local/pack.json` |

`quest/*/local/` está no `.gitignore`. Não force o add desse arquivo. Um pacote novo troca o `campaignId` e a campanha daquele nível começa zerada.
