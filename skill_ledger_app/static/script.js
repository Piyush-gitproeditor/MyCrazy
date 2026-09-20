// --- Tab switching -----------------------------------------------------
document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    document.querySelectorAll(".entry-form").forEach((f) => f.classList.remove("active"));
    tab.classList.add("active");
    document.getElementById(`form-${tab.dataset.tab}`).classList.add("active");
    hideError();
  });
});

// --- Error display -------------------------------------------------------
const errorEl = document.getElementById("form-error");
function showError(msg) {
  errorEl.textContent = msg;
  errorEl.hidden = false;
}
function hideError() {
  errorEl.hidden = true;
}

// --- Generic form submit helper ------------------------------------------
async function submitForm(form, endpoint, buildPayload) {
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    hideError();
    const btn = form.querySelector("button[type=submit]");
    const originalLabel = btn.textContent;
    btn.disabled = true;
    btn.textContent = "Checking...";

    const formData = new FormData(form);
    const payload = buildPayload(formData);

    try {
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) {
        showError(data.error || "Something went wrong.");
      } else {
        renderLedger(data.ledger);
        form.reset();
      }
    } catch (err) {
      showError("Could not reach the local server. Is app.py still running?");
    } finally {
      btn.disabled = false;
      btn.textContent = originalLabel;
    }
  });
}

submitForm(document.getElementById("form-project"), "/api/add_project", (fd) => ({
  skill: fd.get("skill"),
  owner: fd.get("owner"),
  repo: fd.get("repo"),
  date: fd.get("date"),
}));

submitForm(document.getElementById("form-certificate"), "/api/add_certificate", (fd) => ({
  skill: fd.get("skill"),
  name: fd.get("name"),
  url: fd.get("url"),
  tier: fd.get("tier"),
  date: fd.get("date"),
}));

submitForm(document.getElementById("form-achievement"), "/api/add_achievement", (fd) => ({
  skill: fd.get("skill"),
  name: fd.get("name"),
  attestation: fd.get("attestation"),
  date: fd.get("date"),
}));

// --- Reset ----------------------------------------------------------------
document.getElementById("reset-btn").addEventListener("click", async () => {
  if (!confirm("Clear every entry from the ledger?")) return;
  const res = await fetch("/api/reset", { method: "POST" });
  const data = await res.json();
  renderLedger(data.ledger);
});

// --- Rendering --------------------------------------------------------------
function renderLedger(ledger) {
  const container = document.getElementById("ledger-skills");
  const empty = document.getElementById("ledger-empty");
  container.innerHTML = "";

  const skills = Object.keys(ledger);
  empty.hidden = skills.length > 0;

  skills.forEach((skill) => {
    const data = ledger[skill];
    const block = document.createElement("div");
    block.className = "skill-block";

    const header = document.createElement("div");
    header.className = "skill-block-header";
    header.innerHTML = `<h3>${escapeHtml(skill)}</h3><span class="skill-total">${data.total}/100</span>`;
    block.appendChild(header);

    data.entries.forEach((entry) => {
      const row = document.createElement("div");
      row.className = "entry-row";

      let badge = "";
      if (entry.type === "certificate") {
        badge = entry.verified
          ? `<span class="badge verified">verified</span>`
          : `<span class="badge unverified">unreachable</span>`;
      }

      row.innerHTML = `
        <span class="entry-source">${escapeHtml(entry.source)}${badge}</span>
        <span class="entry-math">${escapeHtml(entry.explanation)}</span>
      `;
      block.appendChild(row);
    });

    container.appendChild(block);
  });
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

// --- Initial load -----------------------------------------------------------
fetch("/api/ledger")
  .then((res) => res.json())
  .then(renderLedger)
  .catch(() => showError("Could not reach the local server. Is app.py running?"));
