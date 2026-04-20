# Copilot Instructions

## Workflow
- After any UI changes to the offline mode, regenerate the preview HTML by running:
  ```
  python -m wanderlogpro.cli offline-mode https://wanderlog.com/plan/gpaxvjfljkfalyeh/trip-to-vietnam-guangdong-and-more/shared
  ```
- Do not create git commits on the user's behalf.
- Run `python -m pytest tests/ --tb=short -q` after code changes to verify nothing breaks.

## Security
- Never commit `token.json`, `credentials.json`, or any OAuth secrets.
- The generated offline HTML files (`*-offline.html`) are checked into the repo — regenerate them after changes.

## Project Structure
- Source lives in `src/` with submodules: `calendar_export`, `map_export`, `offline_mode`.
- Package is mapped via `pyproject.toml` as `wanderlogpro.*`.
- Python 3.10+ is required — use modern type hints (e.g., `list[str]` not `List[str]`).

## Style
- Only comment code that needs clarification; avoid obvious comments.
- Keep HTML/CSS/JS embedded in `generator.py` — it's a single self-contained offline file by design.
