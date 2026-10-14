#!/usr/bin/env python3
"""The factory queue — what /factory next may start, in order.

  ready.py          every unchecked backlog line, then every open `factory` issue (oldest first)
  ready.py <n>...   just these issues (for /factory #<n>)

Prints one tab-separated line per item: STATUS, ref (#<n> or "backlog"), text, note.

  READY    nothing stands in the way — start it
  BLOCKED  a dependency hasn't landed on main yet (the note says which)
  TAKEN    a board job already has it
  CLOSED   the issue isn't open

An issue's dependencies are the issues on any body line that starts with "Depends on",
plus GitHub's own "blocked by" links. A plain backlog line can say "depends on #<n>"
anywhere in it; a "#<n>" backlog line is that issue.
A dependency has landed only when its issue was closed as completed AND, if a factory
job built it, that job's pull request is merged. Closing an issue by hand doesn't
unblock work whose code isn't on main yet.
"""

import json
import re
import subprocess
import sys
from functools import cache

from board import FACTORY, read_board


def gh(*args: str):
    result = subprocess.run(["gh", *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    return json.loads(result.stdout)


@cache
def issue(number: int) -> dict:
    return gh("issue", "view", str(number), "--json", "number,title,url,body,state,stateReason")


@cache
def pr_state(url: str) -> str:
    return gh("pr", "view", url, "--json", "state")["state"]


def depends_on_lines(text: str) -> set[int]:
    deps = set()
    for line in text.splitlines():
        if re.match(r"\W*depends on\b", line, re.IGNORECASE):
            deps.update(int(n) for n in re.findall(r"#(\d+)", line))
    return deps


def backlog_dependencies(text: str) -> set[int]:
    """A backlog item is one line, so "depends on #<n>" can appear anywhere in it."""
    match = re.search(r"\bdepends on\b(.*)", text, re.IGNORECASE)
    return {int(n) for n in re.findall(r"#(\d+)", match.group(1))} if match else set()


def native_blockers(number: int) -> set[int]:
    try:
        links = gh("api", f"repos/{{owner}}/{{repo}}/issues/{number}/dependencies/blocked_by")
    except RuntimeError as error:
        print(f"ready.py: couldn't read GitHub blocked-by links for #{number}: {error}", file=sys.stderr)
        return set()
    return {link["number"] for link in links}


def job_for(jobs: list[dict], url: str) -> dict | None:
    return next((job for job in jobs if job.get("issue") == url), None)


def not_landed(number: int, jobs: list[dict]) -> str | None:
    """Why dependency #number isn't on main yet, or None if it is."""
    dep = issue(number)
    if dep["state"] == "OPEN":
        return f"#{number} is open"
    if dep["stateReason"] not in ("COMPLETED", "", None):
        return f"#{number} was closed as {dep['stateReason'].lower().replace('_', ' ')}"
    job = job_for(jobs, dep["url"])
    if job and not job.get("pr"):
        return f"#{number}'s job {job['id']} has no pull request yet"
    if job and pr_state(job["pr"]) != "MERGED":
        return f"#{number}'s pull request isn't merged ({job['pr']})"
    return None


def status(deps: set[int], jobs: list[dict]) -> tuple[str, str]:
    waiting = [reason for dep in sorted(deps) if (reason := not_landed(dep, jobs))]
    return ("BLOCKED", "waiting: " + "; ".join(waiting)) if waiting else ("READY", "")


def issue_item(number: int, jobs: list[dict]) -> tuple[str, str, str, str]:
    item = issue(number)
    ref, title = f"#{number}", item["title"]
    if item["state"] != "OPEN":
        return ("CLOSED", ref, title, "")
    job = job_for(jobs, item["url"])
    if job:
        return ("TAKEN", ref, title, f"job {job['id']} ({job['stage']})")
    verdict, note = status(depends_on_lines(item["body"]) | native_blockers(number), jobs)
    return (verdict, ref, title, note)


def backlog_items(jobs: list[dict]):
    requests = {job["request"] for job in jobs}
    text = re.sub(r"<!--.*?-->", "", (FACTORY / "backlog.md").read_text(), flags=re.DOTALL)
    for line in text.splitlines():
        match = re.match(r"- \[ \] (.+)", line)
        if not match:
            continue
        text = match.group(1).strip()
        issue_ref = re.match(r"#(\d+)\b", text)
        if issue_ref:
            yield issue_item(int(issue_ref.group(1)), jobs)
        elif text in requests:
            yield ("TAKEN", "backlog", text, "already on the board")
        else:
            verdict, note = status(backlog_dependencies(text), jobs)
            yield (verdict, "backlog", text, note)


def queue(jobs: list[dict]):
    seen = set()
    for item in backlog_items(jobs):
        seen.add(item[1])
        yield item
    open_issues = gh("issue", "list", "--label", "factory", "--state", "open", "--limit", "200",
                     "--json", "number", "--search", "sort:created-asc")
    for entry in open_issues:
        if f"#{entry['number']}" not in seen:
            yield issue_item(entry["number"], jobs)


def main():
    jobs = read_board()["jobs"]
    items = [issue_item(int(n.lstrip("#")), jobs) for n in sys.argv[1:]] if sys.argv[1:] else queue(jobs)
    for item in items:
        print("\t".join(item))


if __name__ == "__main__":
    main()
