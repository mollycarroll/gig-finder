import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

import app.auth as auth_module
from app.db import engine, get_db
from app.main import app

# A fixed EC keypair standing in for Supabase's real (rotating) JWT signing
# keys, so tests can sign/verify tokens without a live JWKS endpoint.
_TEST_PRIVATE_KEY = ec.generate_private_key(ec.SECP256R1())
_TEST_PUBLIC_KEY = _TEST_PRIVATE_KEY.public_key()


@dataclass
class _FakeSigningKey:
    key: object


class _FakeJWKClient:
    def get_signing_key_from_jwt(self, token: str) -> _FakeSigningKey:
        return _FakeSigningKey(key=_TEST_PUBLIC_KEY)


@pytest.fixture(autouse=True)
def _patch_jwk_client(monkeypatch):
    monkeypatch.setattr(auth_module, "_jwk_client", lambda: _FakeJWKClient())


@pytest.fixture()
def db_session():
    """A DB session bound to a single connection/transaction.

    Route code under test calls db.commit() internally, which would
    normally end a plain transaction — so the session joins the outer
    transaction in "create_savepoint" mode: each internal commit only
    releases a SAVEPOINT, and rolling back the outer transaction at the
    end discards everything regardless of how many times the code under
    test committed.
    """
    connection = engine.connect()
    outer_transaction = connection.begin()
    TestSession = sessionmaker(bind=connection, join_transaction_mode="create_savepoint")
    session = TestSession()

    yield session

    session.close()
    outer_transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db_session: Session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def make_test_jwt(user_id: uuid.UUID | None = None, *, expired: bool = False) -> str:
    user_id = user_id or uuid.uuid4()
    now = datetime.now(timezone.utc)
    exp = now - timedelta(minutes=5) if expired else now + timedelta(hours=1)
    payload = {"sub": str(user_id), "aud": "authenticated", "role": "authenticated", "exp": exp}
    return jwt.encode(payload, _TEST_PRIVATE_KEY, algorithm="ES256")


@pytest.fixture()
def user_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture()
def auth_headers(user_id: uuid.UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_test_jwt(user_id)}"}
