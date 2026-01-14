#!/usr/bin/env python3

import argparse
import logging
import os
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Pattern, Iterator

from data import Commit, Commits, Period
from exporters import exporters
from plotters import plotters, format_period

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)

EXIT_SUCCESS = 0
EXIT_FAILURE = 1


def iter_git_repos(
    base_path: Path, exclude_patterns: list[Pattern[str]]
) -> Iterator[Path]:
    for root, dirs, files in os.walk(base_path):
        current_path: Path = Path(root)

        # skip directory entirely if it matches an exclude pattern
        if any(p.search(str(current_path)) for p in exclude_patterns):
            dirs[:] = []
            continue

        # if `.git` exists here, yield the repo root
        if ".git" in dirs:
            yield current_path
            dirs.remove(".git")


def get_commit_stats(repo_path: Path, author: str, since: str, until: str) -> Commits:
    """
    Get a list of commit dates (YYYY-MM-DD) for commits matching the author

    :param repo_path: path to the git repository
    :param author: author email or username
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
        f"--author={author}",
        "--pretty=format:%H|%ae|%ad|%s",
        "--date=short",
    ]
    result = subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    if result.returncode != EXIT_SUCCESS:
        raise RuntimeError(f"git query failed with ret code {result.returncode}")

    repo_name: str = repo_path.name
    commits: Commits = []

    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        commit_hash, author_email, commit_date, commit_subj = line.split("|", 3)
        commits.append(
            Commit(repo_name, commit_hash[:7], author_email, commit_date, commit_subj)
        )
    return commits


def aggregate_by_period(commits: Commits, period: Period) -> dict[str, int]:
    """
    Aggregate commit dates by 'daily', 'weekly' or 'monthly'

    :param commits:
    :param period:
    :return:
    """
    counts: dict[str, int] = defaultdict(int)
    for commit in commits:
        key = format_period(datetime.strptime(commit.date, "%Y-%m-%d"), period)
        counts[key] += 1
    return dict(sorted(counts.items()))


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
    parser.add_argument("--export-output", default="export")
    parser.add_argument("--plot", choices=["stats", "summary"])
    parser.add_argument("--plot-output")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    base_path: Path = Path(args.path)
    exclude_patterns: list[Pattern[str]] = [re.compile(p) for p in args.exclude]

    total = 0
    commits: Commits = []

    for repo in iter_git_repos(base_path=base_path, exclude_patterns=exclude_patterns):
        commits_in_repo = get_commit_stats(
            repo_path=repo,
            author=args.author,
            since=args.since,
            until=args.until,
        )
        if commits_in_repo:
            count = len(commits_in_repo)
            total += count
            commits.extend(commits_in_repo)
            logging.debug(f"{repo} -> {count} commits")

    print("\n=== Summary ===")
    print(f"Author: {args.author}")
    print(f"Period: {args.since} to {args.until}")
    print(f"Total commits: {total}")

    if args.daily:
        print("\nCommits by day:")
        for day, count in aggregate_by_period(commits, period=Period.DAY).items():
            print(f"{day}: {count}")

    if args.weekly:
        print("\nCommits by week:")
        for week, count in aggregate_by_period(commits, period=Period.WEEK).items():
            print(f"{week}: {count}")

    if args.monthly:
        print("\nCommits by month:")
        for month, count in aggregate_by_period(commits, period=Period.MONTH).items():
            print(f"{month}: {count}")

    print()

    if args.export:
        output_format: str = args.export
        exporter = exporters.get(output_format)
        if exporter is None:
            logging.error(f"Exporting to format {output_format} is not supported")
        else:
            output_file: Path = Path(args.export_output)
            if output_file.suffix == "":
                output_file = output_file.with_suffix(f".{output_format}")
            logging.debug(f"Exporting {output_file.name}")
            exporter(commits, output_file)

    if args.plot:
        plotter = plotters.get(args.plot)
        if plotter is None:
            logging.error(f"Plot type {args.plot} is not supported")
        else:
            commits.sort(key=lambda c: datetime.strptime(c.date, "%Y-%m-%d"))
            plot_file: Path = Path(
                args.plot_output if args.plot_output else (f"plot.png")
            )
            if args.daily:
                logging.debug(f"Exporting {plot_file}")
                plotter(
                    commits, plot_file.with_stem(plot_file.stem + "_daily"), Period.DAY
                )
            if args.weekly:
                logging.debug(f"Exporting {plot_file}")
                plotter(
                    commits,
                    plot_file.with_stem(plot_file.stem + "_weekly"),
                    Period.WEEK,
                )
            if args.monthly:
                logging.debug(f"Exporting {plot_file}")
                plotter(
                    commits,
                    plot_file.with_stem(plot_file.stem + "_monthly"),
                    Period.MONTH,
                )

    return EXIT_SUCCESS


if __name__ == "__main__":
    ret: int = main()
    sys.exit(ret)
