import pytest
import fakeredis
from fastapi.testclient import TestClient
from httpx import AsyncClient
from fastapi import FastAPI, Depends
from app.main import app
from app.core.redis import get_redis

class MockSES:
    def __init__(self):
        self.sent_emails = []
    async def send_email(self, to_address, subject, body):
        self.sent_emails.append({"to": to_address, "subject": subject, "body": body})
        return True

@pytest.fixture(scope="session")
def event_loop():
    import asyncio
    loop = asyncio.get_event_loop()
    yield loop

@pytest.fixture()
def mock_redis():
    redis = fakeredis.FakeRedis()
    return redis

@pytest.fixture()
def mock_ses():
    return MockSES()

@pytest.fixture()
async def async_client(mock_redis, mock_ses):
    app.dependency_overrides[get_redis] = lambda: mock_redis
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides = {}
