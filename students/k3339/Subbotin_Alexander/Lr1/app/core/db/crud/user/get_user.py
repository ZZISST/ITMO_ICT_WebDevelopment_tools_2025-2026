from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.models.user import User


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    """
    Retrieve a user by their ID.
    
    Args:
        db: Async SQLAlchemy session
        user_id: User ID to search for
    
    Returns:
        Optional[User]: User instance if found, None otherwise
    """
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    """
    Retrieve a user by their username.
    
    Args:
        db: Async SQLAlchemy session
        username: Username to search for
    
    Returns:
        Optional[User]: User instance if found, None otherwise
    """
    stmt = select(User).where(User.username == username)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """
    Retrieve a user by their email address.

    Args:
        db: Async SQLAlchemy session
        email: Email address to search for

    Returns:
        Optional[User]: User instance if found, None otherwise
    """
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_users(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[User]:
    """
    Retrieve a paginated list of all users.

    Args:
        db: Async SQLAlchemy session
        skip: Number of records to skip
        limit: Maximum number of records to return

    Returns:
        List[User]: List of user instances
    """
    stmt = select(User).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())
