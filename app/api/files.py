import os
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File as FastAPIFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.db import get_db
from app.models.file_attachment import FileAttachment
from app.models.message import Message
from app.models.user import User
from app.schemas.files import FileAttachmentRead
from app.services.crypto import encrypt_bytes, decrypt_bytes


MEDIA_ROOT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "media")
os.makedirs(MEDIA_ROOT, exist_ok=True)


router = APIRouter(prefix="/files", tags=["files"])


@router.post("/upload", response_model=FileAttachmentRead, status_code=status.HTTP_201_CREATED)
async def upload_file(
    to_user_id: int,
    file: UploadFile = FastAPIFile(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FileAttachmentRead:
    raw = await file.read()
    encrypted = encrypt_bytes(raw)

    filename = f"{uuid.uuid4().hex}.bin"
    storage_path = os.path.join(MEDIA_ROOT, filename)

    with open(storage_path, "wb") as f:
        f.write(encrypted.ciphertext.encode("utf-8"))

    msg = Message(
        sender_id=current_user.id,
        receiver_id=to_user_id,
        ciphertext=encrypted.ciphertext,
        nonce=encrypted.nonce,
        tag=encrypted.tag,
        meta='{"type":"file"}',
    )
    db.add(msg)
    await db.flush()

    attachment = FileAttachment(
        message_id=msg.id,
        original_filename=file.filename or filename,
        content_type=(
            file.content_type
            if file.content_type and file.content_type != "application/octet-stream"
            else "application/octet-stream"
        ),
        size_bytes=len(raw),
        storage_path=storage_path,
        nonce=encrypted.nonce,
        tag=encrypted.tag,
    )
    db.add(attachment)
    await db.commit()
    await db.refresh(attachment)

    return FileAttachmentRead.model_validate(attachment)


@router.get("/{file_id}", response_model=FileAttachmentRead)
async def get_file_metadata(
    file_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FileAttachmentRead:
    attachment = await db.get(FileAttachment, file_id)
    if not attachment:
        raise HTTPException(status_code=404, detail="File not found")
    msg = await db.get(Message, attachment.message_id)
    if msg is None or (msg.sender_id != current_user.id and msg.receiver_id != current_user.id):
        raise HTTPException(status_code=403, detail="Not allowed to view this file")
    return FileAttachmentRead.model_validate(attachment)


@router.get("/{file_id}/download")
async def download_file(
    file_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    attachment = await db.get(FileAttachment, file_id)
    if not attachment:
        raise HTTPException(status_code=404, detail="File not found")
    msg = await db.get(Message, attachment.message_id)
    if msg is None or (msg.sender_id != current_user.id and msg.receiver_id != current_user.id):
        raise HTTPException(status_code=403, detail="Not allowed to download this file")

    if not os.path.exists(attachment.storage_path):
        raise HTTPException(status_code=404, detail="File content missing")

    with open(attachment.storage_path, "rb") as f:
        ciphertext_b64 = f.read().decode("utf-8")

    try:
        plaintext = decrypt_bytes(ciphertext_b64, attachment.nonce, attachment.tag)
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to decrypt file")

    return StreamingResponse(
        iter([plaintext]),
        media_type=attachment.content_type,
        headers={"Content-Disposition": f'attachment; filename="{attachment.original_filename}"'},
    )

