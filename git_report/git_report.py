#!/usr/bin/env python3

import argparse
import csv
import json
import os
import re
import subprocess
import sys
import logging
from collections import defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import List, Pattern, Dict

import matplotlib.pyplot as plt
from dateutil.relativedelta import relativedelta


EXIT_SUCCESS = 0
EXIT_FAILURE = 1


class PeriodType(Enum):
    DAY = 0
    WEEK = 1
    MONTH = 2


@dataclass
class Commit:
    repo_name: str
    hash: str
    author: str
    date: str
    subject: str


type Commits = list[Commit]


def find_git_repos(base_path: str, exclude_patterns: List[Pattern[str]]) -> List[str]:
    """
    Recursively find Git repositories under base_path, excluding any directory
    whose path matches at least one regext in exclude_patterns

    :param base_path: str, root directory to start search
    :param exclude_patterns: list of compiled regex patterns
    :return: list of repo paths
    """
    git_repos = []
    for root, dirs, files in os.walk(base_path):
        if any(pat.search(root) for pat in exclude_patterns):
            dirs.clear()  # prevent descending further
            continue
        if ".git" in dirs:
            git_repos.append(root)
            dirs.clear()  # prevent descending further
    return git_repos


def get_commit_stats(
    repo_path: Path, author_filter: str, since: str, until: str
) -> Commits:
    """
    Get a list of commit dates (YYYY-MM-DD) for commits matching the author

    :param repo_path: path to the git repository
    :param author_filter: author email or username
    :param since: start date (YYYY-MM-DD)
    :param until: end date (YYYY-MM-DD)
    :return: list of commit dates as strings
    """
    cmd = [
        "git",
        "-C",
        repo_path.absolute(),
        "log",
        "--all",
        f"--since={since}",
        f"--until={until}",
        f"--author={author_filter}",
        "--pretty=format:%H|%ae|%ad|%s",
        "--date=short",
    ]
    result = subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    if result.returncode != 0:
        return []

    repo_name: str = os.path.basename(repo_path.rstrip(os.sep))
    commits: Commits = []

    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        commit_hash, author_email, commit_date, commit_subj = line.split("|", 3)
        commits.append(
            Commit(repo_name, commit_hash[:7], author_email, commit_date, commit_subj)
        )
    return commits


def format_period(date: datetime, period: PeriodType) -> str:
    if period is PeriodType.DAY:
        return date.strftime("%Y-%m-%d")
    elif period is PeriodType.WEEK:
        return f"{date.isocalendar().year}-W{date.isocalendar().week:02d}"
    elif period is PeriodType.MONTH:
        return date.strftime("%Y-%m")
    else:
        raise ValueError("Unsupported period")


def make_period_key(commit: Commit, period: PeriodType) -> str:
    dt = datetime.strptime(commit.date, "%Y-%m-%d")
    return format_period(dt, period)


def generate_dates(
    start: Commit, end: Commit, step: PeriodType, interval: int = 1
) -> Dict[str, Dict[str, int]]:
    dates = defaultdict(lambda: defaultdict(int))
    start_date = datetime.strptime(start.date, "%Y-%m-%d")
    end_date = datetime.strptime(end.date, "%Y-%m-%d")

    current = start_date
    while current <= end_date:
        dates[format_period(current, step)] = defaultdict(int)
        if step == PeriodType.DAY:
            current += timedelta(days=interval)
        elif step == PeriodType.WEEK:
            current += timedelta(weeks=interval)
        elif step == PeriodType.MONTH:
            current += relativedelta(months=interval)
        else:
            raise ValueError("step must be 'days', 'weeks', or 'months'")

    return dates


def aggregate_by_period(commits: Commits, period: PeriodType) -> Dict[str, int]:
    """
    Aggregate commit dates by 'daily', 'weekly' or 'monthly'

    :param commits:
    :param period:
    :return:
    """
    counts: Dict[str, int] = defaultdict(int)
    for commit in commits:
        key = make_period_key(commit, period)
        counts[key] += 1
    return dict(sorted(counts.items()))


def export_data(commits: Commits, fmt: str, output_file: Path) -> None:
    """
    Export commit data as json/csv file

    :param commits:
    :param fmt:
    :param output_file:
    :return:
    """
    if not output_file.lower().endswith(f".{fmt}"):
        output_file += f".{fmt}"
    if fmt == "json":
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(commits, f, default=lambda o: o.__dict__, indent=2)
    elif fmt == "csv":
        if not commits:
            return
        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f, fieldnames=["repo_name", "hash", "author", "date", "subject"]
            )
            writer.writeheader()
            for commit in commits:
                writer.writerow(asdict(commit))
    else:
        raise ValueError("Unsupported export file format")
    # print(f"Exported {len(commits)} to {output_file} ({fmt.upper()})")


