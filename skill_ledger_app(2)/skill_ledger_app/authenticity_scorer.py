"""
Skill Ledger — Project Authenticity Scorer (v0)

What this does:
  Pulls commit history for a GitHub repo and computes a 0-100
  "originality score" based on structural signals — no LLM needed yet.
  This is Step 2-4 of the build plan: raw data -> features -> score.

Setup:
  1. pip install requests
  2. Set your GitHub token as an environment variable (don't hardcode it):
       export GITHUB_TOKEN="ghp_xxxxxxxxxxxx"      (Mac/Linux)
       setx GITHUB_TOKEN "ghp_xxxxxxxxxxxx"          (Windows, new terminal after)
  3. Run:  python authenticity_scorer.py <owner> <repo>
     e.g.  python authenticity_scorer.py torvalds linux
"""

import os
import sys
import statistics
from datetime import datetime
import requests

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    print("WARNING: No GITHUB_TOKEN found in environment. You'll hit low rate limits (60/hr).")

HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}


def get_repo_meta(owner: str, repo: str) -> dict:
    """Basic repo info — tells us if it's a fork, and repo age."""
    url = f"https://api.github.com/repos/{owner}/{repo}"
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    return r.json()


def get_commits(owner: str, repo: str, max_commits: int = 100) -> list:
    """Fetch up to max_commits commit SHAs (most recent first)."""
    commits = []
    page = 1
    while len(commits) < max_commits:
        url = f"https://api.github.com/repos/{owner}/{repo}/commits"
        r = requests.get(url, headers=HEADERS, params={"per_page": 100, "page": page})
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        commits.extend(batch)
        page += 1
        if len(batch) < 100:
            break
    return commits[:max_commits]


def get_commit_detail(owner: str, repo: str, sha: str) -> dict:
    """Full stats (additions/deletions) for one commit."""
    url = f"https://api.github.com/repos/{owner}/{repo}/commits/{sha}"
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    data = r.json()
    return {
        "date": data["commit"]["author"]["date"],
        "message": data["commit"]["message"],
        "additions": data.get("stats", {}).get("additions", 0),
        "deletions": data.get("stats", {}).get("deletions", 0),
        "total": data.get("stats", {}).get("total", 0),
    }


def extract_features(owner: str, repo: str, max_commits: int = 50) -> dict:
    """Pull commits and turn them into the raw feature set the scorer uses."""
    meta = get_repo_meta(owner, repo)
    commit_list = get_commits(owner, repo, max_commits=max_commits)

    details = []
    for c in commit_list:
        try:
            details.append(get_commit_detail(owner, repo, c["sha"]))
        except requests.HTTPError:
            continue  # skip commits GitHub won't return stats for

    if not details:
        raise ValueError("No commit data retrieved — check owner/repo name and token.")

    dates = [datetime.fromisoformat(d["date"].replace("Z", "+00:00")) for d in details]
    sizes = [d["total"] for d in details]
    messages = [d["message"].strip().lower() for d in details]

    span_days = (max(dates) - min(dates)).days
    generic_msgs = {"initial commit", "update", "fix", "first commit", "add files"}
    generic_ratio = sum(1 for m in messages if m in generic_msgs) / len(messages)

    return {
        "is_fork": meta.get("fork", False),
        "commit_count": len(details),
        "span_days": span_days,
        "avg_commit_size": statistics.mean(sizes) if sizes else 0,
        "size_stdev": statistics.pstdev(sizes) if len(sizes) > 1 else 0,
        "largest_commit_share": max(sizes) / sum(sizes) if sum(sizes) > 0 else 0,
        "generic_message_ratio": generic_ratio,
    }


def score(features: dict) -> float:
    """
    Transparent weighted scoring, 0-100. Tune these weights after
    calibrating on real repos — this is a starting point, not gospel.
    """
    s = 100.0

    if features["is_fork"]:
        s -= 30

    if features["commit_count"] < 3:
        s -= 25  # almost no history = can't tell if it's genuine work

    if features["span_days"] < 1:
        s -= 30  # everything committed in one sitting = dump, not build

    if features["largest_commit_share"] > 0.8:
        s -= 20  # one commit did nearly all the work

    s -= features["generic_message_ratio"] * 15  # lazy commit messages

    return round(max(0, min(100, s)), 1)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python authenticity_scorer.py <owner> <repo>")
        sys.exit(1)

    owner, repo = sys.argv[1], sys.argv[2]
    print(f"Analyzing {owner}/{repo} ...")
    feats = extract_features(owner, repo)
    result = score(feats)

    print("\nFeatures:")
    for k, v in feats.items():
        print(f"  {k}: {v}")
    print(f"\nOriginality score: {result}/100")
