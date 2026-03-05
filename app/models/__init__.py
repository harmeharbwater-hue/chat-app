from app.db import Base  # noqa: F401

# Import models so that Base.metadata.create_all sees all tables
from .user import User  # noqa: F401
from .contact import Contact  # noqa: F401
from .message import Message  # noqa: F401
from .file_attachment import FileAttachment  # noqa: F401
from .password_reset_token import PasswordResetToken  # noqa: F401

