from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import pii_cipher
from app.models.call_log import CallLog
from app.schemas.vapi import EndOfCallRequest, EndOfCallResponse


def save_end_of_call(db: Session, payload: EndOfCallRequest) -> EndOfCallResponse:
    call_log = db.scalar(select(CallLog).where(CallLog.vapi_call_id == payload.vapi_call_id))
    if call_log is None:
        call_log = CallLog(
            vapi_call_id=payload.vapi_call_id,
            channel=payload.channel,
            status=payload.status,
        )
        db.add(call_log)

    call_log.channel = payload.channel
    call_log.status = payload.status
    call_log.summary_encrypted = pii_cipher.encrypt(payload.summary)
    call_log.transcript_encrypted = pii_cipher.encrypt(payload.transcript)
    call_log.started_at = payload.started_at
    call_log.ended_at = payload.ended_at

    db.commit()
    return EndOfCallResponse(status="saved", message="Call log saved.")

