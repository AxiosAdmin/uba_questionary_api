"""Database connection setup using SQLAlchemy's asynchronous engine and session maker."""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from src.configs.configs import settings

# from src.utils.db_institution_define import set_default_institution

engine = create_async_engine(settings.database_url, echo=True)

async_session = async_sessionmaker(  # type: ignore[call-overload]
    bind=engine, expire_on_commit=False, class_=AsyncSession
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide a database session for dependency injection."""
    session: AsyncSession = async_session()

    # await set_default_institution(
    #     session=session,
    #     institution_id=request.headers.get("x-institution-id")
    # )

    try:
        yield session
    except Exception as e:
        await session.rollback()
        raise e
    finally:
        await session.close()
