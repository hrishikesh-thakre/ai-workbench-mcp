from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
from typing import Any, Callable


COMMENT_MARKER = "<!-- ai-workbench-pr-gate -->"
MARKER = COMMENT_MARKER
OPERATION = "workbench_pr_gate_comment"
JsonObject = dict[str, Any]
Runner = Callable[..., subprocess.CompletedProcess[str]]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create or update the sticky Workbench PR gate comment.")
    parser.add_argument("--repo", required=True, help="GitHub repository in owner/name form.")
    parser.add_argument("--pr-number", required=True, type=int, help="Pull request number.")
    parser.add_argument("--comment", required=True, help="Rendered PR gate comment markdown path.")
    parser.add_argument("--decision", help="Optional PR gate decision JSON path.")
    return parser


def parse_repo(repo: str) -> tuple[str, str]:
    parts = repo.split("/")
    if len(parts) != 2 or not all(part.strip() for part in parts):
        raise ValueError("repo must use owner/name form.")
    return parts[0].strip(), parts[1].strip()


def read_json_object(path: Path) -> JsonObject:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {path}.")
    return payload


def body_with_marker(comment_text: str) -> str:
    stripped = comment_text.strip()
    if COMMENT_MARKER in stripped:
        return stripped + "\n"
    return f"{COMMENT_MARKER}\n\n{stripped}\n"


def load_comment_body(comment_path: Path, decision_path: Path | None = None) -> str:
    comment_text = comment_path.read_text(encoding="utf-8")
    if decision_path is not None:
        read_json_object(decision_path)
    return body_with_marker(comment_text)


def gh_graphql(query: str, variables: JsonObject, runner: Runner = subprocess.run) -> JsonObject:
    command = ["gh", "api", "graphql", "-f", f"query={query}"]
    for key, value in variables.items():
        flag = "-F" if isinstance(value, bool | int) else "-f"
        command.extend([flag, f"{key}={value}"])
    result = runner(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "gh api graphql failed.")
    payload = json.loads(result.stdout or "{}")
    if not isinstance(payload, dict):
        raise RuntimeError("GitHub GraphQL response was not an object.")
    errors = payload.get("errors")
    if errors:
        raise RuntimeError(f"GitHub GraphQL returned errors: {errors}")
    return payload


def fetch_pr_comments(repo: str, pr_number: int, runner: Runner = subprocess.run) -> tuple[str, list[JsonObject]]:
    owner, name = parse_repo(repo)
    query = """
query($owner: String!, $name: String!, $number: Int!, $after: String) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      id
      comments(first: 100, after: $after) {
        pageInfo {
          hasNextPage
          endCursor
        }
        nodes {
          id
          body
          url
          author {
            login
          }
        }
      }
    }
  }
}
"""
    variables: JsonObject = {"owner": owner, "name": name, "number": pr_number}
    pull_request_id: str | None = None
    comments: list[JsonObject] = []

    while True:
        payload = gh_graphql(query, variables, runner=runner)
        pull_request = payload.get("data", {}).get("repository", {}).get("pullRequest")
        if not isinstance(pull_request, dict):
            raise RuntimeError(f"Pull request #{pr_number} was not found in {repo}.")
        pull_request_id = str(pull_request["id"])
        comment_connection = pull_request.get("comments", {})
        if not isinstance(comment_connection, dict):
            break
        comments.extend(comment for comment in comment_connection.get("nodes", []) if isinstance(comment, dict))
        page_info = comment_connection.get("pageInfo", {})
        if not isinstance(page_info, dict) or page_info.get("hasNextPage") is not True:
            break
        end_cursor = page_info.get("endCursor")
        if not isinstance(end_cursor, str) or not end_cursor:
            break
        variables["after"] = end_cursor

    if pull_request_id is None:
        raise RuntimeError(f"Pull request #{pr_number} was not found in {repo}.")
    return pull_request_id, comments


def find_marker_comment(comments: list[JsonObject]) -> JsonObject | None:
    for comment in comments:
        body = comment.get("body")
        if isinstance(body, str) and COMMENT_MARKER in body:
            return comment
    return None


def create_pr_comment(subject_id: str, body: str, runner: Runner = subprocess.run) -> JsonObject:
    query = """
mutation($subjectId: ID!, $body: String!) {
  addComment(input: {subjectId: $subjectId, body: $body}) {
    commentEdge {
      node {
        id
        url
      }
    }
  }
}
"""
    payload = gh_graphql(query, {"subjectId": subject_id, "body": body}, runner=runner)
    node = payload.get("data", {}).get("addComment", {}).get("commentEdge", {}).get("node", {})
    if not isinstance(node, dict) or not node.get("id"):
        raise RuntimeError("GitHub did not return the created PR comment.")
    return {"id": str(node["id"]), "url": str(node.get("url") or "")}


def update_pr_comment(comment_id: str, body: str, runner: Runner = subprocess.run) -> JsonObject:
    query = """
mutation($id: ID!, $body: String!) {
  updateIssueComment(input: {id: $id, body: $body}) {
    issueComment {
      id
      url
    }
  }
}
"""
    payload = gh_graphql(query, {"id": comment_id, "body": body}, runner=runner)
    comment = payload.get("data", {}).get("updateIssueComment", {}).get("issueComment", {})
    if not isinstance(comment, dict) or not comment.get("id"):
        raise RuntimeError("GitHub did not return the updated PR comment.")
    return {"id": str(comment["id"]), "url": str(comment.get("url") or "")}


def upsert_pr_gate_comment(
    *,
    repo: str,
    pr_number: int,
    body: str,
    runner: Runner = subprocess.run,
) -> JsonObject:
    subject_id, comments = fetch_pr_comments(repo, pr_number, runner=runner)
    existing = find_marker_comment(comments)
    if existing is not None:
        comment = update_pr_comment(str(existing["id"]), body, runner=runner)
        return {
            "operation": OPERATION,
            "action": "updated",
            "pr_number": pr_number,
            "comment_id": comment["id"],
            "comment_url": comment["url"],
        }
    comment = create_pr_comment(subject_id, body, runner=runner)
    return {
        "operation": OPERATION,
        "action": "created",
        "pr_number": pr_number,
        "comment_id": comment["id"],
        "comment_url": comment["url"],
    }


def main() -> int:
    args = build_parser().parse_args()
    decision_path = Path(args.decision) if args.decision else None
    body = load_comment_body(Path(args.comment), decision_path)
    result = upsert_pr_gate_comment(repo=args.repo, pr_number=args.pr_number, body=body)
    print(f"pr_gate_comment_action={result['action']}")
    if result.get("comment_url"):
        print(f"pr_gate_comment_url={result['comment_url']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
