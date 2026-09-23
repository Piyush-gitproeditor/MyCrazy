function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

function badgeFor(entry) {
  if (entry.type === "certificate") {
    return entry.verified
      ? `<span class="badge verified">verified link</span>`
      : `<span class="badge unverified">unverified</span>`;
  }
  if (entry.type === "project") {
    return `<span class="badge verified">live-scored</span>`;
  }
  return `<span class="badge unverified">self-declared</span>`;
}

function renderProfile(data) {
  const { skills, trust } = data;

  document.getElementById("trust-percent").textContent = `${trust.ratio}%`;
  document.getElementById("trust-detail").textContent =
    trust.total_points > 0
      ? `${trust.trusted_points} of ${trust.total_points} total ledger points come from a verified link or a live-scored project.`
      : "Add entries in the editor to see this fill in.";

  const container = document.getElementById("profile-skills");
  const empty = document.getElementById("profile-empty");
  container.innerHTML = "";

  const skillNames = Object.keys(skills);
  empty.hidden = skillNames.length > 0;

  skillNames.forEach((skill) => {
    const s = skills[skill];
    const block = document.createElement("div");
    block.className = "skill-block";

    const header = document.createElement("div");
    header.className = "skill-block-header";
    header.innerHTML = `<h3>${escapeHtml(skill)}</h3><span class="skill-total">${s.total}/100</span>`;
    block.appendChild(header);

    s.entries.forEach((entry) => {
      const row = document.createElement("div");
      row.className = "entry-row";
      row.innerHTML = `
        <span class="entry-source">${escapeHtml(entry.source)} ${badgeFor(entry)}</span>
        <span class="entry-math">${escapeHtml(entry.explanation)}</span>
      `;
      block.appendChild(row);
    });

    container.appendChild(block);
  });
}

fetch("/api/profile")
  .then((res) => res.json())
  .then(renderProfile)
  .catch(() => {
    document.getElementById("trust-detail").textContent =
      "Could not reach the local server. Is app.py running?";
  });
