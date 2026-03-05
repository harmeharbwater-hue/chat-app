from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.contact import Contact, ContactStatus
from app.models.user import User
from app.schemas.contacts import ContactCreate, ContactRead, ContactUpdate
from app.api.auth import get_current_user


router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.get("/search_users", response_model=List[dict])
async def search_users(
    q: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[dict]:
    stmt = (
        select(User)
        .where(
            and_(
                User.id != current_user.id,
                or_(
                    User.username.ilike(f"%{q}%"),
                    User.email.ilike(f"%{q}%"),
                ),
            )
        )
        .limit(20)
    )
    result = await db.execute(stmt)
    users = result.scalars().all()
    return [
        {"id": u.id, "username": u.username, "email": u.email}
        for u in users
    ]


@router.get("", response_model=List[ContactRead])
async def list_contacts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[ContactRead]:
    stmt = select(Contact).where(Contact.user_id == current_user.id)
    result = await db.execute(stmt)
    contacts = result.scalars().all()
    return [ContactRead.model_validate(c) for c in contacts]


@router.post("", response_model=ContactRead, status_code=status.HTTP_201_CREATED)
async def create_or_request_contact(
    payload: ContactCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ContactRead:
    if payload.target_user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot add yourself as a contact")

    target = await db.get(User, payload.target_user_id)
    if not target:
        raise HTTPException(status_code=404, detail="Target user not found")

    # Check if relationship already exists
    existing_stmt = select(Contact).where(
        and_(
            Contact.user_id == current_user.id,
            Contact.contact_user_id == payload.target_user_id,
        )
    )
    result = await db.execute(existing_stmt)
    existing = result.scalar_one_or_none()
    if existing:
        return ContactRead.model_validate(existing)

    contact = Contact(
        user_id=current_user.id,
        contact_user_id=payload.target_user_id,
        status=ContactStatus.PENDING,
    )
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    return ContactRead.model_validate(contact)


@router.patch("/{contact_id}", response_model=ContactRead)
async def update_contact(
    contact_id: int,
    payload: ContactUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ContactRead:
    contact = await db.get(Contact, contact_id)
    if not contact or contact.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Contact not found")

    if payload.action == "accept":
        contact.status = ContactStatus.ACCEPTED
    elif payload.action == "block":
        contact.status = ContactStatus.BLOCKED
    elif payload.action == "remove":
        await db.delete(contact)
        await db.commit()
        raise HTTPException(status_code=204, detail="Contact removed")

    await db.commit()
    await db.refresh(contact)
    return ContactRead.model_validate(contact)

