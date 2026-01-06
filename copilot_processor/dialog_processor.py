import argparse
import csv
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple

ENCODING = "utf-8"
DELIMITER = ","

COL_CONV_ID = "\ufeffConversation"
COL_ROLE = "Author"
COL_TEXT = "Message"
COL_TIME = "Time"
ORDER = ['Human', 'Ai']


def increase_md_headings(text: str, increment: int = 1) -> str:
    def repl(match):
        hashes = match.group(1)
        return "#" * (len(hashes) + increment) + " "

    return re.sub(r"^(#{1,6})\s", repl, text, flags=re.MULTILINE)


def read_input_file(file: str) -> Dict[str, List]:
    dialogs = defaultdict(list)
    with open(file, encoding=ENCODING, newline="") as f:
        reader = csv.DictReader(f, delimiter=DELIMITER)
        for row in reader:
            conv_id = row[COL_CONV_ID]
            time = datetime.strptime(row[COL_TIME].strip(), "%Y-%m-%dT%H:%M:%S")
            role = row[COL_ROLE].strip().capitalize()
            text = row[COL_TEXT].strip()
            dialogs[conv_id].append((time, role, text))
    return dialogs


def sort_dialogs_by_earliest_date(
    input: Dict[str, List[Tuple[datetime, str, str]]],
) -> Dict[str, List[Tuple[datetime, str, str]]]:
    sortable_items = []
    for key, value_list in input.items():
        if value_list:
            min_dt = min(value_list, key=lambda x: x[0])[0]
        else:
            min_dt = datetime.max
        sortable_items.append((min_dt, key, value_list))

    sortable_items.sort(key=lambda item: item[0])

    sorted_dict = {key: value for _, key, value in sortable_items}
    return sorted_dict


def process_dialog(idx: int, conv_id: str, messages: List[Tuple]) -> str:
    md_lines = [f"# Диалог {idx}: {conv_id}", ""]
    messages.sort(key=lambda x: (x[0], ORDER.index(x[1])))
    for time, role, text in messages:
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        text = increase_md_headings(text, increment=1)
        if role.lower() == "human":
            md_lines.append(f"**Пользователь** ({ts})")
        else:
            md_lines.append(f"**Copilot** ({ts})")

        for line in text.splitlines():
            md_lines.append(f"> {line}")

        md_lines.append("")
    return "\n".join(md_lines)


def write_dialog(idx: int, conv_id: str, md_content: str, path: Path) -> bool:
    return (path / f"{idx:03d}_{conv_id}.md").write_text(
        md_content, encoding=ENCODING
    ) > 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="converts copilot export csv to bunch of markdown files split by dialog"
    )
    parser.add_argument("input")
    parser.add_argument("--output", required=True, default="out")

    args = parser.parse_args()

    if not args.input or not args.output:
        return 1

    input_file = args.input
    dialogs = read_input_file(input_file)
    if not dialogs:
        print("no dialogs found")
        return 1

    output_dir = Path(args.output)
    output_dir.mkdir(exist_ok=True)

    dialogs_sorted = sort_dialogs_by_earliest_date(dialogs)
    for idx, (conv_id, messages) in enumerate(dialogs_sorted.items(), start=1):
        print(f"Processing {idx}: {conv_id}")
        md_content = process_dialog(idx, conv_id, messages)
        ok = write_dialog(idx, conv_id, md_content, output_dir)
        if not ok:
            print(f"\tDialog {idx} was not written successfully")

    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
