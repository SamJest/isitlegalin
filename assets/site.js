const STORAGE_KEYS = {
  recent: "isitlegalin-v2-recent",
  saved: "isitlegalin-v2-saved",
  checklist: "isitlegalin-v2-checklist"
};

function readStore(key, fallback) {
  try {
    const raw = window.localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

function writeStore(key, value) {
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // ignore storage failures
  }
}

function clampRecent(items) {
  return items.slice(0, 12);
}

function loadPagePayload() {
  const element = document.getElementById("pagePayload");

  if (!element) {
    return null;
  }

  try {
    return JSON.parse(element.textContent);
  } catch {
    return null;
  }
}

function pushRecentPage(payload) {
  if (!payload || !payload.href) {
    return;
  }

  const recent = readStore(STORAGE_KEYS.recent, []);
  const deduped = [payload, ...recent.filter((item) => item.href !== payload.href)];
  writeStore(STORAGE_KEYS.recent, clampRecent(deduped));
}

function toggleSavedPage(payload) {
  const saved = readStore(STORAGE_KEYS.saved, []);
  const exists = saved.some((item) => item.href === payload.href);
  const next = exists
    ? saved.filter((item) => item.href !== payload.href)
    : clampRecent([payload, ...saved]);
  writeStore(STORAGE_KEYS.saved, next);
  return !exists;
}

function renderSavedState(button, payload) {
  const saved = readStore(STORAGE_KEYS.saved, []);
  const exists = saved.some((item) => item.href === payload.href);
  button.textContent = exists ? "Saved" : "Save page";
  button.setAttribute("aria-pressed", exists ? "true" : "false");
}

function buildMiniCard(item) {
  return `
    <a class="mini-card" href="${item.href}">
      <strong>${item.query}</strong>
      <span>${item.country || item.queryType || item.verdict || ""}</span>
    </a>
  `;
}

function renderMiniCollection(selector, key, emptyMessage) {
  document.querySelectorAll(selector).forEach((container) => {
    const items = readStore(key, []);

    if (!items.length) {
      container.innerHTML = `<p class="empty-state">${emptyMessage}</p>`;
      return;
    }

    container.innerHTML = items.map(buildMiniCard).join("");
  });
}

function initSavedPageButton() {
  const button = document.querySelector("[data-save-page]");
  const payload = loadPagePayload();

  if (!button || !payload) {
    return;
  }

  renderSavedState(button, payload);

  button.addEventListener("click", () => {
    toggleSavedPage(payload);
    renderSavedState(button, payload);
    renderMiniCollection("[data-saved-pages]", STORAGE_KEYS.saved, "Save a page and it will appear here.");
  });
}

function initCopyButton() {
  document.querySelectorAll("[data-copy-answer]").forEach((button) => {
    const text = button.getAttribute("data-copy-text");

    if (!text) {
      return;
    }

    button.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(text);
        const previous = button.textContent;
        button.textContent = "Copied";
        window.setTimeout(() => {
          button.textContent = previous;
        }, 1600);
      } catch {
        button.textContent = "Copy failed";
      }
    });
  });
}

function initChecklist() {
  document.querySelectorAll("[data-checklist-key]").forEach((container) => {
    const key = container.getAttribute("data-checklist-key");
    const saved = readStore(STORAGE_KEYS.checklist, {});
    const state = saved[key] || {};

    container.querySelectorAll("[data-check-item]").forEach((input) => {
      const itemKey = input.getAttribute("data-check-item");
      input.checked = Boolean(state[itemKey]);

      input.addEventListener("change", () => {
        const nextSaved = readStore(STORAGE_KEYS.checklist, {});
        nextSaved[key] = nextSaved[key] || {};
        nextSaved[key][itemKey] = input.checked;
        writeStore(STORAGE_KEYS.checklist, nextSaved);
      });
    });
  });
}

function buildSmartAnswer(payload, question) {
  if (!payload) {
    return "This page can give a quick read once the page data is available.";
  }

  const query = (question || "").toLowerCase();
  const verdict = payload.verdict || "Depends";
  const direct = payload.directAnswer || payload.summary || `This page tracks ${payload.query || "the rule"} in ${payload.country || "this jurisdiction"}.`;
  const risk = payload.riskLabel ? `${payload.riskLabel} risk.` : "";
  const enforcement = payload.enforcement || payload.summary || "";

  if (query.includes("trouble") || query.includes("penalt") || query.includes("risk")) {
    return `${risk || "There is some legal risk."} ${enforcement}`.trim();
  }

  if (query.includes("fully") || query.includes("restrict") || query.includes("legal")) {
    if (verdict === "Legal") {
      return `${direct} It reads as permitted in principle, but the listed conditions and edge-case restrictions still matter.`;
    }

    if (verdict === "Illegal") {
      return `${direct} This does not read as fully legal unless a narrow exception clearly fits.`;
    }

    return `${direct} This is not a clean yes-or-no rule, so restrictions and context are part of the answer.`;
  }

  if (query.includes("carry")) {
    if (verdict === "Illegal") {
      return `${direct} Do not assume carrying it is safe unless the page shows a clear exception.`;
    }

    if (verdict === "Legal") {
      return `${direct} Carrying may still be limited by storage, transport, public-use, or context rules.`;
    }

    return `${direct} Whether you can carry it depends on the exact setting, purpose, and local restrictions.`;
  }

  return `${direct} ${risk}`.trim();
}

