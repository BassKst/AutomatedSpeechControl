from .database.models import Base

# Явный ре-экспорт: `from assistant_core import Base` используется в alembic/env.py.
__all__ = ["Base"]
