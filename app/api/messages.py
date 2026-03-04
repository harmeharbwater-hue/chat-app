from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.db import get_db
from app.models.contact import Contact, ContactStatus
from app.models.message import Message
from app.models.user import User
from app.schemas.messages import MessageCreate, MessageRead
from app.services.crypto import encrypt_text, decrypt_text


router = APIRouter(prefix="/messages", tags=["messages"])


async def _ensure_can_message(
    db: AsyncSession, user_id: int, other_user_id: int
) -> None:
    stmt = select(Contact).where(
        and_(
            Contact.user_id == user_id,
            Contact.contact_user_id == other_user_id,
            Contact.status == ContactStatus.ACCEPTED,
        )
    )
    result = await db.execute(stmt)
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only message accepted contacts",
        )


@router.post("", response_model=MessageRead, status_code=status.HTTP_201_CREATED)
async def send_message(
    payload: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageRead:
    if payload.to_user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot message yourself")

    await _ensure_can_message(db, current_user.id, payload.to_user_id)

    encrypted = encrypt_text(payload.body)

    msg = Message(
        sender_id=current_user.id,
        receiver_id=payload.to_user_id,
        ciphertext=encrypted.ciphertext,
        nonce=encrypted.nonce,
        tag=encrypted.tag,
        meta=None,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)

    return MessageRead(
        id=msg.id,
        sender_id=msg.sender_id,
        receiver_id=msg.receiver_id,
        body=payload.body,
        meta=msg.meta,
        created_at=msg.created_at,
        deleted_at=msg.deleted_at,
    )


@router.get("/{other_user_id}", response_model=List[MessageRead])
async def get_conversation(
    other_user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[MessageRead]:
    await _ensure_can_message(db, current_user.id, other_user_id)

    stmt = (
        select(Message)
        .where(
            or_(
                and_(
                    Message.sender_id == current_user.id,
                    Message.receiver_id == other_user_id,
                ),
                and_(
                    Message.sender_id == other_user_id,
                    Message.receiver_id == current_user.id,
                ),
            )
        )
        .order_by(Message.created_at.asc())
    )
    result = await db.execute(stmt)
    messages = result.scalars().all()

    items: List[MessageRead] = []
    for m in messages:
        try:
            body = decrypt_text(m.ciphertext, m.nonce, m.tag)
        except Exception:
            body = "[decryption error]"
        items.append(
            MessageRead(
                id=m.id,
                sender_id=m.sender_id,
                receiver_id=m.receiver_id,
                body=body,
                meta=m.meta,
                created_at=m.created_at,
                deleted_at=m.deleted_at,
            )
        )
    return items


@router.delete("/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_message(
    message_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    stmt = select(Message).where(Message.id == message_id)
    result = await db.execute(stmt)
    msg = result.scalar_one_or_none()
    if not msg or msg.sender_id != current_user.id:
        raise HTTPException(status_code=404, detail="Message not found")

    await db.execute(
        update(Message)
        .where(Message.id == message_id)
        .values(deleted_at=datetime.utcnow())
    )
    await db.commit()

