# Project instructions

- No commits, staging, repository initialization or other Git operations.
- Keep application runtime fully offline.
- Document implementation plans and continuation notes.
- Validation policy (user decision, 2026-10-06): integration tests only. Do not add or run unit tests or broad test discovery. Verify complete application workflows through actual production components; capture substitutes are allowed only at the hardware boundary. Keep historical tests unless explicitly asked to remove them.
- Preserve existing UTF-8 BOM state and line endings when editing text files.
- Integration checks must retain the previous behavioral and failure-case coverage; maintain a coverage mapping and report any gaps explicitly. Test count alone does not demonstrate equivalent coverage.
