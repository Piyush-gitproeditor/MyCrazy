# 🔍 Skill Ledger — GitHub Repository Authenticity Scorer

A Python-based tool that analyzes a GitHub repository's **commit history and structural development signals** to generate a transparent **0–100 Repository Authenticity Score**.

The goal is to identify unusual repository-development patterns such as extremely concentrated commit activity, forked repositories, minimal commit history, or generic commit messages.

> **Note:** This tool does not prove plagiarism or determine whether code is original. The score is a heuristic indicator based on Git history and should be interpreted as a development-history signal rather than definitive evidence.

---

## 🚀 Features

The analyzer retrieves repository information and commit history using the **GitHub REST API** and extracts the following features:

- 🔀 **Fork status** — checks whether the repository is a fork.
- 📝 **Commit count** — number of commits analyzed.
- 📅 **Development span** — number of days between the oldest and newest analyzed commits.
- 📊 **Average commit size** — average number of changed lines per commit.
- 📈 **Commit-size standard deviation** — measures variation in commit sizes.
- 📦 **Largest commit share** — percentage of total changes contributed by the largest commit.
- 💬 **Generic commit-message ratio** — detects commits using predefined generic messages.
- 🎯 **Authenticity score** — produces a score between 0 and 100.

---

## 🧠 How It Works

The project follows a simple pipeline:

```text
GitHub Repository
       ↓
GitHub REST API
       ↓
Commit History
       ↓
Feature Extraction
       ↓
Heuristic Scoring
       ↓
0–100 Authenticity Score
