from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Admin(SQLModel, table=True):

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(max_length=128, unique=True, nullable=False)
    password_hash: str = Field(max_length=256, nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Report(SQLModel, table=True):

    id: Optional[int] = Field(default=None, primary_key=True)
    token: Optional[str] = Field(
        default=None, max_length=64, unique=True, index=True)
    subject: str = Field(max_length=256, nullable=False)
    description: Optional[str] = Field(default=None)
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = Field(default="Received", max_length=32)
    admin_response: Optional[str] = None
    responded_at: Optional[datetime] = None
