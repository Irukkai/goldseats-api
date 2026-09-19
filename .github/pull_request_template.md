## What and why

<!-- One paragraph: what changes, and what problem it solves. Link the issue. -->

Closes #

## Milestone

<!-- M0 … M9. If this belongs to no milestone, say why. -->

## How to verify

<!-- Exact commands or steps a reviewer can run. -->

```bash
pytest
uvicorn app.main:app --reload
```

## Checklist

- [ ] Title follows Conventional Commits (`feat(films): …`, `fix(db): …`, `chore: …`)
- [ ] `ruff check . && ruff format --check .` passes
- [ ] `mypy app` passes
- [ ] `pytest` passes, and new behaviour has tests
- [ ] Migration included and reversible, if the schema changed
- [ ] `.env.example` updated, if config changed
- [ ] No secrets, credentials, or personal data in the diff
- [ ] Docs updated in `goldseats-docs`, if a convention or contract changed
