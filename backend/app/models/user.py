from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    # OAuth/OpenID fields
    sub = Column(
        String, unique=True, nullable=False, index=True
    )  # Subject identifier from OAuth provider
    email = Column(String, unique=True, nullable=False, index=True)
    name = Column(String)
    picture = Column(String)  # Profile picture URL

    # Additional user info
    preferred_username = Column(String)

    # Metadata
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    last_login = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    feeds = relationship("Feed", back_populates="user")
    articles = relationship("Article", back_populates="user")
    categories = relationship("Category", back_populates="user")
    settings = relationship("UserSettings", back_populates="user")
    newspapers = relationship("Newspaper", back_populates="user")
