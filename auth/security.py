"""
Security Module
================
Rate limiting, fraud detection, and security hardening.

Protections:
- OTP rate limiting (max 3 requests per 10 minutes per phone)
- Login attempt tracking (lockout after 5 failed attempts)
- New device detection + OTP re-verification
- IP-based anomaly detection
- Concurrent session limits
- Brute force protection
"""

import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from dataclasses import dataclass, field
from collections import defaultdict


# ──────────────────────────────────────────────
# Rate Limiting
# ──────────────────────────────────────────────

# In production: use Redis for distributed rate limiting
# This is an in-memory implementation for reference

OTP_MAX_REQUESTS = 3
OTP_WINDOW_SECONDS = 600  # 10 minutes
OTP_COOLDOWN_SECONDS = 60  # Min time between requests

LOGIN_MAX_ATTEMPTS = 5
LOGIN_LOCKOUT_MINUTES = 30


@dataclass
class RateLimitEntry:
    """Track rate limit state for a key (phone, email, IP)."""
    key: str
    attempts: List[float] = field(default_factory=list)
    locked_until: Optional[float] = None
    
    def is_locked(self) -> bool:
        if self.locked_until and time.time() < self.locked_until:
            return True
        if self.locked_until and time.time() >= self.locked_until:
            self.locked_until = None
            self.attempts.clear()
        return False
    
    def record_attempt(self) -> None:
        now = time.time()
        self.attempts.append(now)
    
    def clean_old_attempts(self, window_seconds: int) -> None:
        cutoff = time.time() - window_seconds
        self.attempts = [t for t in self.attempts if t > cutoff]
    
    def recent_count(self, window_seconds: int) -> int:
        self.clean_old_attempts(window_seconds)
        return len(self.attempts)


class RateLimiter:
    """
    In-memory rate limiter.
    
    Production: Replace with Redis-based implementation.
    
    Usage:
        limiter = RateLimiter()
        allowed, msg = limiter.check_otp_rate("+27821234567")
        if not allowed:
            return {"error": msg}
    """
    
    def __init__(self):
        self._entries: Dict[str, RateLimitEntry] = {}
    
    def _get_entry(self, key: str) -> RateLimitEntry:
        if key not in self._entries:
            self._entries[key] = RateLimitEntry(key=key)
        return self._entries[key]
    
    def check_otp_rate(self, identifier: str) -> tuple:
        """
        Check if OTP request is allowed for this phone/email.
        
        Rules:
        - Max 3 OTP requests per 10 minutes
        - Min 60 seconds between requests
        
        Returns:
            (is_allowed, message)
        """
        entry = self._get_entry(f"otp:{identifier}")
        
        if entry.is_locked():
            remaining = int(entry.locked_until - time.time())
            return False, f"Too many OTP requests. Try again in {remaining} seconds"
        
        # Check cooldown (min time between requests)
        if entry.attempts:
            last_attempt = entry.attempts[-1]
            elapsed = time.time() - last_attempt
            if elapsed < OTP_COOLDOWN_SECONDS:
                wait = int(OTP_COOLDOWN_SECONDS - elapsed)
                return False, f"Please wait {wait} seconds before requesting another OTP"
        
        # Check rate limit
        recent = entry.recent_count(OTP_WINDOW_SECONDS)
        if recent >= OTP_MAX_REQUESTS:
            entry.locked_until = time.time() + OTP_WINDOW_SECONDS
            return False, f"OTP rate limit exceeded. Try again in {OTP_WINDOW_SECONDS // 60} minutes"
        
        entry.record_attempt()
        return True, "OK"
    
    def check_login_attempts(self, identifier: str) -> tuple:
        """
        Check if login attempt is allowed (brute force protection).
        
        Rules:
        - Max 5 failed attempts
        - 30 minute lockout after exceeding
        
        Returns:
            (is_allowed, message)
        """
        entry = self._get_entry(f"login:{identifier}")
        
        if entry.is_locked():
            remaining = int((entry.locked_until - time.time()) / 60)
            return False, f"Account temporarily locked. Try again in {remaining} minutes"
        
        recent = entry.recent_count(LOGIN_LOCKOUT_MINUTES * 60)
        if recent >= LOGIN_MAX_ATTEMPTS:
            entry.locked_until = time.time() + (LOGIN_LOCKOUT_MINUTES * 60)
            return False, f"Too many failed login attempts. Locked for {LOGIN_LOCKOUT_MINUTES} minutes"
        
        return True, "OK"
    
    def record_failed_login(self, identifier: str) -> None:
        """Record a failed login attempt."""
        entry = self._get_entry(f"login:{identifier}")
        entry.record_attempt()
    
    def clear_login_attempts(self, identifier: str) -> None:
        """Clear login attempts on successful login."""
        key = f"login:{identifier}"
        if key in self._entries:
            self._entries[key].attempts.clear()


# ──────────────────────────────────────────────
# Fraud Detection
# ──────────────────────────────────────────────

@dataclass
class FraudSignal:
    """A detected fraud signal."""
    signal_type: str       # rapid_otp, multi_account, unusual_ip, etc.
    severity: str          # low, medium, high, critical
    description: str
    user_id: Optional[str] = None
    ip_address: Optional[str] = None
    device_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict = field(default_factory=dict)


def detect_rapid_otp_requests(
    phone: str,
    recent_requests: List[datetime],
    threshold: int = 5,
    window_minutes: int = 5,
) -> Optional[FraudSignal]:
    """Detect rapid OTP request patterns (potential attack)."""
    cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)
    recent = [r for r in recent_requests if r > cutoff]
    
    if len(recent) >= threshold:
        return FraudSignal(
            signal_type="rapid_otp",
            severity="high",
            description=f"{len(recent)} OTP requests in {window_minutes} minutes for {phone}",
            metadata={"phone": phone, "count": len(recent)},
        )
    return None


def detect_multi_account_device(
    device_id: str,
    accounts_on_device: List[str],
    threshold: int = 3,
) -> Optional[FraudSignal]:
    """Detect multiple accounts from the same device."""
    unique_accounts = set(accounts_on_device)
    
    if len(unique_accounts) >= threshold:
        return FraudSignal(
            signal_type="multi_account",
            severity="medium",
            description=f"Device {device_id} used by {len(unique_accounts)} accounts",
            device_id=device_id,
            metadata={"account_count": len(unique_accounts)},
        )
    return None


def detect_unusual_login_location(
    user_id: str,
    current_ip: str,
    known_ips: List[str],
) -> Optional[FraudSignal]:
    """Detect login from previously unseen IP."""
    if current_ip not in known_ips and len(known_ips) > 0:
        return FraudSignal(
            signal_type="unusual_ip",
            severity="low",
            description=f"Login from new IP {current_ip}",
            user_id=user_id,
            ip_address=current_ip,
            metadata={"known_ips_count": len(known_ips)},
        )
    return None


# ──────────────────────────────────────────────
# Security Hardening Utilities
# ──────────────────────────────────────────────

def validate_password_strength(password: str) -> tuple:
    """
    Validate password meets security requirements.
    (For optional password login - admin/supplier accounts)
    
    Returns:
        (is_valid, issues)
    """
    issues = []
    
    if len(password) < 8:
        issues.append("Password must be at least 8 characters")
    if not any(c.isupper() for c in password):
        issues.append("Must contain at least one uppercase letter")
    if not any(c.islower() for c in password):
        issues.append("Must contain at least one lowercase letter")
    if not any(c.isdigit() for c in password):
        issues.append("Must contain at least one digit")
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        issues.append("Must contain at least one special character")
    
    return len(issues) == 0, issues
