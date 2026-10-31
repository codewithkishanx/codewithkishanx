#!/usr/bin/env python3
"""
Keeps README.md honest.

Two things get rewritten on every run:
  1. The repo table between  <!-- LATEST_REPOS:START --> ... <!-- LATEST_REPOS:END -->
  2. The timestamp between    <!-- LAST_UPDATED --> ... <!-- /LAST_UPDATED -->

Stdlib only, so the Actions job needs zero dependencies.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.request

USER = os.environ.get("GITHUB_REPOSITORY_OWNER", "codewithkishanx")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
README = "README.md"

LANGS_PER_REPO = 1
MAX_REPOS = 6

# Hand-written pitches, used when a repo has no description on GitHub.
# Fixing the description in repo settings is still better — this is a fallback.
DESCRIPTIONS = {
    "Pylab-26-27": "Python lab work — fundamentals, exercises and small scripts",
    "rent-a-boyfriend": "A playful full-stack side project built to practice product thinking",
    "Dsa-Arcade-Frontend": "Frontend for DSA Arcade — algorithm practice turned into a game",
    "DSA_ARCADE-": "Main DSA Arcade app — gamified data-structures & algorithms practice",
    "Dsa-Arcade-Backend": "REST API powering DSA Arcade — auth, progress tracking, problem bank",
    "STMP-FRONTEND": "Student Project Management System — role-based platform for students, mentors and admins",
    "Leetcode": "My Java solutions to LeetCode problems, organised by topic",
    "FinanceFlow": "AI-assisted finance tracker — spending insights and budget tracking",
    "myfolio": "MyFolio — AI-powered portfolio builder that deploys from an uploaded resume",
}


def api(url: str):
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", f"{USER}-readme-bot")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_repos() -> list[dict]:
    repos = api(
        f"https://api.github.com/users/{USER}/repos"
        "?per_page=100&sort=pushed&direction=desc&type=owner"
    )
    out = []
    for r in repos:
        if r["name"].lower() == USER.lower():      # skip the profile repo itself
            continue
        if r.get("archived"):
            continue
        out.append(r)
        if len(out) >= MAX_REPOS:
            break
    return out


def describe(repo: dict) -> str:
    desc = (repo.get("description") or "").strip()
    if not desc:
        desc = DESCRIPTIONS.get(repo["name"], "")
    if not desc:
        desc = "Personal project"
    desc = desc.replace("|", "\\|")
    return desc[:110] + ("…" if len(desc) > 110 else "")


def star_cell(repo: dict) -> str:
    return f"⭐ {repo['stargazers_count']}" if repo["stargazers_count"] else "—"


def build_table(repos: list[dict]) -> str:
    rows = [
        "| Repository | What it is | Stack | Stars |",
        "| :--- | :--- | :--- | :---: |",
    ]
    for r in repos:
        name = r["name"]
        lang = r.get("language") or "—"
        fork = " *(fork)*" if r.get("fork") else ""
        rows.append(
            f"| **[{'🔒 ' if r.get('private') else ''}{name}]({r['html_url']})**{fork} "
            f"| {describe(r)} | `{lang}` | {star_cell(r)} |"
        )
    return "\n".join(rows)


def replace_block(text: str, start: str, end: str, body: str, inline: bool = False) -> str:
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.DOTALL)
    if not pattern.search(text):
        print(f"!! markers not found: {start}", file=sys.stderr)
        return text
    wrapped = f"{start}{body}{end}" if inline else f"{start}\n{body}\n{end}"
    return pattern.sub(lambda _m: wrapped, text)


def main() -> int:
    try:
        with open(README, encoding="utf-8") as fh:
            text = fh.read()
    except FileNotFoundError:
        print("README.md not found", file=sys.stderr)
        return 1

    try:
        repos = fetch_repos()
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        # Never fail the build just because the API hiccuped.
        print(f"!! could not reach GitHub API: {exc}", file=sys.stderr)
        repos = []

    if repos:
        text = replace_block(
            text,
            "<!-- LATEST_REPOS:START -->",
            "<!-- LATEST_REPOS:END -->",
            build_table(repos),
        )

    stamp = dt.datetime.now(dt.timezone.utc).strftime("%d %b %Y, %H:%M UTC")
    text = replace_block(
        text,
        "<!-- LAST_UPDATED -->",
        "<!-- /LAST_UPDATED -->",
        f" {stamp} ",
        inline=True,
    )

    with open(README, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)

    print(f"README refreshed: {len(repos)} repos, {stamp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
