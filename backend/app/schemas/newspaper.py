from pydantic import BaseModel
from datetime import datetime, date
from typing import Dict, List


class NewspaperStructure(BaseModel):
    """Structure of a newspaper with today section and category sections"""
    today: List[int]  # List of article IDs for today's section
    categories: Dict[str, List[int]]  # category_slug -> list of article IDs


class NewspaperBase(BaseModel):
    date: date
    structure: NewspaperStructure


class NewspaperCreate(NewspaperBase):
    user_id: int


class NewspaperUpdate(BaseModel):
    structure: NewspaperStructure


class Newspaper(NewspaperBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
