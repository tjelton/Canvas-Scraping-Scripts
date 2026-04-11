# Assignment Comments and Marks

Fetches all student grades and submission comments for a given Canvas course and assignment. Does **not** retrieve student submission content (essay text, file uploads, etc.).

## Output

By default, the output has **one row per submission comment** (or one row per student if they have no comments):

| Column | Description |
|---|---|
| `student_id` | Student identifier — see [Student ID](#student-id) below |
| `score` | Numeric score awarded |
| `grade` | Letter/display grade |
| `graded_at` | ISO timestamp of when the grade was set |
| `grader_id` | Canvas user ID of the grader |
| `comment_id` | Unique ID of the comment |
| `comment_author_id` | Canvas user ID of the comment author |
| `comment_author_name` | Display name of the comment author |
| `comment_created_at` | ISO timestamp of when the comment was posted |
| `comment_body` | Text content of the comment |

With `--collapse-comments`, the output instead has **one row per student** with a single combined `comments` field — see [Collapsing Comments](#collapsing-comments).

## Setup

### 1. Install dependencies

```bash
pip install requests
```

### 2. Set environment variables

| Variable | Description | Example |
|---|---|---|
| `CANVAS_API_TOKEN` | Your Canvas API access token | `1234~abcdef...` |
| `CANVAS_BASE_URL` | Base URL of your Canvas instance | `https://your-institution.instructure.com` |

To generate an API token: Canvas > Account > Settings > New Access Token.

```bash
export CANVAS_API_TOKEN="your_token_here"
export CANVAS_BASE_URL="https://your-institution.instructure.com"
```

### 3. Find your IDs

- **Course ID**: visible in the Canvas course URL — `your-institution.instructure.com/courses/COURSE_ID`
- **Assignment ID**: visible in the assignment URL — `.../assignments/ASSIGNMENT_ID`

## Usage

```bash
python fetch_comments_marks.py --course-id 12345 --assignment-id 67890
```

This saves output to `comments_marks_12345_67890.csv` in the current directory.

### Custom output path

```bash
python fetch_comments_marks.py --course-id 12345 --assignment-id 67890 --output my_data.csv
```

## Collapsing Comments

Some markers leave feedback in the rubric criterion boxes rather than (or in addition to) the overall submission comment box. Use `--collapse-comments` to combine both sources into a single formatted `comments` field, with one row per student.

```bash
python fetch_comments_marks.py --course-id 12345 --assignment-id 67890 --collapse-comments
```

The `comments` field is formatted as:

```
<Criterion Name (Markers Comment)>:
<comment text>

<Final Comment>:
<comment text>
```

Rules:
- Rubric criteria with no comment are omitted.
- `Final Comment` is omitted if the marker left no overall submission comment.
- If the assignment has no rubric, only `Final Comment` appears (if present).
- If there are multiple submission comments, they are joined in chronological order.

**Example** — assignment with rubric criteria "Working" and "Presentation", where only "Presentation" has a comment:

```
<Presentation (Markers Comment)>:
The slides were clear and well-structured.

<Final Comment>:
Good effort overall. See rubric for specific feedback.
```

## Student ID

Canvas stores two different student identifiers. Use `--id-type` to control which appears in the output.

| Value | Column(s) | Description |
|---|---|---|
| `sis` (default) | `student_id` | The SIS user ID — an identifier imported from your institution's Student Information System (e.g. a student number). Falls back to the Canvas user ID if not set. |
| `canvas` | `student_id` | The Canvas internal user ID. Consistent across all Canvas instances but not meaningful outside Canvas. |
| `both` | `student_sis_id`, `student_canvas_id` | Both IDs as separate columns. Useful for cross-referencing. |

**What is `sis_user_id`?** Canvas is used by many institutions, each of which can import their own student identifiers from an external Student Information System (SIS). The `sis_user_id` is whatever your institution has configured — commonly a student number, staff ID, or email prefix. It is a standard Canvas field, not institution-specific. If your institution hasn't configured SIS integration, this field will be empty and the script falls back to the Canvas user ID.

### Examples

```bash
# Default: use SIS user ID (falls back to Canvas ID if not set)
python fetch_comments_marks.py --course-id 12345 --assignment-id 67890

# Use Canvas internal user ID
python fetch_comments_marks.py --course-id 12345 --assignment-id 67890 --id-type canvas

# Output both IDs as separate columns
python fetch_comments_marks.py --course-id 12345 --assignment-id 67890 --id-type both
```

## Notes

- Results are paginated automatically — all pages are fetched regardless of class size.
- Students with no comments will still appear in the output.
- Only submission-level comments are included (not draft/provisional comments).
- You must have at least a Teacher or TA role in the course to access grade, rubric, and comment data.
