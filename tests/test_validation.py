import pytest
from app.core.validation import validate_sa_phone, validate_sa_id, validate_email

@pytest.mark.parametrize("phone,valid", [
    ("+27821234567", True),
    ("+27123456789", True),
    ("+27712345678", True),
    ("+26812345678", False),  # Not SA
    ("27821234567", False),   # Missing +
    ("+2782123456", False),   # Too short
    ("+278212345678", False), # Too long
    ("+2782abcdefg", False),  # Not digits
])
def test_sa_phone_validation(phone, valid):
    if valid:
        assert validate_sa_phone(phone)
    else:
        with pytest.raises(Exception):
            validate_sa_phone(phone)

@pytest.mark.parametrize("sa_id,valid", [
    ("8001015009087", True),   # Valid Luhn
    ("8001015009086", False),  # Invalid Luhn
    ("80010150090", False),    # Too short
    ("abcdefghijklm", False),  # Not digits
])
def test_sa_id_luhn_check(sa_id, valid):
    if valid:
        assert validate_sa_id(sa_id)["is_valid"]
    else:
        with pytest.raises(Exception):
            validate_sa_id(sa_id)

@pytest.mark.parametrize("email,valid", [
    ("user@example.com", True),
    ("user.name+tag@domain.co.za", True),
    ("user@sub.domain.com", True),
    ("user@domain", False),
    ("user@.com", False),
    ("user@domain..com", False),
    ("userdomain.com", False),
    ("@domain.com", False),
])
def test_email_validation(email, valid):
    if valid:
        assert validate_email(email)
    else:
        with pytest.raises(Exception):
            validate_email(email)
