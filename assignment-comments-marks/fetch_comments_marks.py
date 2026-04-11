"""
Fetch student assignment comments and marks from Canvas for a given course and assignment.
Excludes student submission content — only retrieves grades and submission comments.

Usage:
    python fetch_comments_marks.py --course-id COURSE_ID --assignment-id ASSIGNMENT_ID

Output:
    CSV file: comments_marks_<course_id>_<assignment_id>.csv
"""

import argparse
import csv
import os
import sys
import requests


def get_env(key: str) -> str:
    value = os.environ.get(key)
    if not value:
        print(f"Error: environment variable {key} is not set.", file=sys.stderr)
        sys.exit(1)
    return value


def fetch_submissions(base_url: str, headers: dict, course_id: str, assignment_id: str) -> list[dict]:
    """
    Fetch all submissions for a given course and assignment.
    Uses the 'submission_comments' include to retrieve comments.
    Excludes submission body/attachments from the returned data.
    """
    url = f"{base_url}/api/v1/courses/{course_id}/assignments/{assignment_id}/submissions"
    params = {
        "include[]": ["submission_comments", "user"],
        "per_page": 100,
    }

    submissions = []
    while url:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        submissions.extend(response.json())

        # Canvas uses Link headers for pagination
        url = None
        params = {}
        link_header = response.headers.get("Link", "")
        for part in link_header.split(","):
            if 'rel="next"' in part:
                url = part.split(";")[0].strip().strip("<>")
                break

    return submissions


def extract_rows(submissions: list[dict], id_type: str) -> list[dict]:
    """
    Extract only grade and comment data from submissions.
    Returns one row per comment, or one row per student if no comments exist.

    id_type controls the student ID column(s):
      'sis'    — sis_user_id (falls back to Canvas user ID if absent)
      'canvas' — Canvas internal user ID
      'both'   — both sis_user_id and canvas_user_id as separate columns
    """
    rows = []
    for sub in submissions:
        canvas_user_id = sub.get("user_id")
        sis_user_id = sub.get("user", {}).get("sis_user_id")

        if id_type == "canvas":
            id_fields = {"student_id": canvas_user_id}
        elif id_type == "both":
            id_fields = {
                "student_sis_id": sis_user_id,
                "student_canvas_id": canvas_user_id,
            }
        else:  # "sis" (default)
            id_fields = {"student_id": sis_user_id or canvas_user_id}

        base = {
            **id_fields,
            "score": sub.get("score"),
            "grade": sub.get("grade"),
            "graded_at": sub.get("graded_at"),
            "grader_id": sub.get("grader_id"),
        }

        comments = sub.get("submission_comments", [])
        if comments:
            for comment in comments:
                rows.append({
                    **base,
                    "comment_id": comment.get("id"),
                    "comment_author_id": comment.get("author_id"),
                    "comment_author_name": comment.get("author_name"),
                    "comment_created_at": comment.get("created_at"),
                    "comment_body": comment.get("comment"),
                })
        else:
            rows.append({
                **base,
                "comment_id": None,
                "comment_author_id": None,
                "comment_author_name": None,
                "comment_created_at": None,
                "comment_body": None,
            })

    return rows


def write_csv(rows: list[dict], output_path: str) -> None:
    if not rows:
        print("No data to write.")
        return

    fieldnames = list(rows[0].keys())
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Saved {len(rows)} rows to {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Fetch Canvas assignment comments and marks (no submission content)."
    )
    parser.add_argument("--course-id", required=True, help="Canvas course ID")
    parser.add_argument("--assignment-id", required=True, help="Canvas assignment ID")
    parser.add_argument(
        "--id-type",
        choices=["sis", "canvas", "both"],
        default="sis",
        help=(
            "Which student ID to include in the output. "
            "'sis' (default): the SIS user ID your institution imports into Canvas (e.g. a student number), "
            "falling back to the Canvas user ID if not available. "
            "'canvas': the Canvas internal user ID. "
            "'both': output both as separate columns (student_sis_id and student_canvas_id)."
        ),
    )
    parser.add_argument("--output", help="Output CSV file path (optional)")
    args = parser.parse_args()

    canvas_token = get_env("CANVAS_API_TOKEN")
    canvas_url = get_env("CANVAS_BASE_URL")  # e.g. https://canvas.sydney.edu.au

    headers = {"Authorization": f"Bearer {canvas_token}"}

    print(f"Fetching submissions for course {args.course_id}, assignment {args.assignment_id}...")
    submissions = fetch_submissions(canvas_url, headers, args.course_id, args.assignment_id)
    print(f"Retrieved {len(submissions)} submissions.")

    rows = extract_rows(submissions, args.id_type)

    output_path = args.output or f"comments_marks_{args.course_id}_{args.assignment_id}.csv"
    write_csv(rows, output_path)


if __name__ == "__main__":
    main()
