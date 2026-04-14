# Canvas Scraping Scripts

A collection of scripts for extracting data from the Canvas LMS via the Canvas REST API.

## Setup

All scripts share the same environment variable requirements:

| Variable | Description | Example |
|---|---|---|
| `CANVAS_API_TOKEN` | Your Canvas API access token | `1234~abcdef...` |
| `CANVAS_BASE_URL` | Base URL of your Canvas instance | `https://your-institution.instructure.com` |

To generate an API token: Canvas > Account > Settings > New Access Token.

```bash
export CANVAS_API_TOKEN="your_token_here"
export CANVAS_BASE_URL="https://your-institution.instructure.com"
```

## Scripts

| Script | Description |
|---|---|
| [Assignment Comments and Marks](assignment-comments-marks/README.md) | Fetch student grades and submission comments for a given course and assignment (no submission content) |

## Notes

- For people at the University of Sydney: export CANVAS_BASE_URL="https://canvas.sydney.edu.au"
