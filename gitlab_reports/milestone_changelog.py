import argparse
import re
import gitlab
from datetime import date
from collections import defaultdict
import sys

other_tags = {
    "type::feature": "прочие изменения",
    "type::refactor": "прочие изменения",
    "type::remove": "прочие изменения",
    "type::bugfix": "прочие исправления",
}

headers_tags = {
    "type::feature": "Добавлено",
    "type::refactor": "Изменено",
    "type::remove": "Изменено",
    "type::bugfix": "Исправлено",
}

release_date = date.today().strftime("%Y-%m-%d")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--token", type=str)
    parser.add_argument("--label-regex", required=True)
    parser.add_argument("--milestone-name", type=str)
    parser.add_argument("--milestone-id", type=int)

    args = parser.parse_args()

    # parse url
    try:
        parts = args.repo.split("//", 1)[-1].split("/", 1)
        host_url = parts[0]
        project_path = parts[1]
    except Exception as e:
        print(f"invalid url format, {e}")
        return 1

    gl = gitlab.Gitlab(f"https://{host_url}", private_token=args.token)

    try:
        project = gl.projects.get(project_path)
    except gitlab.GitlabGetError as e:
        print(f"error while getting project: {e}")
        return 1

    # preparing regex
    try:
        label_pattern = re.compile(args.label_regex, re.IGNORECASE)
    except re.error as e:
        print(f"regexp error: {e}")
        return 1

    # getting labels
    labels = project.labels.list(all=True)
    matched_labels = [lbl.name for lbl in labels if label_pattern.search(lbl.name)]

    if not matched_labels:
        print("did not find any labels matching request")
        return 0

    # getting milestones
    milestones = project.milestones.list(all=True)
    milestone = None
    if args.milestone_id:
        milestone = next((m for m in milestones if m.id == args.milestone_id), None)
    elif args.milestone_name:
        milestone = next(
            (m for m in milestones if m.title == args.milestone_name), None
        )
    if not milestone:
        print("did not found milestone matching request")
        sys.exit(0)

    # getting issues
    issues = project.issues.list(milestone=milestone.title, all=True)

    # grouping by label
    grouped = defaultdict(list)
    for issue in issues:
        for label in matched_labels:
            if label in issue.labels:
                grouped[label].append(issue)

    # print out
    print(f"## [{milestone.title}] - {release_date}\n")
    for label in matched_labels:
        if label in grouped:
            print(f"### {headers_tags[label]}\n")
            internal = []
            for issue in grouped[label]:
                if "scope::customer" in issue.labels:
                    print(f"- {issue.title.lower()} (#{issue.iid})")
                elif "scope::internal" in issue.labels:
                    internal.append(issue)
            if internal:
                others = ", ".join(f"#{issue.iid}" for issue in internal)
                for tag, msg in other_tags.items():
                    if tag in issue.labels:
                        print(f"- {msg} ({others})")
                        break
            print()

    return 0


if __name__ == "__main__":
    ret = main()
    sys.exit(ret)
