from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.core.auth import get_current_user, get_current_user_optional
from app.models.settings import UserSettings
from app.models.user import User
from app.schemas.settings import (
    UserSettings as SettingsSchema,
    UserSettingsCreate,
    UserSettingsUpdate,
)

router = APIRouter()


@router.get("/", response_model=List[SettingsSchema])
def get_all_settings(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Get all settings for the current user."""
    settings = (
        db.query(UserSettings).filter(UserSettings.user_id == current_user.id).all()
    )
    return settings


@router.get("/{key}", response_model=SettingsSchema)
def get_setting(
    key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific setting by key for the current user."""
    setting = (
        db.query(UserSettings)
        .filter(UserSettings.key == key, UserSettings.user_id == current_user.id)
        .first()
    )
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    return setting


@router.post("/", response_model=SettingsSchema)
def create_or_update_setting(
    setting: UserSettingsCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create or update a setting for the current user."""
    # Check if setting exists for this user
    existing = (
        db.query(UserSettings)
        .filter(
            UserSettings.key == setting.key, UserSettings.user_id == current_user.id
        )
        .first()
    )
    if existing:
        # Update existing
        existing.value = setting.value
        if hasattr(setting, "description") and setting.description:
            existing.description = setting.description
        db.commit()
        db.refresh(existing)
        return existing

    # Create new
    db_setting = UserSettings(**setting.model_dump(), user_id=current_user.id)
    db.add(db_setting)
    db.commit()
    db.refresh(db_setting)
    return db_setting


@router.put("/{key}", response_model=SettingsSchema)
def update_setting(
    key: str,
    setting_update: UserSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a setting."""
    setting = db.query(UserSettings).filter(UserSettings.key == key).first()
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")

    setting.value = setting_update.value
    db.commit()
    db.refresh(setting)
    return setting


@router.delete("/{key}")
def delete_setting(
    key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a setting."""
    setting = db.query(UserSettings).filter(UserSettings.key == key).first()
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")

    db.delete(setting)
    db.commit()
    return {"message": "Setting deleted successfully"}
