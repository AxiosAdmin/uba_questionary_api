"""
Utility functions for database institution handling.

This module should implement Tenant_id in every route but
I coundn't set it up in a way that it works with the async
session and the way I structured the code.

So this function stays here for now, but it's not being used.
The idea is to set the current institution in the database
session when should be possible
"""

import uuid
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def set_default_institution(session: AsyncSession, institution_id: str | None):
    """Set the default institution for the current database session."""
    if not institution_id or institution_id.strip() == "":
        return

    try:
        uuid.UUID(institution_id)
    except ValueError:
        return

    await session.execute(
        text(f"SET SESSION app.current_institution_id = '{institution_id}'")
    )
