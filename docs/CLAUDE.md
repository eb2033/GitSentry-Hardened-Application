# docs

Detail behind the brief in `../CLAUDE.md`.

## Rules

- `PLAN.md` is the canonical design. If it disagrees with `../CLAUDE.md`, `PLAN.md` wins; then fix the brief.
- Change the plan only when asked, or when a source contradicts it. Record the change in the relevant `sources/` file under "Changes the plan", update `PLAN.md`, then add a dated line under "Decisions already made" in `../CLAUDE.md`.
- Do not add components the plan has cut (Prometheus, Grafana, frontend, deployed baseline, nightly destroy).
- Update the "last updated" date in any file you edit.
- Dissertation-bound text: British English, neutral academic register, no contractions.

## Subfolders

Each has its own `CLAUDE.md` and `README.md`: `checklists/`, `prompts/`, `sources/`.
