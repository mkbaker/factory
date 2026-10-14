#!/usr/bin/env python3
"""The factory board — the only way to change factory/board.json.

Every write holds an exclusive lock and replaces the file atomically, so several jobs
(in one Claude session or in several) can update the board at once without losing
each other's changes. Works from the main checkout or any worktree.

  board.py new <slug> <request> [--issue URL]   create a job + its folder; prints the id
  board.py set <id> '<json object>'             merge top-level fields into a job
  board.py review <id> <reviewer> <verdict>     set one reviewer's chip
  board.py round <id> <reviewer>...             start the next round; prints its number
  board.py get [<id>]                           print one job, or the whole board
"""

import argparse
import fcntl
import json
import os
import re
import subprocess
import sys
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

VERDICTS = {"pending", "PASS", "CHANGES", "SKIPPED"}


def main_checkout() -> Path:
    git_dir = subprocess.run(
        ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return Path(git_dir).parent


FACTORY = main_checkout() / "factory"
BOARD = FACTORY / "board.json"
JOBS = FACTORY / "jobs"
LOCK = JOBS / ".board.lock"


def read_board() -> dict:
    return json.loads(BOARD.read_text()) if BOARD.exists() else {"jobs": []}


@contextmanager
def locked_board():
    """Yield the board for editing; it is written back only if the block succeeds."""
    JOBS.mkdir(parents=True, exist_ok=True)
    with open(LOCK, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        board = read_board()
        yield board
        tmp = JOBS / "board.json.tmp"
        tmp.write_text(json.dumps(board, indent=2) + "\n")
        os.replace(tmp, BOARD)


def find(board: dict, job_id: str) -> dict:
    for job in board["jobs"]:
        if job["id"] == job_id:
            return job
    sys.exit(f"board.py: no job {job_id!r} on the board")


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def cmd_new(args):
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", args.slug):
        sys.exit(f"board.py: slug must be kebab-case, got {args.slug!r}")
    with locked_board() as board:
        for job in board["jobs"]:
            if args.issue and job.get("issue") == args.issue:
                sys.exit(f"board.py: {job['id']} already has issue {args.issue}")
            if job["request"] == args.request:
                sys.exit(f"board.py: {job['id']} already has this request")
        numbers = [int(job["id"][:3]) for job in board["jobs"]]
        numbers += [int(p.name[:3]) for p in JOBS.iterdir() if re.match(r"\d{3}-", p.name)]
        job_id = f"{max(numbers, default=0) + 1:03d}-{args.slug}"
        (JOBS / job_id).mkdir()
        board["jobs"].append({
            "id": job_id,
            "title": None,
            "request": args.request,
            "branch": f"factory/{job_id}",
            "worktree": f".claude/worktrees/{job_id}",
            "stage": "spec",
            "round": 0,
            "reviews": {},
            "history": [],
            "decision": None,
            "issue": args.issue,
            "pr": None,
            "updated": now(),
        })
    print(job_id)


def cmd_set(args):
    fields = json.loads(args.fields)
    if not isinstance(fields, dict) or "id" in fields:
        sys.exit("board.py: set takes a JSON object of fields (not including id)")
    with locked_board() as board:
        job = find(board, args.id)
        job.update(fields)
        job["updated"] = now()


def cmd_review(args):
    if args.verdict not in VERDICTS:
        sys.exit(f"board.py: verdict must be one of {sorted(VERDICTS)}")
    with locked_board() as board:
        job = find(board, args.id)
        job["reviews"][args.reviewer] = args.verdict
        job["updated"] = now()


def cmd_round(args):
    with locked_board() as board:
        job = find(board, args.id)
        if job["round"] > 0:
            job["history"].append({"round": job["round"], "reviews": job["reviews"]})
        job["round"] += 1
        job["reviews"] = {reviewer: "pending" for reviewer in args.reviewers}
        job["updated"] = now()
        (JOBS / args.id / f"round-{job['round']}").mkdir(exist_ok=True)
    print(job["round"])


def cmd_get(args):
    board = read_board()
    print(json.dumps(find(board, args.id) if args.id else board, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Update the factory board.")
    commands = parser.add_subparsers(required=True)

    new = commands.add_parser("new")
    new.add_argument("slug")
    new.add_argument("request")
    new.add_argument("--issue")
    new.set_defaults(run=cmd_new)

    set_ = commands.add_parser("set")
    set_.add_argument("id")
    set_.add_argument("fields")
    set_.set_defaults(run=cmd_set)

    review = commands.add_parser("review")
    review.add_argument("id")
    review.add_argument("reviewer")
    review.add_argument("verdict")
    review.set_defaults(run=cmd_review)

    round_ = commands.add_parser("round")
    round_.add_argument("id")
    round_.add_argument("reviewers", nargs="+")
    round_.set_defaults(run=cmd_round)

    get = commands.add_parser("get")
    get.add_argument("id", nargs="?")
    get.set_defaults(run=cmd_get)

    args = parser.parse_args()
    args.run(args)


if __name__ == "__main__":
    main()
