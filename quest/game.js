(function () {
  const app = document.querySelector("#app");
  const context = document.querySelector("#context");
  const level = document.body.dataset.level || "";
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const banks = [
    { id: "concept", title: "Conceitos", hint: "O que o projeto ensina", icon: "🧠" },
    { id: "technology", title: "Tecnologias", hint: "Como a ferramenta foi usada", icon: "⚙️" },
    { id: "usecase", title: "Casos de uso", hint: "O que a pessoa faz no sistema", icon: "🎯" },
  ];

  const levels = [
    { id: "junior", title: "Junior", tone: "junior", rank: 1 },
    { id: "mid-level", title: "Mid-level", tone: "mid-level", rank: 2 },
    { id: "senior", title: "Senior", tone: "senior", rank: 3 },
    { id: "staff", title: "Staff", tone: "staff", rank: 4 },
  ];

  const icons = {
    junior:
      '<svg viewBox="0 0 24 24"><path d="M7 20h10"/><path d="M10 20c5.5-2.5.8-6.4 3-10"/><path d="M9.5 9.4c1.1.8 1.8 2.2 2.3 3.7-2 .4-3.5.4-4.8-.3-1.2-.6-2.3-1.9-3-4.2 2.8.4 4.4 1.4 5.5 2.8z"/><path d="M14.1 6a7 7 0 0 0-1.1 4c1.9-.1 3.3-.6 4.3-1.4 1-1 1.6-2.3 1.7-4.6-2.7.1-4 1-4.9 2z"/></svg>',
    "mid-level":
      '<svg viewBox="0 0 24 24"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>',
    senior:
      '<svg viewBox="0 0 24 24"><path d="M3 22h18"/><path d="M6 18v-7"/><path d="M10 18v-7"/><path d="M14 18v-7"/><path d="M18 18v-7"/><path d="m12 2 8 5H4z"/></svg>',
    staff:
      '<svg viewBox="0 0 24 24"><path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"/><path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"/><path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0"/><path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"/></svg>',
    concept:
      '<svg viewBox="0 0 24 24"><path d="M9 18h6"/><path d="M10 22h4"/><path d="M12 2a7 7 0 0 0-4 12c.6.6 1 1.4 1 2h6c0-.6.4-1.4 1-2a7 7 0 0 0-4-12Z"/></svg>',
    technology:
      '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M19.1 4.9 17 7M7 17l-2.1 2.1"/></svg>',
    usecase:
      '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="4"/><circle cx="12" cy="12" r="1"/></svg>',
    review:
      '<svg viewBox="0 0 24 24"><path d="M4 12a8 8 0 1 0 2.3-5.6"/><path d="M4 4v5h5"/></svg>',
    lock:
      '<svg viewBox="0 0 24 24"><rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/></svg>',
  };

  const ranks = ["Novato", "Aprendiz", "Dev", "Engenheiro", "Arquiteto", "Lenda"];
  const SESSION_SIZE = 10;

  // Cada conquista é derivada do estado salvo, então campanhas antigas ganham as suas.
  const achievements = [
    { id: "first", icon: "✨", title: "Primeiro acerto", test: (s) => count(s.correct) >= 1 },
    { id: "s5", icon: "🔥", title: "Sequência de 5", test: (s) => (s.best || 0) >= 5 },
    { id: "s10", icon: "☄️", title: "Sequência de 10", test: (s) => (s.best || 0) >= 10 },
    { id: "perfect", icon: "💎", title: "Sessão perfeita", test: (s) => (s.perfects || 0) >= 1 },
    { id: "c50", icon: "📚", title: "50 acertos", test: (s) => count(s.correct) >= 50 },
    { id: "xp500", icon: "👑", title: "500 XP", test: (s) => s.xp >= 500 },
  ];

  let keyHandler = null;
  document.addEventListener("keydown", function (event) {
    if (keyHandler && !event.ctrlKey && !event.metaKey && !event.altKey) keyHandler(event);
  });

  if (!level) {
    renderHall();
    return;
  }

  boot(level);

  /* ---------- Entrada ---------- */

  async function renderHall() {
    const days = touchDayStreak();
    const packs = await Promise.all(
      levels.map(function (item) {
        return readJson(item.id + "/local/pack.json");
      }),
    );
    const rows = levels.map(function (item, index) {
      const pack = packs[index];
      const ready = pack && pack.campaignId && Array.isArray(pack.questions) && pack.questions.length;
      if (!ready) return { item: item, state: "locked", done: 0, total: 0, xp: 0, info: levelInfo(0) };
      const saved = loadState(keyFor(item.id, pack.campaignId));
      const done = count(saved.correct);
      const total = pack.questions.length;
      return {
        item: item,
        state: done >= total ? "done" : "active",
        done: done,
        total: total,
        xp: saved.xp,
        info: levelInfo(saved.xp),
      };
    });
    const totals = rows.reduce(
      function (sum, row) {
        return { done: sum.done + row.done, total: sum.total + row.total, xp: sum.xp + row.xp };
      },
      { done: 0, total: 0, xp: 0 },
    );
    const current = rows.filter(function (row) {
      return row.state === "active";
    })[0] || rows.filter(function (row) {
      return row.state === "done";
    }).slice(-1)[0];

    context.textContent = current
      ? current.item.title + " · " + totals.done + " de " + totals.total + " acertos"
      : "A jornada abre quando o primeiro pacote existir.";

    const view = el("div");
    view.append(playerSummary(totals, days, current));
    view.append(el("div", "section-title", "Jornada"));
    const trail = el("ol", "trail");
    rows.forEach(function (row) {
      trail.append(levelCard(row));
    });
    view.append(trail);
    app.replaceChildren(view);
    animateBars(view);
  }

  function levelCard(row) {
    const step = el("li", "trail-step");
    const locked = row.state === "locked";
    const node = el(locked ? "div" : "a", "level is-" + row.state);
    node.dataset.tone = row.item.tone;
    if (!locked) node.href = row.item.id + "/";
    if (locked) {
      node.setAttribute("role", "button");
      node.tabIndex = 0;
      node.addEventListener("click", function () {
        node.classList.remove("shake");
        void node.offsetWidth;
        node.classList.add("shake");
      });
    }

    const emblem = el("span", "emblem");
    emblem.append(icon(row.item.tone));
    if (row.state === "done") emblem.append(el("span", "seal", "✓"));
    node.append(emblem);

    const copy = el("span", "card-copy");
    const head = el("span", "card-head");
    const name = el("span", "card-name");
    name.append(el("strong", null, row.item.title));
    name.append(rankMark(row.item.rank));
    head.append(name);
    if (locked) head.append(el("span", "soon", "Em breve"));
    else head.append(xpLine(row.xp));
    copy.append(head);
    if (!locked) copy.append(progressRow(row.done, row.total));
    node.append(copy);

    if (locked) node.append(icon("lock", "lock"));
    else node.append(el("span", "cta", ctaLabel(row)));
    step.append(node);
    return step;
  }

  function ctaLabel(row) {
    if (row.state === "done") return "Rever";
    if (row.done > 0) return "Continuar";
    return "Começar";
  }

  async function boot(levelId) {
    context.textContent = "Três missões. Acerte para avançar.";

    let pack;
    try {
      const response = await fetch("local/pack.json");
      if (!response.ok) {
        missingPack(levelId);
        return;
      }
      pack = await response.json();
    } catch (error) {
      blocked(levelId);
      return;
    }

    if (!pack || !Array.isArray(pack.questions) || !pack.campaignId) {
      missingPack(levelId);
      return;
    }

    play(levelId, pack);
  }

  /* ---------- Jogo ---------- */

  function play(levelId, pack) {
    const storageKey = keyFor(levelId, pack.campaignId);
    let state = loadState(storageKey);
    let session = [];
    let results = [];
    let cursor = 0;
    let sessionStart = null;

    renderMap();

    function renderMap() {
      keyHandler = null;
      const view = el("div");
      view.append(hud());

      view.append(el("div", "section-title", "Escolha uma missão"));
      const grid = el("div", "grid");
      banks.forEach(function (bank) {
        const questions = pack.questions.filter(function (question) {
          return question.bank === bank.id;
        });
        const done = questions.filter(function (question) {
          return state.correct[question.id];
        }).length;
        const complete = questions.length > 0 && done === questions.length;
        const button = el("button", "bank is-" + (complete ? "done" : "active"));
        button.type = "button";
        button.dataset.tone = bank.id;
        const emblem = el("span", "emblem");
        emblem.append(icon(bank.id));
        if (complete) emblem.append(el("span", "seal", "✓"));
        button.append(emblem);
        const copy = el("span", "card-copy");
        const head = el("span", "card-head");
        head.append(el("strong", null, bank.title));
        head.append(el("span", "soon", bank.hint));
        copy.append(head, progressRow(done, questions.length));
        button.append(copy);
        button.append(el("span", "cta", complete ? "Rever" : done ? "Continuar" : "Começar"));
        button.addEventListener("click", function () {
          startSession(bank.id);
        });
        grid.append(button);
      });

      const wrongCount = reviewPool().length;
      if (wrongCount) {
        const review = el("button", "bank is-active");
        review.type = "button";
        review.dataset.tone = "review";
        const emblem = el("span", "emblem");
        emblem.append(icon("review"));
        review.append(emblem);
        const copy = el("span", "card-copy");
        const head = el("span", "card-head");
        head.append(el("strong", null, "Revisar erros"));
        head.append(el("span", "soon", wrongCount + " para tentar de novo"));
        copy.append(head);
        review.append(copy);
        review.append(el("span", "cta", "Revisar"));
        review.addEventListener("click", function () {
          startSession("review");
        });
        grid.append(review);
      }
      view.append(grid);

      view.append(el("div", "section-title", "Conquistas"));
      const badges = el("div", "badges");
      achievements.forEach(function (item) {
        const on = item.test(state);
        const node = el("div", "ach" + (on ? " on" : ""));
        node.append(item.icon);
        node.append(el("b", null, item.title));
        badges.append(node);
      });
      view.append(badges);

      const row = el("div", "row");
      const reset = el("button", "ghost", "Zerar esta campanha");
      reset.type = "button";
      reset.addEventListener("click", function () {
        if (!window.confirm("Zerar XP, sequência e acertos desta campanha?")) return;
        state = emptyState();
        saveState(storageKey, state);
        renderMap();
      });
      const hall = el("a", "ghost", "Todos os níveis");
      hall.href = "../";
      row.append(reset, hall);
      view.append(row);
      app.replaceChildren(view);
      animateBars(view);
    }

    function reviewPool() {
      return pack.questions.filter(function (question) {
        return state.wrong[question.id] && !state.correct[question.id];
      });
    }

    function startSession(bankId) {
      const pool =
        bankId === "review"
          ? reviewPool()
          : pack.questions.filter(function (question) {
              return question.bank === bankId && !state.correct[question.id];
            });
      shuffle(pool);
      session = pool.slice(0, SESSION_SIZE);
      results = [];
      cursor = 0;
      sessionStart = { xp: state.xp, level: levelInfo(state.xp).n, badges: unlocked() };
      if (!session.length) {
        keyHandler = null;
        const view = el("div");
        view.append(hud());
        const notice = el("p", "notice");
        notice.textContent =
          "Missão cumprida! Tudo acertado aqui nesta campanha. Zere a campanha para jogar de novo.";
        view.append(notice);
        const back = el("button", "solid", "Voltar ao mapa");
        back.type = "button";
        back.addEventListener("click", renderMap);
        view.append(back);
        app.replaceChildren(view);
        return;
      }
      renderQuestion();
    }

    function renderQuestion() {
      const question = session[cursor];
      const view = el("div");
      view.append(hud());

      const stepper = el("div", "stepper");
      const dots = el("div", "dots");
      session.forEach(function (_, index) {
        const dot = el("i");
        if (index < results.length) dot.className = results[index] ? "ok" : "no";
        else if (index === cursor) dot.className = "cur";
        dots.append(dot);
      });
      stepper.append(dots, el("span", "tag", cursor + 1 + "/" + session.length + " · " + question.project));
      view.append(stepper);

      const card = el("article", "card");
      card.append(el("p", "prompt", question.prompt));
      question.choices.forEach(function (choice, choiceIndex) {
        const button = el("button", "choice");
        button.type = "button";
        button.append(el("span", "key", String(choiceIndex + 1)));
        button.append(el("span", null, choice));
        button.addEventListener("click", function () {
          grade(question, choiceIndex, card);
        });
        card.append(button);
      });
      view.append(card);

      const back = el("button", "ghost abandon", "Abandonar sessão");
      back.type = "button";
      back.addEventListener("click", renderMap);
      view.append(back);
      app.replaceChildren(view);

      keyHandler = function (event) {
        const index = Number(event.key) - 1;
        if (index >= 0 && index < 4) {
          const target = card.querySelectorAll(".choice")[index];
          if (target && !target.disabled) target.click();
        }
      };
    }

    function grade(question, choiceIndex, card) {
      const buttons = card.querySelectorAll(".choice");
      buttons.forEach(function (button, buttonIndex) {
        button.disabled = true;
        if (buttonIndex === question.answer) button.classList.add("right");
        if (buttonIndex === choiceIndex && choiceIndex !== question.answer) {
          button.classList.add("wrong");
        }
      });

      const right = choiceIndex === question.answer;
      results.push(right);
      let gained = 0;
      if (right) {
        state.streak += 1;
        state.best = Math.max(state.best || 0, state.streak);
        gained = 10 + comboBonus(state.streak);
        state.xp += gained;
        state.correct[question.id] = true;
        delete state.wrong[question.id];
        card.classList.add("glow");
      } else {
        state.streak = 0;
        state.wrong[question.id] = true;
        card.classList.add("shake");
      }

      const finished = cursor + 1 === session.length;
      if (finished && results.every(Boolean)) state.perfects = (state.perfects || 0) + 1;
      saveState(storageKey, state);

      const explain = el("div", "explain " + (right ? "good" : "bad"));
      explain.append(el("strong", null, right ? "Acertou! +" + gained + " XP" : "Quase lá"));
      explain.append(question.explanation);
      card.append(explain);

      const next = el("button", "solid", finished ? "Ver resultado" : "Próxima");
      next.type = "button";
      next.addEventListener("click", advance);
      card.append(next);
      next.focus({ preventScroll: true });

      keyHandler = function (event) {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          advance();
        }
      };

      const before = app.querySelector(".hud");
      before.replaceWith(hud());
      if (right) {
        floatXp("+" + gained + " XP", buttons[choiceIndex]);
        const streakPill = app.querySelector(".pill.hot, .pill[data-streak]");
        if (streakPill) streakPill.classList.add("bump");
      }

      function advance() {
        cursor += 1;
        if (cursor >= session.length) renderSummary();
        else renderQuestion();
      }
    }

    function renderSummary() {
      keyHandler = null;
      const rightCount = results.filter(Boolean).length;
      const ratio = rightCount / session.length;
      const stars = ratio === 1 ? 3 : ratio >= 0.7 ? 2 : ratio >= 0.4 ? 1 : 0;
      const titles = ["Vamos de novo", "Bom começo", "Mandou bem", "Sessão perfeita!"];

      const view = el("div");
      view.append(hud());
      const box = el("div", "result");
      const starRow = el("div", "stars");
      for (let index = 0; index < 3; index += 1) {
        starRow.append(el("span", index < stars ? "on" : "off", "⭐"));
      }
      box.append(starRow);
      box.append(el("h2", null, titles[stars]));
      box.append(el("p", null, rightCount + " de " + session.length + " acertadas"));

      const gains = el("div", "gains");
      gains.append(el("span", "pill gold", "+" + (state.xp - sessionStart.xp) + " XP"));
      gains.append(el("span", "pill", "Melhor sequência " + (state.best || 0)));
      box.append(gains);

      const info = levelInfo(state.xp);
      if (info.n > sessionStart.level) {
        box.append(el("p", "toast-up", "🎉 Subiu para o nível " + info.n + " · " + rankName(info.n)));
      }
      unlocked()
        .filter(function (id) {
          return sessionStart.badges.indexOf(id) === -1;
        })
        .forEach(function (id) {
          const item = achievements.filter(function (a) {
            return a.id === id;
          })[0];
          box.append(el("p", "toast-up", item.icon + " Conquista: " + item.title));
        });

      const row = el("div", "row");
      const map = el("button", "solid", "Voltar ao mapa");
      map.type = "button";
      map.addEventListener("click", renderMap);
      row.append(map);
      box.append(row);
      view.append(box);
      app.replaceChildren(view);
      if (stars >= 2) confetti(stars === 3 ? 70 : 35);
    }

    function unlocked() {
      return achievements
        .filter(function (item) {
          return item.test(state);
        })
        .map(function (item) {
          return item.id;
        });
    }

    function hud() {
      const info = levelInfo(state.xp);
      const node = el("div", "hud");
      const badge = el("div", "badge-lvl", String(info.n));
      badge.append(el("small", null, "NV"));
      node.append(badge);

      const main = el("div", "hud-main");
      const rank = el("div", "rank");
      rank.append(el("b", null, rankName(info.n)));
      rank.append(el("span", null, state.xp - info.floor + " / " + (info.next - info.floor) + " XP"));
      main.append(rank);
      const bar = el("div", "xpbar");
      const fill = el("span");
      fill.style.width = percent(state.xp - info.floor, info.next - info.floor);
      bar.append(fill);
      main.append(bar);
      node.append(main);

      const side = el("div", "hud-side");
      const streak = el("span", "pill" + (state.streak >= 3 ? " hot" : ""));
      streak.dataset.streak = "1";
      streak.append(el("span", "ico", "🔥"), " " + state.streak);
      streak.title = "Sequência de acertos";
      side.append(streak);
      side.append(el("span", "pill gold", "⭐ " + state.xp + " XP"));
      node.append(side);
      return node;
    }
  }

  /* ---------- Avisos ---------- */

  function missingPack(levelId) {
    const notice = el("p", "notice");
    notice.append(
      "Não há pacote em ",
      code("quest/" + levelId + "/local/pack.json"),
      ". Aponte o agente para ",
      code("quest/AGENT.md"),
      " e para esta pasta. O pacote não entra no Git.",
    );
    const hall = el("a", "ghost", "Todos os níveis");
    hall.href = "../";
    const row = el("div", "row");
    row.append(hall);
    app.replaceChildren(notice, row);
  }

  function blocked(levelId) {
    const notice = el("p", "notice");
    notice.append(
      "O navegador bloqueou a leitura de ",
      code("local/pack.json"),
      ". Na raiz do repositório, rode ",
      code("python3 -m http.server"),
      " e abra ",
      code("/quest/" + levelId + "/"),
      ".",
    );
    app.replaceChildren(notice);
  }

  /* ---------- Progressão ---------- */

  // Nível n começa em 50·n·(n-1) XP: 0, 100, 300, 600, 1000…
  function levelInfo(xp) {
    const n = Math.floor((1 + Math.sqrt(1 + (4 * xp) / 50)) / 2);
    return { n: n, floor: 50 * n * (n - 1), next: 50 * (n + 1) * n };
  }

  function rankName(n) {
    return ranks[Math.min(n - 1, ranks.length - 1)];
  }

  function comboBonus(streak) {
    if (streak >= 10) return 10;
    if (streak >= 5) return 5;
    if (streak >= 3) return 2;
    return 0;
  }

  function keyFor(levelId, campaignId) {
    return "quest:" + levelId + ":" + campaignId;
  }

  function loadState(key) {
    try {
      const saved = JSON.parse(localStorage.getItem(key) || "");
      if (saved && saved.correct && saved.wrong) {
        return Object.assign(emptyState(), saved);
      }
    } catch (error) {
      // A campanha nova começa vazia.
    }
    return emptyState();
  }

  function emptyState() {
    return { xp: 0, streak: 0, best: 0, perfects: 0, correct: {}, wrong: {} };
  }

  function saveState(key, state) {
    try {
      localStorage.setItem(key, JSON.stringify(state));
    } catch (error) {
      // Sem armazenamento, o jogo segue só nesta aba.
    }
  }

  /* ---------- Efeitos ---------- */

  function floatXp(text, anchor) {
    if (reduceMotion || !anchor) return;
    const box = anchor.getBoundingClientRect();
    const node = el("span", "float-xp", text);
    node.style.left = box.right - 90 + "px";
    node.style.top = box.top + "px";
    document.body.append(node);
    setTimeout(function () {
      node.remove();
    }, 1000);
  }

  function confetti(amount) {
    if (reduceMotion) return;
    const colors = ["#7c5cff", "#22d3ee", "#ffc53d", "#34d399", "#fb7185"];
    for (let index = 0; index < amount; index += 1) {
      const piece = el("i", "confetti");
      piece.style.left = Math.random() * 100 + "vw";
      piece.style.background = colors[index % colors.length];
      piece.style.animationDuration = 1.6 + Math.random() * 1.6 + "s";
      piece.style.animationDelay = Math.random() * 0.4 + "s";
      document.body.append(piece);
      setTimeout(function () {
        piece.remove();
      }, 3800);
    }
  }

  /* ---------- Utilidades ---------- */

  async function readJson(url) {
    try {
      const response = await fetch(url);
      if (!response.ok) return null;
      return await response.json();
    } catch (error) {
      return null;
    }
  }

  function count(map) {
    return Object.keys(map || {}).length;
  }

  function percent(done, total) {
    if (!total) return "0%";
    return Math.round((done / total) * 100) + "%";
  }

  function shuffle(items) {
    for (let index = items.length - 1; index > 0; index -= 1) {
      const swap = Math.floor(Math.random() * (index + 1));
      const current = items[index];
      items[index] = items[swap];
      items[swap] = current;
    }
  }

  function playerSummary(totals, days, current) {
    const ratio = totals.total ? Math.round((totals.done / totals.total) * 100) : 0;
    const node = el("section", "player");
    const ring = el("div", "ring");
    ring.style.setProperty("--p", String(ratio));
    ring.append(el("span", null, ratio + "%"));
    const copy = el("div", "player-copy");
    copy.append(el("strong", null, current ? current.item.title : "Jornada"));
    copy.append(
      el(
        "p",
        null,
        totals.total
          ? totals.done + " de " + totals.total + " acertos nesta jornada"
          : "Nenhum pacote gerado ainda",
      ),
    );
    const pills = el("div", "player-pills");
    pills.append(el("span", "pill gold", totals.xp + " XP"));
    pills.append(el("span", "pill" + (days >= 2 ? " hot" : ""), "🔥 " + days + (days === 1 ? " dia" : " dias")));
    copy.append(pills);
    node.append(ring, copy);
    return node;
  }

  function xpLine(xp) {
    const node = el("span", "card-xp");
    node.append(el("b", null, String(xp)));
    node.append(" XP");
    return node;
  }

  function rankMark(rank) {
    const node = el("span", "card-rank");
    const label = el("span", "nv");
    label.append("Nv.");
    label.append(el("b", null, String(rank)));
    const bars = el("span", "bars");
    for (let step = 1; step <= 4; step += 1) bars.append(el("span", step <= rank ? "on" : ""));
    node.append(label, bars);
    return node;
  }

  function progressRow(done, total) {
    const row = el("span", "card-progress");
    const bar = el("div", "bar");
    const fill = el("span");
    fill.dataset.goal = percent(done, total);
    bar.append(fill);
    row.append(bar, el("span", "card-count", done + " / " + total));
    return row;
  }

  function animateBars(root) {
    requestAnimationFrame(function () {
      root.querySelectorAll(".bar span").forEach(function (fill) {
        fill.style.width = fill.dataset.goal || "0%";
      });
    });
  }

  function icon(name, className) {
    const node = el("span", className || "emblem-icon");
    node.innerHTML = icons[name] || "";
    return node;
  }

  function touchDayStreak() {
    const key = "quest:days";
    const today = localDay(new Date());
    let streak = 1;
    try {
      const saved = JSON.parse(localStorage.getItem(key) || "");
      if (saved && saved.lastDay === today) streak = saved.streak || 1;
      else if (saved && saved.lastDay === localDay(new Date(Date.now() - 86400000))) {
        streak = (saved.streak || 0) + 1;
      }
    } catch (error) {
      streak = 1;
    }
    try {
      localStorage.setItem(key, JSON.stringify({ lastDay: today, streak: streak }));
    } catch (error) {
      // Sem armazenamento, a sequência vale só nesta abertura.
    }
    return streak;
  }

  function localDay(date) {
    return (
      date.getFullYear() +
      "-" +
      String(date.getMonth() + 1).padStart(2, "0") +
      "-" +
      String(date.getDate()).padStart(2, "0")
    );
  }

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function code(text) {
    return el("code", null, text);
  }
})();
