"""
Shared validation utilities for API endpoints.
Provides input validation to prevent SQL injection and other attacks.
"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator
from fastapi import Query, HTTPException


class PaginationParams(BaseModel):
    """Standard pagination parameters with validation."""

    skip: int = Field(default=0, ge=0, le=10000, description="Number of items to skip")
    limit: int = Field(
        default=100, ge=1, le=1000, description="Maximum number of items to return"
    )


class IdParam(BaseModel):
    """Validated ID parameter."""

    id: int = Field(gt=0, description="Positive integer ID")


def validate_positive_int(
    value: Optional[int], param_name: str = "parameter"
) -> Optional[int]:
    """
    Validate that an integer parameter is positive.

    Args:
        value: The value to validate
        param_name: Name of the parameter for error messages

    Returns:
        The validated value

    Raises:
        HTTPException: If validation fails
    """
    if value is not None:
        if not isinstance(value, int):
            raise HTTPException(
                status_code=400, detail=f"Invalid {param_name}: must be an integer"
            )
        if value < 0:
            raise HTTPException(
                status_code=400, detail=f"Invalid {param_name}: must be non-negative"
            )
        if value > 2147483647:  # Max PostgreSQL integer
            raise HTTPException(
                status_code=400, detail=f"Invalid {param_name}: value too large"
            )
    return value


def validate_string_length(
    value: Optional[str],
    param_name: str = "parameter",
    max_length: int = 255,
    min_length: int = 0,
) -> Optional[str]:
    """
    Validate string parameter length.

    Args:
        value: The string to validate
        param_name: Name of the parameter for error messages
        max_length: Maximum allowed length
        min_length: Minimum allowed length

    Returns:
        The validated value

    Raises:
        HTTPException: If validation fails
    """
    if value is not None:
        if not isinstance(value, str):
            raise HTTPException(
                status_code=400, detail=f"Invalid {param_name}: must be a string"
            )
        if len(value) < min_length:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid {param_name}: minimum length is {min_length}",
            )
        if len(value) > max_length:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid {param_name}: maximum length is {max_length}",
            )
    return value


def validate_days_back(days_back: Optional[int]) -> Optional[int]:
    """Validate days_back parameter (must be between 1 and 365)."""
    if days_back is not None:
        if not isinstance(days_back, int):
            raise HTTPException(
                status_code=400, detail="Invalid days_back: must be an integer"
            )
        if days_back < 0:
            raise HTTPException(
                status_code=400, detail="Invalid days_back: must be non-negative"
            )
        if days_back > 365:
            raise HTTPException(
                status_code=400, detail="Invalid days_back: maximum value is 365"
            )
    return days_back


# Query parameter dependencies for common validations
CategoryIdParam = Query(None, ge=1, le=2147483647, description="Category ID filter")
FeedIdParam = Query(None, ge=1, le=2147483647, description="Feed ID filter")
ArticleIdParam = Query(None, ge=1, le=2147483647, description="Article ID filter")
DaysBackParam = Query(None, ge=0, le=365, description="Number of days to look back")
LimitParam = Query(100, ge=1, le=1000, description="Maximum items to return")
SkipParam = Query(0, ge=0, le=100000, description="Number of items to skip")
