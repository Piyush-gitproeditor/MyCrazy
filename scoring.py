import json
import requests
from datetime import date, datetime

from test import extract_features, score as authenticity_score

# Same transparent weights table as before — unchanged.
WEIGHTS = {
    "certificate": {"base_by_tier": {1: 40, 2: 25, 3: 10}},
    "project": {"base": 50},
    "achievement": {
        "base_by_attestation": {"institutional": 35, "self_reported": 10},
    },
    "recency": {"decay_per_year": 0.10, "floor": 0.5},
    "skill_cap": 100,
}

def recency_factor(entry_date: str, today: date = None) -> float:
    today = today or date.today()
    d = datetime.strptime(entry_date, "%Y-%m-%d").date()
    years_since = max(0.0, (today - d).days / 365.25)
    factor = 1.0 - WEIGHTS["recency"]["decay_per_year"] * years_since
    return round(max(WEIGHTS["recency"]["floor"], factor), 3)

# NEW: live certificate verification — is the link actually real?
def verify_certificate_link(url: str, timeout: int = 6) -> bool:
    try:
        r = requests.get(url, timeout=timeout, allow_redirects=True)
        return r.status_code == 200
    except requests.RequestException:
        return False

# NEW: parse a GitHub URL and get a live authenticity score for it.
def parse_github_url(url: str) -> tuple:
    parts = url.rstrip("/").split("/")
    return parts[-2], parts[-1]  # owner, repo

def live_project_score(url: str) -> float:
    owner, repo = parse_github_url(url)
    features = extract_features(owner, repo)
    return authenticity_score(features)

# Score one entry — now with real verification instead of trusted input.
def score_entry(entry: dict) -> dict:
    etype = entry["type"]
    rec = recency_factor(entry["date"])

    if etype == "certificate":
        reachable = verify_certificate_link(entry["source"])
        if not reachable:
            return {
                "skill": entry["skill"],
                "score": 0.0,
                "explanation": (
                    f"[{entry['skill']}] Certificate '{entry['source']}' -> "
                    f"UNVERIFIED (link unreachable) -> score 0.0"
                ),
            }
        base = WEIGHTS["certificate"]["base_by_tier"][entry["tier"]]
        raw = base * rec
        explanation = (
            f"[{entry['skill']}] Certificate '{entry['source']}' "
            f"(Tier {entry['tier']}, link verified) -> base {base} x recency {rec} = {round(raw, 1)}"
        )

    elif etype == "project":
        evidence_score = live_project_score(entry["source"])
        base = WEIGHTS["project"]["base"]
        raw = base * (evidence_score / 100) * rec
        explanation = (
            f"[{entry['skill']}] Project '{entry['source']}' -> base {base} "
            f"x LIVE authenticity {evidence_score}/100 x recency {rec} = {round(raw, 1)}"
        )

    elif etype == "achievement":
        base = WEIGHTS["achievement"]["base_by_attestation"][entry["attestation"]]
        raw = base * rec
        explanation = (
            f"[{entry['skill']}] Achievement '{entry['source']}' "
            f"({entry['attestation']}) -> base {base} x recency {rec} = {round(raw, 1)} "
            f"[NOTE: attestation is self-declared in this prototype, not auto-verified]"
        )

    else:
        raise ValueError(f"Unknown entry type: {etype}")

    return {"skill": entry["skill"], "score": round(raw, 1), "explanation": explanation}


def score_ledger(entries: list) -> dict:
    scored = [score_entry(e) for e in entries]
    by_skill = {}
    for s in scored:
        by_skill.setdefault(s["skill"], []).append(s)

    results = {}
    for skill, items in by_skill.items():
        total = sum(i["score"] for i in items)
        results[skill] = {
            "total": round(min(total, WEIGHTS["skill_cap"]), 1),
            "raw_total_before_cap": round(total, 1),
            "entries": items,
        }
    return results

if __name__ == "__main__":
    with open("ledger_entries.json") as f:
        entries = json.load(f)

    print("Fetching + verifying entries... (this hits the network, may take a few seconds)\n")
    results = score_ledger(entries)
    print("SKILL LEDGER — LIVE SCORE BREAKDOWN")
    for skill, data in results.items():
        print(f"\n{skill}: {data['total']}/100")
        print("-" * 40)
        for e in data["entries"]:
            print(f"  {e['explanation']}")