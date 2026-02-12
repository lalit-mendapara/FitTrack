---
description: How to create and apply database migrations with Alembic
---

## Creating a New Migration

After modifying an SQLAlchemy model (e.g., adding a column), generate a migration:

// turbo
1. Run inside Docker:
```bash
docker exec diet_planner_backend /home/appuser/.local/bin/alembic revision --autogenerate -m "describe_your_change"
```

2. Review the generated file in `backend/alembic/versions/` — verify the `upgrade()` and `downgrade()` look correct.

3. Restart the backend (migrations auto-apply on startup):
```bash
docker restart diet_planner_backend
```

## Useful Commands

// turbo
- Check current revision:
```bash
docker exec diet_planner_backend /home/appuser/.local/bin/alembic current
```

// turbo
- View migration history:
```bash
docker exec diet_planner_backend /home/appuser/.local/bin/alembic history
```

- Downgrade one step:
```bash
docker exec diet_planner_backend /home/appuser/.local/bin/alembic downgrade -1
```

## Notes

- Migrations auto-run on backend startup via `main.py`
- If Alembic fails, it falls back to `Base.metadata.create_all()`
- Legacy Django tables (auth_*, django_*) are excluded from autogenerate
- All model classes must be imported in `app/models/__init__.py` for autogenerate to detect them
