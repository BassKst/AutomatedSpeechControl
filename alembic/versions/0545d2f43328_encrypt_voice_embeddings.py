"""encrypt voice embeddings

Revision ID: 0545d2f43328
Revises: bfe8dab76875
Create Date: 2026-02-25 03:35:28.518781

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from common.encryption_service import encrypt_list

# revision identifiers, used by Alembic.
revision: str = '0545d2f43328'
down_revision: Union[str, Sequence[str], None] = 'bfe8dab76875'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    conn = op.get_bind()

    # 1. добавляем временную колонку
    op.add_column("users", sa.Column("voice_embedding_enc", sa.Text(), nullable=True))

    # 2. забираем старые данные
    result = conn.execute(sa.text("SELECT id, voice_embedding FROM users"))

    for user_id, embedding in result:
        if embedding:
            # embedding сейчас dict или list — зависит как хранил
            encrypted = encrypt_list(embedding)
            conn.execute(
                sa.text(
                    "UPDATE users SET voice_embedding_enc = :enc WHERE id = :id"
                ),
                {"enc": encrypted, "id": user_id},
            )

    # 3. удаляем старую колонку
    op.drop_column("users", "voice_embedding")

    # 4. переименовываем новую
    op.alter_column(
        "users",
        "voice_embedding_enc",
        new_column_name="voice_embedding",
    )


def downgrade():
    raise RuntimeError("Rollback not supported for encrypted embeddings")
