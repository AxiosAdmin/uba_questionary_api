import os
from types import SimpleNamespace
from uuid import uuid4

import pytest

os.environ["POSTGRES_DB"] = "test_db"
os.environ["POSTGRES_USER"] = "test_user"
os.environ["POSTGRES_PASSWORD"] = "test_password"
os.environ["POSTGRES_HOST"] = "localhost"
os.environ["POSTGRES_PORT"] = "5432"
os.environ["OPENAI_API_KEY"] = "test-openai-key"
os.environ["FERNET_KEY"] = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-with-at-least-32-bytes"
os.environ["ALGORITHM"] = "HS256"
os.environ["JWT_EXPIRATION_MINUTES"] = "60"
os.environ["RESTRICT_STRIPE_AUTH_KEY"] = "rk_test"
os.environ["PUBLIC_STRIPE_AUTH_KEY"] = "pk_test"
os.environ["SECRET_STRIPE_AUTH_KEY"] = "sk_test"
os.environ["WEBHOOK_STRIPE_SECRECT_KEY"] = "whsec_test"
os.environ["DEFAULT_PRICE_ID"] = "price_test"
os.environ["PAYMENT_CURRENCY"] = "brl"
os.environ["CHECKOUT_REDIRECT_URL"] = "https://example.com/checkout"
os.environ["FRONTEND_ORIGINS"] = '["http://localhost:3000"]'


class FakeScalarResult:
    def __init__(self, items=None):
        self.items = list(items or [])

    def first(self):
        return self.items[0] if self.items else None

    def all(self):
        return list(self.items)


class FakeExecuteResult:
    def __init__(self, scalars_items=None, rows=None):
        self._scalars_items = list(scalars_items or [])
        self._rows = list(rows or [])

    def scalars(self):
        return FakeScalarResult(self._scalars_items)

    def all(self):
        return list(self._rows)


class FakeAsyncSession:
    def __init__(self, execute_results=None, scalar_results=None, commit_error=None):
        self.execute_results = list(execute_results or [])
        self.scalar_results = list(scalar_results or [])
        self.commit_error = commit_error
        self.executed_queries = []
        self.scalar_queries = []
        self.added = []
        self.deleted = []
        self.refreshed = []
        self.committed = False
        self.rolled_back = False
        self.closed = False

    async def execute(self, query):
        self.executed_queries.append(query)
        if self.execute_results:
            return self.execute_results.pop(0)
        return FakeExecuteResult()

    async def scalar(self, query):
        self.scalar_queries.append(query)
        if self.scalar_results:
            return self.scalar_results.pop(0)
        return None

    def add(self, item):
        self.added.append(item)

    async def delete(self, item):
        self.deleted.append(item)

    async def commit(self):
        if self.commit_error is not None:
            raise self.commit_error
        self.committed = True

    async def rollback(self):
        self.rolled_back = True

    async def refresh(self, item):
        self.refreshed.append(item)

    async def close(self):
        self.closed = True

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.fixture
def app():
    from src.__main__ import app as fastapi_app

    return fastapi_app


@pytest.fixture
def client(app):
    from fastapi.testclient import TestClient

    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def fake_db_session():
    return FakeAsyncSession()


@pytest.fixture
def override_db(app, fake_db_session):
    from src.configs.db_connection import get_db

    async def _override():
        yield fake_db_session

    app.dependency_overrides[get_db] = _override
    yield fake_db_session
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def authorize_request(monkeypatch):
    from fastapi import HTTPException
    from src.middleware import jwt_middleware

    def _authorize(user_id=None, institution_id=None, permission_error=None):
        resolved_user_id = str(user_id or uuid4())
        resolved_institution_id = str(institution_id or uuid4())
        middleware_session = FakeAsyncSession()

        monkeypatch.setattr(
            jwt_middleware.JWTUtils,
            "decode_jwt",
            staticmethod(lambda token: {"id": resolved_user_id}),
        )

        async def _check_permissions(*args, **kwargs):
            if permission_error is not None:
                raise HTTPException(
                    status_code=permission_error["status_code"],
                    detail=permission_error["detail"],
                )
            return True

        monkeypatch.setattr(jwt_middleware, "check_permissions", _check_permissions)
        monkeypatch.setattr(jwt_middleware, "async_session", lambda: middleware_session)

        return {
            "Authorization": "Bearer test-token",
            "x-institution-id": resolved_institution_id,
        }, middleware_session

    return _authorize


@pytest.fixture
def sample_ids():
    return SimpleNamespace(
        user_id=uuid4(),
        institution_id=uuid4(),
        question_id=uuid4(),
        profile_id=uuid4(),
        subscription_id=uuid4(),
    )
