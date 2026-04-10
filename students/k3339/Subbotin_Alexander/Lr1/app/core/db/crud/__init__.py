"""
CRUD operations module.

This module provides all database operations for the mavrodi_wall manager API.
All CRUD functions are organized by model type (user, reservation, review).
"""

# User CRUD operations
from app.core.db.crud.user.create_user import create_user
from app.core.db.crud.user.get_user import get_user_by_id, get_user_by_username, get_user_by_email, get_users
from app.core.db.crud.user.profile import create_user_profile, get_user_profile, update_user_profile
from app.core.db.crud.user.update_user import update_user, update_user_password


__all__ = [
    # User operations
    "create_user",
    "get_user_by_id",
    "get_user_by_username",
    "get_user_by_email",
    "get_users",
    "create_user_profile",
    "get_user_profile",
    "update_user_profile",
    "update_user",
    "update_user_password",
    
]
