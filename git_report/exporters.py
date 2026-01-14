import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Callable

from data import Commits


def export_json(commits: Commits, out: Path) -> None:
    with open(out, "w", encoding="utf-8") as f:
        json.dump(commits, f, default=lambda o: o.__dict__, indent=2)


def export_csv(commits: Commits, out: Path) -> None:
    with open(out, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["repo_name", "hash", "author", "date", "subject"]
        )
        writer.writeheader()
        for commit in commits:
            writer.writerow(asdict(commit))


type ExportFn = Callable[[Commits, Path], None]
exporters: dict[str, ExportFn] = {"json": export_json, "csv": export_csv}