function initSmartAnswer() {
  document.querySelectorAll("[data-smart-answer]").forEach((root) => {
    const output = root.querySelector("[data-smart-output]");
    const input = root.querySelector("[data-smart-input]");
    const submit = root.querySelector("[data-smart-submit]");
    const payload = loadPagePayload();

    if (!output) {
      return;
    }

    const ask = (question) => {
      if (!question) {
        output.textContent = "Ask about legality, restrictions, or getting in trouble.";
        output.classList.remove("is-ready", "is-thinking");
        return;
      }

      output.textContent = "Checking this page...";
      output.classList.add("is-thinking");
      output.classList.remove("is-ready");

      window.setTimeout(() => {
        output.textContent = buildSmartAnswer(payload, question);
        output.classList.remove("is-thinking");
        output.classList.add("is-ready");
      }, 420);
    };

    root.querySelectorAll("[data-smart-prompt]").forEach((button) => {
      button.addEventListener("click", () => {
        ask(button.textContent || "");
      });
    });

    if (submit && input) {
      submit.addEventListener("click", () => ask(input.value.trim()));
      input.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
          event.preventDefault();
          ask(input.value.trim());
        }
      });
    }
  });
}

function createResultCard(item) {
  return `
    <a class="search-result" href="${item.href}">
      <div class="search-result__meta">
        <span>${item.country}</span>
        <span>${item.intentLabel}</span>
        <span>${item.verdict}</span>
        <span>${item.riskLabel}</span>
      </div>
      <h3>${item.query}</h3>
      <p>${item.summary}</p>
    </a>
  `;
}

function applyExplorerFilters(index, root) {
  const input = root.querySelector("[data-search-input]");
  const country = root.querySelector("[data-country-filter]");
  const topic = root.querySelector("[data-topic-filter]");
  const intent = root.querySelector("[data-intent-filter]");
  const verdict = root.querySelector("[data-verdict-filter]");
  const results = root.querySelector("[data-search-results]");
  const status = root.querySelector("[data-search-status]");
  const mode = root.getAttribute("data-mode") || "full";
  const limit = mode === "compact" ? 6 : 24;

  const update = () => {
    const text = (input.value || "").trim().toLowerCase();
    const filtered = index.pages.filter((item) => {
      if (country.value && item.countrySlug !== country.value) {
        return false;
      }

      if (topic.value && item.topicSlug !== topic.value) {
        return false;
      }

      if (intent.value && item.intent !== intent.value) {
        return false;
      }

      if (verdict.value && item.verdict !== verdict.value) {
        return false;
      }

      if (!text) {
        return true;
      }

      return [item.query, item.summary, item.country, item.topic, item.intentLabel]
        .join(" ")
        .toLowerCase()
        .includes(text);
    });

    const visible = filtered
      .sort((left, right) => right.riskScore - left.riskScore)
      .slice(0, limit);

    status.textContent = filtered.length
      ? `${filtered.length} matching pages`
      : "No matching pages yet";

    results.innerHTML = visible.length
      ? visible.map(createResultCard).join("")
      : `<p class="empty-state">Try another country, topic, or intent.</p>`;
  };

  [input, country, topic, intent, verdict].forEach((element) => {
    element.addEventListener("input", update);
    element.addEventListener("change", update);
  });

  const params = new URLSearchParams(window.location.search);
  const search = params.get("q");

  if (search && !input.value) {
    input.value = search;
  }

  update();
}

async function initExplorerSearch() {
  const roots = document.querySelectorAll("[data-explorer-root]");

  if (!roots.length) {
    return;
  }

  try {
    const response = await fetch("/page-index.json");
    const index = await response.json();

    roots.forEach((root) => {
      const country = root.querySelector("[data-country-filter]");
      const topic = root.querySelector("[data-topic-filter]");
      const intent = root.querySelector("[data-intent-filter]");
      const verdict = root.querySelector("[data-verdict-filter]");

      country.innerHTML += index.countries
        .map((item) => `<option value="${item.slug}">${item.name}</option>`)
        .join("");
      topic.innerHTML += index.topics
        .map((item) => `<option value="${item.slug}">${item.label}</option>`)
        .join("");
      intent.innerHTML += index.intents
        .map((item) => `<option value="${item.slug}">${item.label}</option>`)
        .join("");
      verdict.innerHTML += index.verdicts
        .map((item) => `<option value="${item}">${item}</option>`)
        .join("");

      applyExplorerFilters(index, root);
    });
  } catch {
    roots.forEach((root) => {
      const status = root.querySelector("[data-search-status]");
      if (status) {
        status.textContent = "Search index unavailable";
      }
    });
  }
}

function initRecentsAndSaved() {
  renderMiniCollection("[data-recent-pages]", STORAGE_KEYS.recent, "Open a page and it will show up here.");
  renderMiniCollection("[data-saved-pages]", STORAGE_KEYS.saved, "Save a page and it will appear here.");
}

function initPageMemory() {
  const payload = loadPagePayload();
  if (payload) {
    pushRecentPage(payload);
  }
}

initPageMemory();
initSavedPageButton();
initCopyButton();
initChecklist();
initSmartAnswer();
initExplorerSearch();
initRecentsAndSaved();
