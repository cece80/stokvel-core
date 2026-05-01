from fastapi import APIRouter, Request
from pydantic import BaseModel, EmailStr, constr
from app.services import auth_service
from app.core import rate_limit

router = APIRouter(prefix="/auth", tags=["auth"])

class RegisterRequest(BaseModel):
    email: EmailStr
    password: constr(min_length=8)
    name: constr(min_length=1)

class VerifyEmailRequest(BaseModel):
    email: EmailStr
    otp: constr(min_length=4, max_length=8)

class LoginRequest(BaseModel):
    email: EmailStr

class VerifyLoginRequest(BaseModel):
    email: EmailStr
    otp: constr(min_length=4, max_length=8)

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: constr(min_length=4, max_length=8)
    new_password: constr(min_length=8)

@router.post("/register")
@rate_limit("register", limit=5, period=600)
async def register(data: RegisterRequest, request: Request):
    resp = await auth_service.register_user(data.email, data.password, data.name)
    return resp

@router.post("/verify-email")
@rate_limit("verify_email", limit=10, period=600)
async def verify_email(data: VerifyEmailRequest, request: Request):
    resp = await auth_service.verify_email(data.email, data.otp)
    return resp

@router.post("/login")
@rate_limit("login", limit=10, period=600)
async def login(data: LoginRequest, request: Request):
    resp = await auth_service.send_login_otp(data.email)
    return resp

@router.post("/verify-login")
@rate_limit("verify_login", limit=10, period=600)
async def verify_login(data: VerifyLoginRequest, request: Request):
    resp = await auth_service.verify_login_otp(data.email, data.otp)
    return resp

@router.post("/forgot-password")
@rate_limit("forgot_password", limit=5, period=600)
async def forgot_password(data: ForgotPasswordRequest, request: Request):
    resp = await auth_service.send_password_reset_otp(data.email)
    return resp

@router.post("/reset-password")
@rate_limit("reset_password", limit=5, period=600)
async def reset_password(data: ResetPasswordRequest, request: Request):
    resp = await auth_service.reset_password(data.email, data.otp, data.new_password)
    return resp
