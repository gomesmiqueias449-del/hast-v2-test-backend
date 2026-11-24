from __future__ import annotations

import json
import os
import secrets
import sqlite3
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator

import jwt
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

JWT_ALGORITHM = "HS256"
DEFAULT_TOKEN_TTL_SECONDS = 7 * 24 * 60 * 60
MAX_TOKEN_TTL_SECONDS = 30 * 24 * 60 * 60


class GuestLogin(BaseModel):
    device_id: str = Field(min_length=1, max_length=128)


class RenameRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=100)


def create_app(
    database_path: str | None = None,
    jwt_secret: str | None = None,
    token_ttl_seconds: int | None = None,
) -> FastAPI:
    db_path = database_path or os.getenv("DATABASE_PATH", "./data/game.db")
    secret = jwt_secret if jwt_secret is not None else os.getenv("JWT_SECRET", "")
    ttl_value = token_ttl_seconds
    if ttl_value is None:
        try:
            ttl_value = int(os.getenv("TOKEN_TTL_SECONDS", str(DEFAULT_TOKEN_TTL_SECONDS)))
        except ValueError:
            ttl_value = 0

    @contextmanager
    def connect_db() -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(db_path, timeout=5)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize_database() -> None:
        if db_path != ":memory:":
            Path(db_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
        with connect_db() as connection:
            connection.execute("PRAGMA busy_timeout = 5000")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    level INTEGER NOT NULL DEFAULT 1,
                    coins INTEGER NOT NULL DEFAULT 0,
                    gems INTEGER NOT NULL DEFAULT 0,
                    inventory TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL
                )
                """
            )

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if len(secret.encode("utf-8")) < 32:
            raise RuntimeError("JWT_SECRET must be set to a random value of at least 32 bytes")
        if ttl_value < 60 or ttl_value > MAX_TOKEN_TTL_SECONDS:
            raise RuntimeError("TOKEN_TTL_SECONDS must be between 60 and 2592000")
        initialize_database()
        yield

    app = FastAPI(
        title="Hast Private Test Backend",
        version="1.0.0",
        description="Isolated guest/profile API for authorized testing. Photon integration is disabled.",
        lifespan=lifespan,
    )
    bearer = HTTPBearer(auto_error=False)

    def issue_token(user_id: str) -> str:
        now = datetime.now(timezone.utc)
        return jwt.encode(
            {"sub": user_id, "iat": now, "exp": now + timedelta(seconds=ttl_value)},
            secret,
            algorithm=JWT_ALGORITHM,
        )

    def require_user(
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    ) -> str:
        if credentials is None or credentials.scheme.lower() != "bearer":
            raise HTTPException(
                status_code=401,
                detail="bearer_token_required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        try:
            payload = jwt.decode(
                credentials.credentials,
                secret,
                algorithms=[JWT_ALGORITHM],
                options={"require": ["sub", "iat", "exp"]},
            )
            subject = payload.get("sub")
            if not isinstance(subject, str) or not subject:
                raise jwt.InvalidTokenError("invalid_subject")
            return subject
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=401,
                detail="invalid_or_expired_token",
                headers={"WWW-Authenticate": "Bearer"},
            )

    def load_user(user_id: str) -> sqlite3.Row | None:
        with connect_db() as connection:
            return connection.execute(
                "SELECT id, display_name, level, coins, gems, inventory, created_at FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()

    @app.get("/health")
    def health() -> dict[str, object]:
        return {"ok": True, "service": "hast-private-test-backend", "photonIntegration": False}

    @app.post("/v2/auth/guest")
    def guest_login(request: GuestLogin) -> dict[str, object]:
        # The supplied device_id is validated but deliberately not stored or used as an account key.
        if not request.device_id.strip():
            raise HTTPException(status_code=400, detail="invalid_device_id")

        user_id = "guest-" + secrets.token_hex(16)
        created_at = datetime.now(timezone.utc).isoformat()
        with connect_db() as connection:
            connection.execute(
                """
                INSERT INTO users (id, display_name, level, coins, gems, inventory, created_at)
                VALUES (?, ?, 1, 0, 0, '[]', ?)
                """,
                (user_id, "Jogador", created_at),
            )

        return {
            "success": True,
            "userId": user_id,
            "displayName": "Jogador",
            "accessToken": issue_token(user_id),
            "sessionId": secrets.token_urlsafe(24),
        }

    @app.get("/v2/profile/{user_id}")
    def profile(user_id: str, authenticated_user: str = Depends(require_user)) -> dict[str, object]:
        if authenticated_user != user_id:
            raise HTTPException(status_code=403, detail="profile_access_forbidden")

        user = load_user(user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="user_not_found")
        try:
            inventory = json.loads(user["inventory"])
        except (TypeError, json.JSONDecodeError):
            inventory = []

        return {
            "success": True,
            "userId": user["id"],
            "displayName": user["display_name"],
            "level": user["level"],
            "coins": user["coins"],
            "gems": user["gems"],
            "inventory": inventory,
            "selectedSkin": None,
            "progress": {},
            "settings": {},
        }

    @app.post("/v2/profile/{user_id}/name")
    def rename(
        user_id: str,
        request: RenameRequest,
        authenticated_user: str = Depends(require_user),
    ) -> dict[str, object]:
        if authenticated_user != user_id:
            raise HTTPException(status_code=403, detail="profile_access_forbidden")

        name = request.display_name.strip()
        if len(name) < 3 or len(name) > 20:
            raise HTTPException(status_code=400, detail="invalid_name")

        with connect_db() as connection:
            cursor = connection.execute(
                "UPDATE users SET display_name = ? WHERE id = ?",
                (name, user_id),
            )
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="user_not_found")

        return {"success": True, "userId": user_id, "displayName": name}

    @app.post("/v2/photon/session", include_in_schema=True)
    def photon_session_disabled() -> None:
        raise HTTPException(status_code=501, detail="photon_integration_disabled_for_test")

    return app


app = create_app()
