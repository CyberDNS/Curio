from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.category import Category
from app.models.user import User
from app.schemas.category import (
    Category as CategorySchema,
    CategoryCreate,
    CategoryUpdate,
)

router = APIRouter()


@router.get("/", response_model=List[CategorySchema])
def get_categories(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Get all active (non-deleted) categories for the current user."""
    categories = (
        db.query(Category)
        .filter(Category.user_id == current_user.id, Category.is_deleted == False)
        .order_by(Category.display_order)
        .all()
    )
    return categories


@router.post("/", response_model=CategorySchema)
def create_category(
    category: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new category for the current user.

    If a soft-deleted category with the same slug exists, it will be restored
    instead of creating a new one.
    """
    # Check if a soft-deleted category with this slug exists
    existing_deleted = (
        db.query(Category)
        .filter(
            Category.slug == category.slug,
            Category.user_id == current_user.id,
            Category.is_deleted == True,
        )
        .first()
    )

    if existing_deleted:
        # Restore the soft-deleted category
        existing_deleted.is_deleted = False
        existing_deleted.deleted_at = None
        existing_deleted.name = category.name
        existing_deleted.description = category.description
        existing_deleted.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing_deleted)
        return existing_deleted

    # Check if an active category with this slug exists
    existing_active = (
        db.query(Category)
        .filter(
            Category.slug == category.slug,
            Category.user_id == current_user.id,
            Category.is_deleted == False,
        )
        .first()
    )
    if existing_active:
        raise HTTPException(
            status_code=400, detail="Category with this slug already exists"
        )

    db_category = Category(**category.model_dump(), user_id=current_user.id)
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category


@router.put("/{category_id}", response_model=CategorySchema)
def update_category(
    category_id: int,
    category_update: CategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a category for the current user."""
    category = (
        db.query(Category)
        .filter(
            Category.id == category_id,
            Category.user_id == current_user.id,
            Category.is_deleted == False,
        )
        .first()
    )
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    update_data = category_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(category, key, value)

    db.commit()
    db.refresh(category)
    return category


@router.delete("/{category_id}")
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Soft delete a category for the current user.

    The category is marked as deleted but remains in the database to preserve
    historical newspaper editions. It will not appear in category lists or be
    used for new article classifications.
    """
    category = (
        db.query(Category)
        .filter(
            Category.id == category_id,
            Category.user_id == current_user.id,
            Category.is_deleted == False,
        )
        .first()
    )
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # Soft delete: mark as deleted instead of removing from database
    category.is_deleted = True
    category.deleted_at = datetime.utcnow()
    db.commit()

    return {"message": "Category deleted successfully"}


@router.post("/reorder", response_model=List[CategorySchema])
def reorder_categories(
    category_ids: List[int],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Reorder categories for the current user.

    Accepts a list of category IDs in the desired order.
    Updates display_order for each category.
    """
    # Verify all categories belong to the current user and are not deleted
    categories = (
        db.query(Category)
        .filter(
            Category.user_id == current_user.id,
            Category.id.in_(category_ids),
            Category.is_deleted == False,
        )
        .all()
    )

    if len(categories) != len(category_ids):
        raise HTTPException(
            status_code=400, detail="Some categories not found or don't belong to you"
        )

    # Update display_order for each category
    category_map = {cat.id: cat for cat in categories}
    for index, category_id in enumerate(category_ids):
        category_map[category_id].display_order = index

    db.commit()

    # Return updated categories in order (only non-deleted)
    updated_categories = (
        db.query(Category)
        .filter(Category.user_id == current_user.id, Category.is_deleted == False)
        .order_by(Category.display_order)
        .all()
    )
    return updated_categories
