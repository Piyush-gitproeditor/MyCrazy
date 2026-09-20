# Skill Ledger — Local Prototype

A small local web app that puts a real frontend on the authenticity
scorer and the transparent scoring engine, backed by a Flask server
that runs on your own machine.

## Setup

```
pip install flask requests
```

Set your GitHub token in the same terminal you'll run the app from
(never paste it into any file):

```
# Mac/Linux
export GITHUB_TOKEN="ghp_your_token_here"

# Windows (cmd)
set GITHUB_TOKEN=ghp_your_token_here
```

## Run it

```
python app.py
```

Then open **http://127.0.0.1:5000** in your browser.

## How it works

- **Project tab** — enter a GitHub owner + repo. The server calls
  `authenticity_scorer.py` live against the real repo and scores it.
- **Certificate tab** — enter a verification URL. The server checks
  the link actually resolves before any score is given.
- **Achievement tab** — enter an achievement and an attestation
  level. This is *not* auto-verified — it's flagged as self-declared,
  same limitation as the command-line version.

All entries are saved to `ledger_entries.json` in this folder, so
your ledger persists between runs. Use "Clear all" in the app to
reset it.

## Files

- `app.py` — Flask backend + scoring logic
- `authenticity_scorer.py` — the GitHub commit-based originality scorer
- `templates/index.html` — the page
- `static/style.css`, `static/script.js` — styling and frontend logic
- `ledger_entries.json` — created automatically the first time you add an entry