def plot_commits(commits: Commits, period: PeriodType, output_file: Path) -> None:
    if not commits:
        # print("No commits to plot")
        return

    # aggregate: {period_label: {repo: count}}
    data = generate_dates(commits[0], commits[-1], period)
    repos = set()

    for commit in commits:
        key = make_period_key(commit, period)
        data[key][commit.repo_name] += 1
        repos.add(commit.repo_name)

    # sort periods chronologically
    periods = sorted(data.keys())
    repos = sorted(repos)

    # prepare stacked data
    bottom = [0] * len(periods)
    fig, ax = plt.subplots(figsize=(12, 6))

    for repo in repos:
        heights = [data[period].get(repo, 0) for period in periods]
        rects = ax.bar(periods, heights, bottom=bottom, label=repo)
        ax.bar_label(rects, fmt=lambda x: int(x) if x > 0 else "", label_type="center")
        bottom = [b + h for b, h in zip(bottom, heights)]

    ax.set_title(
        f"Commits per Repository ({period.name.capitalize()}) by "
        f"<{commits[0].author}>"
    )
    ax.set_xlabel("Period")
    ax.set_ylabel("Number of Commits")
    ax.legend(title="Repository", bbox_to_anchor=(1.05, 1), loc="upper left")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(output_file)
    # print(f"Plot saved to {output_file}")


def plot_summary(commits: Commits, output_file: str) -> None:
    if not commits:
        return

    data = defaultdict(int)
    for commit in commits:
        data[commit.repo_name] += 1

    data = dict(sorted(data.items(), key=lambda item: item[1]))

    values = list(data.values())
    labels = list(data.keys())

    def absolute_value(val):
        total = sum(values)
        value = int(round(val * total / 100))
        return f"{value}"

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.set_title(
        f"Commits per Repository (from "
        f"{make_period_key(commits[0], PeriodType.DAY)} to {
        make_period_key(commits[-1], PeriodType.DAY)
        }) by <{commits[0].author}>"
    )
    ax.pie(values, labels=labels, autopct=absolute_value)
    plt.axis("equal")
    plt.savefig(output_file)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Search Git repos for commit stats by author and date range"
    )
    parser.add_argument("path", nargs="?", default=".")
    parser.add_argument("--author", required=True)
    parser.add_argument("--since", required=True)
    parser.add_argument("--until", required=True)
    parser.add_argument("--exclude", nargs="*", default=[])
    parser.add_argument("--daily", action="store_true")
    parser.add_argument("--weekly", action="store_true")
    parser.add_argument("--monthly", action="store_true")
    parser.add_argument("--export", choices=["csv", "json"])
    parser.add_argument("--export-output")
    parser.add_argument("--plot", choices=["stats", "summary"])
    parser.add_argument("--plot-output")
    args = parser.parse_args()

    base_path: Path = Path(args.path)
    exclude_patterns = [re.compile(p) for p in args.exclude]
    repos = find_git_repos(base_path=base_path, exclude_patterns=exclude_patterns)
    if not repos:
        logging.error("No git repositories found")
        return EXIT_FAILURE

    total = 0
    commits: Commits = []

    logging.info(f"Scanning {len(repos)} repositories...\n")
    for repo in repos:
        commits_in_repo = get_commit_stats(
            repo_path=repo,
            author_filter=args.author,
            since=args.since,
            until=args.until,
        )
        if commits_in_repo:
            count = len(commits_in_repo)
            total += count
            commits.extend(commits_in_repo)
            print(f"{repo} -> {count} commits")

    print("\n=== Summary ===")
    print(f"Author: {args.author}")
    print(f"Period: {args.since} to {args.until}")
    print(f"Total commits: {total}")

    if args.daily:
        print("\nCommits by day:")
        for day, count in aggregate_by_period(commits, period=PeriodType.DAY).items():
            print(f"{day}: {count}")

    if args.weekly:
        print("\nCommits by week:")
        for week, count in aggregate_by_period(commits, period=PeriodType.WEEK).items():
            print(f"{week}: {count}")

    if args.monthly:
        print("\nCommits by month:")
        for month, count in aggregate_by_period(commits, PeriodType.MONTH).items():
            print(f"{month}: {count}")

    if args.export and args.export_output:
        export_data(commits, fmt=args.export, output_file=args.export_output)

    p = (
        PeriodType.DAY
        if args.daily
        else PeriodType.WEEK if args.weekly else PeriodType.MONTH
    )
    if args.plot_output:
        commits.sort(key=lambda c: datetime.strptime(c.date, "%Y-%m-%d"))
        if args.plot == "stats":
            plot_commits(commits, period=p, output_file=args.plot_output)
        elif args.plot == "summary":
            plot_summary(commits, output_file=args.plot_output)

    return EXIT_SUCCESS


if __name__ == "__main__":
    ret: int = main()
    sys.exit(ret)
