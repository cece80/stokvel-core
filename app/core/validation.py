import re
from typing import Dict
from datetime import date, datetime
from app.core.exceptions import ValidationError

__all__ = [
    "validate_sa_phone",
    "validate_email",
    "validate_sa_id",
]

VALID_SA_PHONE_PREFIXES = ("06", "07", "08")


def validate_sa_phone(phone: str) -> str:
    """
    Validate and normalize a South African phone number to +27XXXXXXXXX.
    Args:
        phone: Input phone number (various formats)
    Returns:
        Normalized phone number in +27XXXXXXXXX format
    Raises:
        ValidationError if invalid
    """
    phone = re.sub(r"[\s\-\(\)]", "", phone)
    normalized = None
    if phone.startswith("+27") and len(phone) == 12:
        normalized = phone
    elif phone.startswith("27") and len(phone) == 11:
        normalized = "+" + phone
    elif phone.startswith("0") and len(phone) == 10:
        normalized = "+27" + phone[1:]
    else:
        raise ValidationError(
            f"Invalid SA phone number format: {phone}. Expected 0821234567, +27821234567, or 27821234567"
        )
    if len(normalized) != 12:
        raise ValidationError(f"Phone number wrong length: {normalized}")
    if not normalized[1:].isdigit():
        raise ValidationError(f"Phone number contains non-digits: {normalized}")
    if not normalized[3:5] in VALID_SA_PHONE_PREFIXES:
        raise ValidationError(f"Phone number prefix invalid: {normalized}")
    return normalized


def validate_email(email: str) -> str:
    """
    Validate an email address (basic RFC 5322 compliance).
    Args:
        email: Input email address
    Returns:
        Normalized email (lowercase)
    Raises:
        ValidationError if invalid
    """
    email = email.strip().lower()
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    if not re.match(pattern, email):
        raise ValidationError(f"Invalid email address: {email}")
    return email


def validate_sa_id(id_number: str) -> Dict[str, any]:
    """
    Validate a South African ID number (13 digits, Luhn check, date extraction).
    Args:
        id_number: 13-digit SA ID number
    Returns:
        Dict with extracted info (date_of_birth, gender, citizenship, age, id_number)
    Raises:
        ValidationError if invalid
    """
    id_number = re.sub(r"[\s-]", "", id_number)
    if not re.match(r"^\d{13}$", id_number):
        raise ValidationError("SA ID number must be exactly 13 digits")
    year = int(id_number[0:2])
    month = int(id_number[2:4])
    day = int(id_number[4:6])
    gender_code = int(id_number[6:10])
    citizenship = int(id_number[10])
    checksum_digit = int(id_number[12])
    current_year_2digit = datetime.now().year % 100
    if year > current_year_2digit:
        full_year = 1900 + year
    else:
        full_year = 2000 + year
    try:
        dob = date(full_year, month, day)
    except ValueError:
        raise ValidationError(f"Invalid date of birth in ID number: {full_year}-{month:02d}-{day:02d}")
    if dob > date.today():
        raise ValidationError("Date of birth cannot be in the future")
    gender = "female" if gender_code < 5000 else "male"
    if citizenship == 0:
        citizen_status = "citizen"
    elif citizenship == 1:
        citizen_status = "permanent_resident"
    else:
        raise ValidationError(f"Invalid citizenship digit: {citizenship}. Must be 0 (citizen) or 1 (permanent resident)")
    if not _luhn_check(id_number):
        raise ValidationError("ID number fails Luhn checksum validation")
    return {
        "is_valid": True,
        "date_of_birth": dob,
        "age": _calculate_age(dob),
        "gender": gender,
        "citizenship": citizen_status,
        "id_number": id_number,
    }


def _luhn_check(id_number: str) -> bool:
    """
    Perform Luhn algorithm check on SA ID number.
    Args:
        id_number: 13-digit string
    Returns:
        True if valid, False otherwise
    """
    digits = [int(d) for d in id_number]
    checksum = 0
    for i, digit in enumerate(reversed(digits)):
        if i % 2 == 1:
            doubled = digit * 2
            if doubled > 9:
                doubled -= 9
            checksum += doubled
        else:
            checksum += digit
    return checksum % 10 == 0


def _calculate_age(dob: date) -> int:
    """
    Calculate age from date of birth.
    Args:
        dob: Date of birth
    Returns:
        Age in years
    """
    today = date.today()
    age = today.year - dob.year
    if (today.month, today.day) < (dob.month, dob.day):
        age -= 1
    return age
