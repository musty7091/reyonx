from database import db
from models import AuditLog
from datetime import datetime


def log_action(action, table_name, record_id=None, description=None):
    try:
        log = AuditLog(
            action=action,
            table_name=table_name,
            record_id=record_id,
            description=description,
            timestamp=datetime.utcnow()
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print("LOG HATASI:", e)