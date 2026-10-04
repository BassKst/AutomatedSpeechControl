import logging

from sqlalchemy.orm import joinedload

from assistant_core.database.models import SessionLocal, ExecutionLog, User

logger = logging.getLogger(__name__)


def get_active_users():
    active_users = []
    with SessionLocal() as db:
        try:
            active_users = (
                db.query(User)
                .options(joinedload(User.role))
                .filter(User.is_active.in_([1, True, "true"]))
                .all()
            )
            db.expunge_all()
        except Exception as e:
            logger.error(f"БД недоступна для проверки прав: {e}")

    return active_users


def add_db_log(user_id, audio_text, entities, intent):
    with SessionLocal() as db:
        new_log = ExecutionLog(
            user_id=user_id,
            raw_voice_text=audio_text,
            extracted_entities=entities,
            intent_name=intent,
            status="PROCESSING",
            system_response="Задача принята в конвейер..."
        )
        db.add(new_log)
        db.commit()
        db.refresh(new_log)
        return new_log.id


def update_log_in_db(log_id: int, status: str, system_response: str):
    with SessionLocal() as db:
        try:
            log_entry = db.query(ExecutionLog).filter(ExecutionLog.id == log_id).first()
            if log_entry:
                log_entry.status = status
                log_entry.system_response = system_response
                db.commit()
        except Exception as e:
            logger.error(f"Ошибка обновления БД: {e}")

