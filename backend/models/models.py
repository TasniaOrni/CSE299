import uuid
from datetime import datetime, time, timezone
from typing import List, Optional

from sqlalchemy import (
    Column, Integer, String, Enum as SAEnum, ForeignKey, Time, DateTime, Text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, declarative_base
from enum import Enum as PyEnum
from sqlmodel import SQLModel, Field, Relationship

# SQLModel base class
class SQLModelBase(SQLModel):
    pass

# SQLAlchemy declarative base
Base = declarative_base()

import uuid
from datetime import datetime, time, timezone
from typing import List, Optional

from sqlalchemy import (
    Column, Integer, String, Enum as SAEnum, ForeignKey, Time, DateTime, Text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, declarative_base
import enum
from sqlmodel import SQLModel, Field, Relationship

# SQLModel base class
class SQLModelBase(SQLModel):
    pass

# SQLAlchemy declarative base
Base = declarative_base()


class EventType(str, enum.Enum):
    assignment = "assignment"
    exam = "exam"
    final = "final"
    project = "project"
    office_hours = "office-hours"
    reminder = "reminder"

class Event(SQLModel, table=True):
    __tablename__ = 'events' 

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, nullable=False),
    )

    # Link to the user who created/owns the event
    user_id: uuid.UUID = Field(foreign_key="users.user_id", nullable=False)

    # Event details
    title: str = Field(sa_column=Column(String, nullable=False))
    description: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    type: EventType = Field(
        sa_column=Column(
            SAEnum(EventType, values_callable=lambda obj: [e.value for e in obj]), 
            nullable=False
        )
    )
    # Timing
    event_date: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    task_time: time = Field(sa_column=Column(Time, nullable=False))
    duration_minutes: Optional[int] = Field(default=60)

    # Google Calendar integration
    google_event_id: Optional[str] = Field(default=None)
    is_synced: bool = Field(default=False)

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relations
    user: "User" = Relationship(back_populates="events")   


class User(SQLModel, table=True):
    __tablename__ = "users"
    user_id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, nullable=False),
    )
    email: str = Field(index=True, nullable=False, unique=True)
    name: Optional[str] = Field(default=None)
    picture: Optional[str] = Field(default=None)
    
    # Google Calendar integration
    google_id: Optional[str] = Field(default=None, index=True)
    calendar_id: Optional[str] = Field(default=None)  # Primary calendar ID
    google_access_token: Optional[str] = Field(default=None, sa_column=Column(Text))
    google_refresh_token: Optional[str] = Field(default=None, sa_column=Column(Text))
    token_expiry: Optional[datetime] = Field(default=None)
    
    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    events: List["Event"] = Relationship(back_populates="user")   
