import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Area, Venue
from tests.conftest import make_test_jwt


def _make_venue(db_session: Session) -> Venue:
    area = Area(
        query_text="Asheville, NC",
        display_name="Asheville, NC, USA",
        lat=35.5951,
        lon=-82.5515,
        radius_m=10000,
    )
    db_session.add(area)
    db_session.flush()

    venue = Venue(
        area_id=area.id,
        osm_id=1,
        osm_type="node",
        name="The Blue Note",
        address="1 Main St",
        lat=35.6,
        lon=-82.55,
        osm_tags={},
    )
    db_session.add(venue)
    db_session.commit()
    db_session.refresh(venue)
    return venue


def test_get_requires_auth(client: TestClient):
    assert client.get("/api/saved-venues").status_code == 401


def test_post_requires_auth(client: TestClient):
    assert client.post("/api/saved-venues", json={"venue_id": 1}).status_code == 401


def test_delete_requires_auth(client: TestClient):
    assert client.delete("/api/saved-venues/1").status_code == 401


def test_invalid_token_is_401(client: TestClient):
    headers = {"Authorization": "Bearer not-a-real-token"}
    assert client.get("/api/saved-venues", headers=headers).status_code == 401


def test_expired_token_is_401(client: TestClient):
    headers = {"Authorization": f"Bearer {make_test_jwt(expired=True)}"}
    assert client.get("/api/saved-venues", headers=headers).status_code == 401


def test_save_then_list(client: TestClient, db_session: Session, auth_headers: dict):
    venue = _make_venue(db_session)

    post_resp = client.post(
        "/api/saved-venues", json={"venue_id": venue.id}, headers=auth_headers
    )
    assert post_resp.status_code == 201
    assert post_resp.json()["venue_id"] == venue.id
    assert post_resp.json()["venue"]["name"] == "The Blue Note"

    list_resp = client.get("/api/saved-venues", headers=auth_headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1
    assert list_resp.json()[0]["venue_id"] == venue.id


def test_save_is_idempotent(client: TestClient, db_session: Session, auth_headers: dict):
    venue = _make_venue(db_session)

    first = client.post("/api/saved-venues", json={"venue_id": venue.id}, headers=auth_headers)
    second = client.post("/api/saved-venues", json={"venue_id": venue.id}, headers=auth_headers)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]

    list_resp = client.get("/api/saved-venues", headers=auth_headers)
    assert len(list_resp.json()) == 1


def test_save_nonexistent_venue_is_404(client: TestClient, auth_headers: dict):
    response = client.post("/api/saved-venues", json={"venue_id": 999999}, headers=auth_headers)
    assert response.status_code == 404


def test_delete_removes_saved_venue(client: TestClient, db_session: Session, auth_headers: dict):
    venue = _make_venue(db_session)
    client.post("/api/saved-venues", json={"venue_id": venue.id}, headers=auth_headers)

    delete_resp = client.delete(f"/api/saved-venues/{venue.id}", headers=auth_headers)
    assert delete_resp.status_code == 204

    list_resp = client.get("/api/saved-venues", headers=auth_headers)
    assert list_resp.json() == []


def test_delete_nonexistent_is_still_204(client: TestClient, auth_headers: dict):
    response = client.delete("/api/saved-venues/999999", headers=auth_headers)
    assert response.status_code == 204


def test_saved_venues_are_scoped_to_user(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    user_a_headers = {"Authorization": f"Bearer {make_test_jwt(uuid.uuid4())}"}
    user_b_headers = {"Authorization": f"Bearer {make_test_jwt(uuid.uuid4())}"}

    client.post("/api/saved-venues", json={"venue_id": venue.id}, headers=user_a_headers)

    assert client.get("/api/saved-venues", headers=user_a_headers).json() != []
    assert client.get("/api/saved-venues", headers=user_b_headers).json() == []
