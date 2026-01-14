from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable

import matplotlib.pyplot as plt
from dateutil.relativedelta import relativedelta

from data import Commit, Commits, Period

type CommitsPerRepo = dict[str, int]
type CommitsPerRepoPerPeriod = dict[str, CommitsPerRepo]


def format_period(date: datetime, period: Period) -> str:
    if not date:
        raise ValueError("No date provided")

    if period is Period.DAY:
        return date.strftime("%Y-%m-%d")
    elif period is Period.WEEK:
        return f"{date.isocalendar().year}-W{date.isocalendar().week:02d}"
    elif period is Period.MONTH:
        return date.strftime("%Y-%m")
    else:
        raise ValueError("Unsupported period")


def make_period_key(commit: Commit, period: Period) -> str:
    return format_period(datetime.strptime(commit.date, "%Y-%m-%d"), period)


def generate_dates(
    start: Commit, end: Commit, step: Period, interval: int = 1
) -> CommitsPerRepoPerPeriod:
    """
    aggregate: {period_label: {repo: count}}

    creates sorted dictionary of dates -> commits_per_repo in range from start
    to end
    """
    dates: CommitsPerRepoPerPeriod = defaultdict(lambda: defaultdict(int))

    start_date: datetime = datetime.strptime(start.date, "%Y-%m-%d")
    end_date: datetime = datetime.strptime(end.date, "%Y-%m-%d")

    current = start_date
    while current <= end_date:
        period_tag: str = format_period(current, step)
        dates[period_tag] = defaultdict(int)
        if step == Period.DAY:
            current += timedelta(days=interval)
        elif step == Period.WEEK:
            current += timedelta(weeks=interval)
        elif step == Period.MONTH:
            current += relativedelta(months=interval)
        else:
            raise ValueError("step must be 'days', 'weeks', or 'months'")

    return dates


def plot_commits(commits: Commits, output_file: Path, period: Period) -> None:
    if not commits:
        raise ValueError("No commits provided")

    # aggregate: {period_label: {repo: count}}
    data: CommitsPerRepoPerPeriod = generate_dates(commits[0], commits[-1], period)
    repos: set[str] = set()

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


def plot_summary(commits: Commits, output_file: Path, period: Period = None) -> None:
    if not commits:
        raise ValueError("No commits provided")

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
        f"Commits per Repository (from {make_period_key(commits[0], Period.DAY)} to {make_period_key(commits[-1], Period.DAY)}) by <{commits[0].author}>"
    )
    ax.pie(values, labels=labels, autopct=absolute_value)
    plt.axis("equal")
    plt.savefig(output_file)


type PlotFn = Callable[[Commits, Path, Period], None]
plotters: dict[str, PlotFn] = {"stats": plot_commits, "summary": plot_summary}
