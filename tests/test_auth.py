import pytest
import asyncio
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_register_sends_otp(async_client, mock_redis, mock_ses):
    resp = await async_client.post("/auth/register", json={"email": "user@example.com", "password": "Password123!", "phone": "+27821234567"})
    assert resp.status_code == 200
    # OTP should be sent via SES
    assert any("user@example.com" in email["to"] for email in mock_ses.sent_emails)
    # OTP should be in redis
    otp_key = f"otp:register:user@example.com"
    otp = await mock_redis.get(otp_key)
    assert otp is not None

@pytest.mark.asyncio
async def test_verify_email_creates_user(async_client, mock_redis):
    email = "verify@example.com"
    otp = "123456"
    await mock_redis.set(f"otp:register:{email}", otp)
    resp = await async_client.post("/auth/verify-email", json={"email": email, "otp": otp})
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == email

@pytest.mark.asyncio
async def test_login_sends_otp(async_client, mock_redis, mock_ses):
    email = "login@example.com"
    # Assume user exists
    # Create user in DB or mock as needed
    resp = await async_client.post("/auth/login", json={"email": email, "password": "Password123!"})
    assert resp.status_code == 200
    assert any(email in e["to"] for e in mock_ses.sent_emails)
    otp = await mock_redis.get(f"otp:login:{email}")
    assert otp is not None

@pytest.mark.asyncio
async def test_verify_login_returns_tokens(async_client, mock_redis):
    email = "login2@example.com"
    otp = "654321"
    await mock_redis.set(f"otp:login:{email}", otp)
    resp = await async_client.post("/auth/verify-login", json={"email": email, "otp": otp})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data and "refresh_token" in data

@pytest.mark.asyncio
async def test_forgot_password_flow(async_client, mock_redis, mock_ses):
    email = "forgot@example.com"
    resp = await async_client.post("/auth/forgot-password", json={"email": email})
    assert resp.status_code == 200
    assert any(email in e["to"] for e in mock_ses.sent_emails)
    otp = await mock_redis.get(f"otp:forgot:{email}")
    assert otp is not None
    # Now reset password
    resp2 = await async_client.post("/auth/reset-password", json={"email": email, "otp": otp.decode() if hasattr(otp, 'decode') else otp, "new_password": "NewPassword123!"})
    assert resp2.status_code == 200

@pytest.mark.asyncio
async def test_rate_limiting(async_client, mock_redis):
    email = "ratelimit@example.com"
    for _ in range(5):
        resp = await async_client.post("/auth/register", json={"email": email, "password": "Password123!", "phone": "+27821234567"})
        assert resp.status_code == 200
    # 6th attempt should be rate limited
    resp = await async_client.post("/auth/register", json={"email": email, "password": "Password123!", "phone": "+27821234567"})
    assert resp.status_code in (429, 400)