# AGENTS.md

## Dev environment tips
- Install dependencies with `npm install` before running scaffolds.
- Use `npm run dev` for the interactive TypeScript session that powers local experimentation.
- Run `npm run build` to refresh the CommonJS bundle in `dist/` before shipping changes.
- Store generated artefacts in `.context/` so reruns stay deterministic.

## Testing instructions
- Execute `npm run test` to run the Jest suite.
- Append `-- --watch` while iterating on a failing spec.
- Trigger `npm run build && npm run test` before opening a PR to mimic CI.
- Add or update tests alongside any generator or CLI changes.

## PR instructions
- Follow Conventional Commits (for example, `feat(scaffolding): add doc links`).
- Cross-link new scaffolds in `docs/README.md` and `agents/README.md` so future agents can find them.
- Attach sample CLI output or generated markdown when behaviour shifts.
- Confirm the built artefacts in `dist/` match the new source changes.

## Repository map
- `__pycache__/` — Python bytecode cache generated at runtime; do not edit manually.
- `config_exemplo.env/` — Template of required environment variables; update when new settings are introduced.
- `config.env/` — Local environment configuration with real credentials; edit locally only, never commit secrets.
- `src/api/athena/client.py` — AWS Athena extraction for SAP NF-e keys; edit when SAP query logic changes.
- `cron_job.sh/` — Cron entry helper for container or VPS scheduling; edit when schedule or entrypoint changes.
- `dados/` — Local data artifacts (CSV exports, caches); agents may inspect or add samples but avoid committing large outputs.
- `src/database/manager.py` — PostgreSQL access layer with inserts/queries; edit when schema or persistence logic changes.
- `src/database/schema.py` — DDL definitions for all tables; edit when adding or modifying database tables.

## AI Context References
- Documentation index: `.context/docs/README.md`
- Agent playbooks: `.context/agents/README.md`
- Contributor guide: `CONTRIBUTING.md`
