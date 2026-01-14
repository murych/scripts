from dataclasses import dataclass
from enum import Enum


class Period(Enum):
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
