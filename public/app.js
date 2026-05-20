const askBtn = document.querySelector("#askBtn");
const ingestBtn = document.querySelector("#ingestBtn");
const ingestConfluenceBtn = document.querySelector("#ingestConfluenceBtn");
const questionInput = document.querySelector("#question");
const toneInput = document.querySelector("#tone");
const answerOutput = document.querySelector("#answer");
const statusEl = document.querySelector("#status");
const sourcesEl = document.querySelector("#sources");
const toastEl = document.querySelector("#toast");
let toastTimer = null;

function setBusy(isBusy, label) {
  askBtn.disabled = isBusy;
  ingestBtn.disabled = isBusy;
  ingestConfluenceBtn.disabled = isBusy;
  statusEl.textContent = label;
}

function showToast(message, type = "success") {
  if (toastTimer) {
    clearTimeout(toastTimer);
  }
  toastEl.textContent = message;
  toastEl.classList.toggle("is-error", type === "error");
  toastEl.classList.add("is-visible");
  toastTimer = setTimeout(() => {
    toastEl.classList.remove("is-visible");
  }, 2000);
}

async function postJson(url, body = {}) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

function renderSources(result) {
  if (!result.sources.length) {
    sourcesEl.innerHTML = "<p>No sources yet. Ingest sample documents or try another question.</p>";
    return;
  }

  const risks = result.risks.length
    ? `<p class="risk">Risk keywords: ${result.risks.join(", ")}</p>`
    : "";
  const cards = result.sources
    .map(
      (source) => `
        <article class="source-item">
          <a href="${source.url}" target="_blank" rel="noreferrer">${source.title}<span aria-hidden="true"> ↗</span></a>
          <p>${source.section || "Unlabeled section"} · Relevance ${relevanceLabel(source.score)}</p>
        </article>
      `,
    )
    .join("");

  sourcesEl.innerHTML = `${risks}<div class="source-list">${cards}</div>`;
}

function relevanceLabel(score) {
  if (score >= 0.65) {
    return "High";
  }
  if (score >= 0.5) {
    return "Medium";
  }
  return "Low";
}

ingestBtn.addEventListener("click", async () => {
  try {
    setBusy(true, "Ingesting");
    const result = await postJson("/api/ingest-samples");
    statusEl.textContent = "Ready";
    showToast(`Indexed ${result.chunks_indexed} sample chunks`);
  } catch (error) {
    statusEl.textContent = "Ready";
    showToast(`Ingestion failed: ${error.message}`, "error");
  } finally {
    askBtn.disabled = false;
    ingestBtn.disabled = false;
    ingestConfluenceBtn.disabled = false;
  }
});

ingestConfluenceBtn.addEventListener("click", async () => {
  try {
    setBusy(true, "Syncing Confluence");
    const result = await postJson("/api/ingest-confluence");
    statusEl.textContent = "Ready";
    showToast(`Indexed ${result.pages_indexed} pages / ${result.chunks_indexed} chunks`);
  } catch (error) {
    statusEl.textContent = "Ready";
    showToast(`Confluence sync failed: ${error.message}`, "error");
  } finally {
    askBtn.disabled = false;
    ingestBtn.disabled = false;
    ingestConfluenceBtn.disabled = false;
  }
});

askBtn.addEventListener("click", async () => {
  const question = questionInput.value.trim();
  if (!question) {
    statusEl.textContent = "Enter a question";
    return;
  }

  try {
    setBusy(true, "Generating");
    const result = await postJson("/api/ask", {
      question,
      tone: toneInput.value,
    });
    answerOutput.textContent = result.answer;
    statusEl.textContent = result.used_mock_ai ? "Mock AI" : "Generated";
    renderSources(result);
  } catch (error) {
    statusEl.textContent = "Generation failed";
    answerOutput.textContent = error.message;
  } finally {
    askBtn.disabled = false;
    ingestBtn.disabled = false;
    ingestConfluenceBtn.disabled = false;
  }
});
