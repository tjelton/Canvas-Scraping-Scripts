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


def fetch_assignment(base_url: str, headers: dict, course_id: str, assignment_id: str) -> dict:
    """Fetch assignment details, including rubric criteria if present."""
    url = f"{base_url}/api/v1/courses/{course_id}/assignments/{assignment_id}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def build_rubric_map(assignment: dict) -> dict[str, str]:
    """
    Return a mapping of rubric criterion ID -> criterion description name.
    Returns an empty dict if the assignment has no rubric.
    """
    rubric = assignment.get("rubric", [])
    return {criterion["id"]: criterion["description"] for criterion in rubric}


def fetch_submissions(base_url: str, headers: dict, course_id: str, assignment_id: str) -> list[dict]:
    """
    Fetch all submissions for a given course and assignment.
    Includes submission comments, rubric assessments, and user info.
    """
    url = f"{base_url}/api/v1/courses/{course_id}/assignments/{assignment_id}/submissions"
    params = {
        "include[]": ["submission_comments", "rubric_assessment", "user"],
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


def build_id_fields(sub: dict, id_type: str) -> dict:
    canvas_user_id = sub.get("user_id")
    sis_user_id = sub.get("user", {}).get("sis_user_id")

    if id_type == "canvas":
        return {"student_id": canvas_user_id}
    elif id_type == "both":
        return {
            "student_sis_id": sis_user_id,
            "student_canvas_id": canvas_user_id,
        }
    else:  # "sis" (default)
        return {"student_id": sis_user_id or canvas_user_id}


def build_combined_comment(submission: dict, rubric_map: dict[str, str]) -> str:
    """
    Build a single formatted comment string combining:
      - Any rubric criterion comments (labelled by criterion name)
      - The overall submission comment(s) under "Final Comment"

    Format:
        Criterion Name (Markers Comment):
        <comment text>

        Final Comment:
        <comment text>

    Rubric criteria with no comment are omitted.
    "Final Comment" is omitted if there are no submission comments.
    """
    parts = []

    # Rubric criterion comments
    rubric_assessment = submission.get("rubric_assessment", {})
    for criterion_id, rating in rubric_assessment.items():
        comment = (rating.get("comments") or "").strip()
        if comment:
            name = rubric_map.get(criterion_id, criterion_id)
            parts.append(f"<{name} (Markers Comment)>:\n{comment}")

    # Overall submission comments (concatenate if multiple)
    submission_comments = submission.get("submission_comments", [])
    final_text = "\n\n".join(
        (c.get("comment") or "").strip()
        for c in submission_comments
        if (c.get("comment") or "").strip()
    )
    if final_text:
        parts.append(f"<Final Comment>:\n{final_text}")

    return "\n\n".join(parts)


def extract_rows_collapsed(submissions: list[dict], rubric_map: dict[str, str], id_type: str) -> list[dict]:
    """
    One row per student. Rubric criterion comments and submission comments
    are combined into a single formatted 'comments' field.
    """
    rows = []
    for sub in submissions:
        rows.append({
            **build_id_fields(sub, id_type),
            "score": sub.get("score"),
            "grade": sub.get("grade"),
            "graded_at": sub.get("graded_at"),
            "grader_id": sub.get("grader_id"),
            "comments": build_combined_comment(sub, rubric_map),
        })
    return rows


def extract_rows(submissions: list[dict], id_type: str) -> list[dict]:
    """
    One row per submission comment, or one row per student if no comments exist.
    Does not include rubric comments.
    """
    rows = []
    for sub in submissions:
        base = {
            **build_id_fields(sub, id_type),
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
    parser.add_argument(
        "--collapse-comments",
        action="store_true",
        help=(
            "Combine rubric criterion comments and the overall submission comment into a single "
            "formatted 'comments' field, with one row per student. "
            "Without this flag, output has one row per submission comment (rubric comments excluded)."
        ),
    )
    parser.add_argument("--output", help="Output CSV file path (optional)")
    args = parser.parse_args()

    canvas_token = get_env("CANVAS_API_TOKEN")
    canvas_url = get_env("CANVAS_BASE_URL")  # e.g. https://canvas.sydney.edu.au

    headers = {"Authorization": f"Bearer {canvas_token}"}

    if args.collapse_comments:
        print(f"Fetching assignment {args.assignment_id} in course {args.course_id}...")
        assignment = fetch_assignment(canvas_url, headers, args.course_id, args.assignment_id)
        rubric_map = build_rubric_map(assignment)
        if rubric_map:
            print(f"Found rubric with {len(rubric_map)} criteria: {', '.join(rubric_map.values())}")
        else:
            print("No rubric found for this assignment.")

    print("Fetching submissions...")
    submissions = fetch_submissions(canvas_url, headers, args.course_id, args.assignment_id)
    print(f"Retrieved {len(submissions)} submissions.")

    if args.collapse_comments:
        rows = extract_rows_collapsed(submissions, rubric_map, args.id_type)
    else:
        rows = extract_rows(submissions, args.id_type)

    output_path = args.output or f"comments_marks_{args.course_id}_{args.assignment_id}.csv"
    write_csv(rows, output_path)


if __name__ == "__main__":
    main()
