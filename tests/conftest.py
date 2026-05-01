import pytest
import fakeredis
from fastapi.testclient import TestClient
from httpx import AsyncClient
from fastapi import FastAPI, Depends
from app.main import app  # Adjust import as needed
from app.dependencies import get_redis  # Adjust import as needed

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
    # Override dependencies
    app.dependency_overrides[get_redis] = lambda: mock_redis
    # If you have a get_ses dependency, override here as well
    # app.dependency_overrides[get_ses] = lambda: mock_ses
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides = {}