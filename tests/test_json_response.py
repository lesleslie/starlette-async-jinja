import datetime
import typing as t
from dataclasses import dataclass
from enum import Enum

import pytest
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.testclient import TestClient
from starlette_async_jinja.responses import JsonResponse


class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"


@dataclass
class User:
    id: int
    username: str
    email: str
    role: UserRole
    created_at: datetime.datetime


@pytest.mark.asyncio
async def test_json_response_with_complex_types() -> None:
    """Test JsonResponse with complex data types."""
    # Create test data
    now = datetime.datetime.now()
    user = User(
        id=1,
        username="testuser",
        email="test@example.com",
        role=UserRole.ADMIN,
        created_at=now,
    )

    # Create app with routes
    async def get_user(request: t.Any) -> t.Any:
        return JsonResponse(user)

    async def get_users(request: t.Any) -> t.Any:
        users = [
            user,
            User(
                id=2,
                username="user2",
                email="user2@example.com",
                role=UserRole.USER,
                created_at=now,
            ),
        ]
        return JsonResponse(users)

    async def get_mixed_data(request: t.Any) -> t.Any:
        data = {
            "users": [user],
            "settings": {
                "theme": "dark",
                "notifications": True,
                "last_login": now,
            },
            "stats": {
                "visits": 100,
                "conversion_rate": 0.25,
            },
        }
        return JsonResponse(data)

    routes = [
        Route("/user", get_user),
        Route("/users", get_users),
        Route("/mixed", get_mixed_data),
    ]

    app = Starlette(routes=routes)
    client = TestClient(app)

    # Test single object
    response = client.get("/user")
    assert response.status_code == 200
    user_data = response.json()
    assert user_data["id"] == 1
    assert user_data["username"] == "testuser"
    assert user_data["email"] == "test@example.com"
    assert user_data["role"] == "admin"
    assert "created_at" in user_data

    # Test list of objects
    response = client.get("/users")
    assert response.status_code == 200
    users_data = response.json()
    assert len(users_data) == 2
    assert users_data[0]["id"] == 1
    assert users_data[1]["id"] == 2

    # Test mixed data
    response = client.get("/mixed")
    assert response.status_code == 200
    mixed_data = response.json()
    assert len(mixed_data["users"]) == 1
    assert mixed_data["settings"]["theme"] == "dark"
    assert mixed_data["settings"]["notifications"] is True
    assert mixed_data["stats"]["visits"] == 100
    assert mixed_data["stats"]["conversion_rate"] == 0.25


@pytest.mark.asyncio
async def test_json_response_with_custom_status_and_headers() -> None:
    """Test JsonResponse with custom status code and headers."""

    # Create app with routes
    async def created(request: t.Any) -> t.Any:
        return JsonResponse(
            {"status": "created", "id": 123},
            status_code=201,
            headers={"Location": "/resources/123"},
        )

    async def not_found(request: t.Any) -> t.Any:
        return JsonResponse(
            {"error": "Resource not found"},
            status_code=404,
        )

    async def with_custom_headers(request: t.Any) -> t.Any:
        return JsonResponse(
            {"data": "test"},
            headers={
                "X-Custom-Header": "custom-value",
                "Cache-Control": "no-cache",
            },
        )

    routes = [
        Route("/created", created),
        Route("/not-found", not_found),
        Route("/custom-headers", with_custom_headers),
    ]

    app = Starlette(routes=routes)
    client = TestClient(app)

    # Test created response
    response = client.get("/created")
    assert response.status_code == 201
    assert response.headers["location"] == "/resources/123"
    assert response.json() == {"status": "created", "id": 123}

    # Test not found response
    response = client.get("/not-found")
    assert response.status_code == 404
    assert response.json() == {"error": "Resource not found"}

    # Test custom headers
    response = client.get("/custom-headers")
    assert response.status_code == 200
    assert response.headers["x-custom-header"] == "custom-value"
    assert response.headers["cache-control"] == "no-cache"
    assert response.json() == {"data": "test"}
