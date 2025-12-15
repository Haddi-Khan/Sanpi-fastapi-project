from database import Base
from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime
from sqlalchemy.schema import ForeignKey
from sqlalchemy.orm import relationship


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String, nullable=False)

    # NEW: Define relationship for MediaItem to access User
    media_items = relationship("MediaItem", back_populates="owner")


class ContactMessage(Base):
    __tablename__ = "contact_messages"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True)
    email = Column(String(100), index=True)
    subject = Column(String(255))
    message = Column(Text)
    submission_date = Column(DateTime, default=datetime.utcnow)


class MediaItem(Base):
    __tablename__ = "media_items"

    id = Column(Integer, primary_key=True, index=True)
    # CRITICAL: Foreign Key definition
    user_id = Column(Integer, ForeignKey("users.id"))
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(50))
    upload_date = Column(DateTime, default=datetime.utcnow)

    # NEW: Define relationship to User and the back-reference
    owner = relationship("User", back_populates="media_items")


class SharedMedia(Base):
    __tablename__ = "shared_media"

    id = Column(Integer, primary_key=True, index=True)
    media_id = Column(Integer, ForeignKey("media_items.id"))
    owner_id = Column(Integer, ForeignKey("users.id"))
    shared_with_id = Column(Integer, ForeignKey("users.id"))

    # Relationships to allow template access (e.g. m.owner.username)
    media = relationship("MediaItem", backref="shared_entries")
    owner = relationship("User", foreign_keys=[owner_id])
    shared_with = relationship("User", foreign_keys=[shared_with_id])
