import sqlite3

import pytest
from fastapi.testclient import TestClient

from main import create_app


TEST_SECRET = "test-only-secret-not-for-deployment-0123456789abcdef"


def make_app(database_path, secret=TEST_SECRET):
    return create_app(
        database_path=str(database_path),
        jwt_secret=secret,
        token_ttl_seconds=3600,
    )


def guest_login(client: TestClient) -> dict:
    response = client.post(
        "/v2/auth/guest",
        json={"device_id": "android-test-device"},
    )
    assert response.status_code == 200
    return response.json()


def test_health_reports_photon_disabled(tmp_path):
    with TestClient(make_app(tmp_path / "test.sqlite3")) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert response.json()["photonIntegration"] is False


def test_guest_login_returns_random_test_identity_and_zero_balances(tmp_path):
    database = tmp_path / "test.sqlite3"
    with TestClient(make_app(database)) as client:
        first = guest_login(client)
        second = guest_login(client)
        profile = client.get(
            f"/v2/profile/{first['userId']}",
            headers={"Authorization": f"Bearer {first['accessToken']}"},
        )

    assert first["success"] is True
    assert first["userId"].startswith("guest-")
    assert first["displayName"] == "Jogador"
    assert first["accessToken"]
    assert first["sessionId"]
    assert "photonUserId" not in first
    assert "region" not in first
    assert first["userId"] != second["userId"]
    assert profile.json()["coins"] == 0
    assert profile.json()["gems"] == 0

    with sqlite3.connect(database) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(users)")}
    assert "device_id" not in columns


def test_profile_requires_own_bearer_token(tmp_path):
    with TestClient(make_app(tmp_path / "test.sqlite3")) as client:
        guest = guest_login(client)
        path = f"/v2/profile/{guest['userId']}"
        no_auth = client.get(path)
        own_profile = client.get(
            path,
            headers={"Authorization": f"Bearer {guest['accessToken']}"},
        )
        other_profile = client.get(
            "/v2/profile/guest-someone-else",
            headers={"Authorization": f"Bearer {guest['accessToken']}"},
        )

    assert no_auth.status_code == 401
    assert own_profile.status_code == 200
    assert own_profile.json()["coins"] == 0
    assert own_profile.json()["gems"] == 0
    assert other_profile.status_code == 403


def test_rename_persists_across_app_restart_and_rejects_short_names(tmp_path):
    database = tmp_path / "test.sqlite3"
    with TestClient(make_app(database)) as client:
        guest = guest_login(client)
        user_id = guest["userId"]
        headers = {"Authorization": f"Bearer {guest['accessToken']}"}
        name_path = f"/v2/profile/{user_id}/name"
        renamed = client.post(name_path, headers=headers, json={"display_name": "HastTeste"})
        invalid = client.post(name_path, headers=headers, json={"display_name": "ab"})

    with TestClient(make_app(database)) as restarted_client:
        profile = restarted_client.get(
            f"/v2/profile/{user_id}",
            headers=headers,
        )

    assert renamed.status_code == 200
    assert invalid.status_code == 400
    assert profile.status_code == 200
    assert profile.json()["displayName"] == "HastTeste"


def test_photon_session_is_explicitly_disabled(tmp_path):
    with TestClient(make_app(tmp_path / "test.sqlite3")) as client:
        response = client.post("/v2/photon/session")
    assert response.status_code == 501
    assert response.json()["detail"] == "photon_integration_disabled_for_test"


def test_service_refuses_to_start_without_a_long_jwt_secret(tmp_path):
    app = make_app(tmp_path / "test.sqlite3", secret="too-short")
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        with TestClient(app):
            pass
