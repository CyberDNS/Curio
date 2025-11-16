from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class UserSettingsBase(BaseModel):
    key: str
    value: str


class UserSettingsCreate(UserSettingsBase):
    pass


class UserSettingsUpdate(BaseModel):
    value: str


class UserSettings(UserSettingsBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
