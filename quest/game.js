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
    { id: "junior", title: "Junior", projects: "projects/junior", icon: "🌱" },
    { id: "mid-level", title: "Mid-level", projects: "projects/mid-level", icon: "🔧" },
    { id: "senior", title: "Senior", projects: "projects/senior", icon: "🏛️" },
    { id: "staff", title: "Staff", projects: "projects/staff", icon: "🚀" },
  ];

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
    context.textContent = "Escolha o nível da sua jornada.";
    const view = el("div");
    view.append(el("div", "section-title", "Níveis"));
    const grid = el("div", "grid");
    view.append(grid);
    app.replaceChildren(view);

    for (const item of levels) {
      const link = el("a", "level");
      link.href = item.id + "/";
      link.append(el("span", "emblem", item.icon));
      link.append(el("strong", null, item.title));
      const meta = el("span", "meta", item.projects);
      link.append(meta);
      link.append(el("span", "go", "→"));
      const bar = el("div", "bar");
      const fill = el("span");
      fill.style.width = "0%";
      bar.append(fill);
      link.append(bar);
      grid.append(link);

      // Progresso de cada nível, quando já existe pacote e campanha.
      readJson(item.id + "/local/pack.json").then(function (pack) {
        if (!pack || !pack.campaignId || !Array.isArray(pack.questions)) {
          meta.textContent = item.projects + " · sem pacote";
          return;
        }
        const state = loadState(keyFor(item.id, pack.campaignId));
        const done = count(state.correct);
        const info = levelInfo(state.xp);
        meta.textContent =
          "Nv. " + info.n + " · " + done + " de " + pack.questions.length + " acertos · " + state.xp + " XP";
        requestAnimationFrame(function () {
          fill.style.width = percent(done, pack.questions.length);
        });
      });
    }
  }

  async function boot(levelId) {
    const source = await readJson("source.json");
    const projects = source && source.projects ? source.projects : "projects/" + levelId;
    context.textContent = "Ligado a " + projects;

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
        const button = el("button", "bank" + (complete ? " complete" : ""));
        button.type = "button";
        button.append(el("span", "emblem", complete ? "🏆" : bank.icon));
        button.append(el("strong", null, bank.title));
        button.append(
          el("span", "meta", done + " de " + questions.length + " · " + bank.hint),
        );
        button.append(el("span", "go", "▶"));
        const bar = el("div", "bar");
        const fill = el("span");
        fill.style.width = "0%";
        bar.append(fill);
        button.append(bar);
        requestAnimationFrame(function () {
          fill.style.width = percent(done, questions.length);
        });
        button.addEventListener("click", function () {
          startSession(bank.id);
        });
        grid.append(button);
      });

      const wrongCount = reviewPool().length;
      if (wrongCount) {
        const review = el("button", "bank");
        review.type = "button";
        review.append(el("span", "emblem", "🩹"));
        review.append(el("strong", null, "Revisar erros"));
        review.append(el("span", "meta", wrongCount + " para tentar de novo"));
        review.append(el("span", "go", "▶"));
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

      const back = el("button", "ghost", "Abandonar sessão");
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

      const next = el("button", "solid", finished ? "Ver resultado →" : "Próxima →");
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
    return "filafacil-quest:" + levelId + ":" + campaignId;
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
