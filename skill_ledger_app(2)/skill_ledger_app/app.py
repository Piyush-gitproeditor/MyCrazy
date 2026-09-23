"""
Skill Ledger — Local Web App (backend)

Wraps three things behind a local web server:
  1. authenticity_scorer.py  — live GitHub project scoring
  2. Certificate link verification (is the URL real?)
  3. The transparent weighted scoring engine

Your GITHUB_TOKEN never leaves this machine — the browser only ever
talks to http://127.0.0.1:5000, never to GitHub directly.

Setup:
  pip install flask requests
  export GITHUB_TOKEN="ghp_..."      (Windows: set GITHUB_TOKEN=ghp_...)
  python app.py
  Open http://127.0.0.1:5000 in your browser

All entries persist in ledger_entries.json in this same folder.
"""

import json
import os
from datetime import date, datetime

from flask import Flask, jsonify, render_template, request
import requests

from authenticity_scorer import extract_features, score as authenticity_score

app = Flask(__name__)

LEDGER_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ledger_entries.json")

WEIGHTS = {
    "certificate": {"base_by_tier": {1: 40, 2: 25, 3: 10}},
    "project": {"base": 50},
    "achievement": {"base_by_attestation": {"institutional": 35, "self_reported": 10}},
    "recency": {"decay_per_year": 0.10, "floor": 0.5},
    "skill_cap": 100,
}


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------
def load_entries():
    if not os.path.exists(LEDGER_FILE):
        return []
    with open(LEDGER_FILE) as f:
        return json.load(f)


def save_entries(entries):
    with open(LEDGER_FILE, "w") as f:
        json.dump(entries, f, indent=2)


# ---------------------------------------------------------------------------
# Scoring primitives (same logic as scoring_engine_live.py)
# ---------------------------------------------------------------------------
def recency_factor(entry_date: str, today: date = None) -> float:
    today = today or date.today()
    d = datetime.strptime(entry_date, "%Y-%m-%d").date()
    years_since = max(0.0, (today - d).days / 365.25)
    factor = 1.0 - WEIGHTS["recency"]["decay_per_year"] * years_since
    return round(max(WEIGHTS["recency"]["floor"], factor), 3)


def verify_certificate_link(url: str, timeout: int = 6) -> bool:
    try:
        r = requests.get(url, timeout=timeout, allow_redirects=True)
        return r.status_code == 200
    except requests.RequestException:
        return False


def score_entry(entry: dict) -> dict:
    etype = entry["type"]
    rec = recency_factor(entry["date"])
    out = dict(entry)

    if etype == "certificate":
        if not entry.get("verified"):
            out["score"] = 0.0
            out["explanation"] = "Link unverified -> score 0.0"
            return out
        base = WEIGHTS["certificate"]["base_by_tier"][entry["tier"]]
        raw = round(base * rec, 1)
        out["score"] = raw
        out["explanation"] = f"Tier {entry['tier']} cert, link verified -> base {base} x recency {rec} = {raw}"
        return out

    if etype == "project":
        evidence = entry.get("evidence_score", 0)
        base = WEIGHTS["project"]["base"]
        raw = round(base * (evidence / 100) * rec, 1)
        out["score"] = raw
        out["explanation"] = f"base {base} x authenticity {evidence}/100 x recency {rec} = {raw}"
        return out

    if etype == "achievement":
        base = WEIGHTS["achievement"]["base_by_attestation"][entry["attestation"]]
        raw = round(base * rec, 1)
        out["score"] = raw
        out["explanation"] = f"{entry['attestation']} -> base {base} x recency {rec} = {raw} (self-declared, not auto-verified)"
        return out

    raise ValueError(f"Unknown entry type: {etype}")


def compute_ledger() -> dict:
    entries = load_entries()
    scored = [score_entry(e) for e in entries]
    by_skill = {}
    for s in scored:
        by_skill.setdefault(s["skill"], []).append(s)

    results = {}
    for skill, items in by_skill.items():
        total = sum(i["score"] for i in items)
        results[skill] = {
            "total": round(min(total, WEIGHTS["skill_cap"]), 1),
            "raw_total": round(total, 1),
            "entries": items,
        }
    return results


def compute_trust_ratio(ledger: dict) -> dict:
    """
    What fraction of the total ledger score comes from independently
    checkable evidence, vs. self-declared claims.

    - certificate: counts as trusted only if its link was verified live
    - project: always counts as trusted (it's always live-scored from
      real commit history, never typed in by hand)
    - achievement: never counts as trusted in this prototype, regardless
      of attestation level — nothing currently checks institutional
      attestations independently, so being honest about that gap here
      is the point, not a bug.
    """
    trusted = 0.0
    total = 0.0
    for data in ledger.values():
        for entry in data["entries"]:
            total += entry["score"]
            if entry["type"] == "certificate" and entry.get("verified"):
                trusted += entry["score"]
            elif entry["type"] == "project":
                trusted += entry["score"]

    ratio = round((trusted / total) * 100, 1) if total > 0 else 0.0
    return {"trusted_points": round(trusted, 1), "total_points": round(total, 1), "ratio": ratio}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/profile")
def profile():
    return render_template("profile.html")


@app.route("/api/profile")
def api_profile():
    ledger = compute_ledger()
    return jsonify({"skills": ledger, "trust": compute_trust_ratio(ledger)})


@app.route("/api/ledger")
def api_ledger():
    return jsonify(compute_ledger())


@app.route("/api/add_project", methods=["POST"])
def add_project():
    data = request.json
    owner, repo = data["owner"].strip(), data["repo"].strip()

    try:
        features = extract_features(owner, repo)
        evidence = authenticity_score(features)
    except Exception as e:
        return jsonify({"error": f"Could not score {owner}/{repo}: {e}"}), 400

    entry = {
        "skill": data["skill"].strip(),
        "type": "project",
        "source": f"https://github.com/{owner}/{repo}",
        "evidence_score": evidence,
        "features": features,
        "date": data["date"],
    }
    entries = load_entries()
    entries.append(entry)
    save_entries(entries)
    return jsonify({"entry": score_entry(entry), "ledger": compute_ledger()})


@app.route("/api/add_certificate", methods=["POST"])
def add_certificate():
    data = request.json
    url = data["url"].strip()
    verified = verify_certificate_link(url)

    entry = {
        "skill": data["skill"].strip(),
        "type": "certificate",
        "source": data.get("name", "").strip() or url,
        "url": url,
        "tier": int(data["tier"]),
        "verified": verified,
        "date": data["date"],
    }
    entries = load_entries()
    entries.append(entry)
    save_entries(entries)
    return jsonify({"entry": score_entry(entry), "ledger": compute_ledger()})


@app.route("/api/add_achievement", methods=["POST"])
def add_achievement():
    data = request.json
    entry = {
        "skill": data["skill"].strip(),
        "type": "achievement",
        "source": data["name"].strip(),
        "attestation": data["attestation"],
        "date": data["date"],
    }
    entries = load_entries()
    entries.append(entry)
    save_entries(entries)
    return jsonify({"entry": score_entry(entry), "ledger": compute_ledger()})


@app.route("/api/reset", methods=["POST"])
def reset():
    save_entries([])
    return jsonify({"ledger": compute_ledger()})


if __name__ == "__main__":
    if not os.environ.get("GITHUB_TOKEN"):
        print("WARNING: GITHUB_TOKEN not set in this terminal — project scoring will fail or rate-limit.")
    app.run(debug=True, port=5000)
