"""
South African ID Number Validator
==================================
Validates the 13-digit SA ID number using the Luhn algorithm.

Format: YYMMDD SSSS C A Z
- YYMMDD: Date of birth
- SSSS: Gender (0000-4999 = Female, 5000-9999 = Male)
- C: Citizenship (0 = SA citizen, 1 = Permanent resident)
- A: Usually 8 (was used for racial classification, now deprecated)
- Z: Checksum digit (Luhn algorithm)
"""

import re
from datetime import date, datetime
from typing import Optional


class SAIDValidationError(Exception):
    """Raised when SA ID number validation fails."""
    pass


def validate_sa_id_number(id_number: str) -> dict:
    """
    Validate a South African ID number.
    
    Args:
        id_number: 13-digit SA ID number
        
    Returns:
        Dictionary with extracted information:
        - date_of_birth: date object
        - gender: 'male' or 'female'
        - citizenship: 'citizen' or 'permanent_resident'
        - is_valid: bool
        
    Raises:
        SAIDValidationError: If the ID number is invalid
    """
    # Remove spaces and dashes
    id_number = re.sub(r'[\s-]', '', id_number)
    
    # Must be exactly 13 digits
    if not re.match(r'^\d{13}$', id_number):
        raise SAIDValidationError(
            "SA ID number must be exactly 13 digits"
        )
    
    # Extract components
    year = int(id_number[0:2])
    month = int(id_number[2:4])
    day = int(id_number[4:6])
    gender_code = int(id_number[6:10])
    citizenship = int(id_number[10])
    checksum_digit = int(id_number[12])
    
    # Validate date of birth
    # Determine century: if year > current 2-digit year, assume 1900s
    current_year_2digit = datetime.now().year % 100
    if year > current_year_2digit:
        full_year = 1900 + year
    else:
        full_year = 2000 + year
    
    try:
        dob = date(full_year, month, day)
    except ValueError:
        raise SAIDValidationError(
            f"Invalid date of birth in ID number: {full_year}-{month:02d}-{day:02d}"
        )
    
    # Validate date is not in the future
    if dob > date.today():
        raise SAIDValidationError("Date of birth cannot be in the future")
    
    # Determine gender
    gender = "female" if gender_code < 5000 else "male"
    
    # Citizenship status
    if citizenship == 0:
        citizen_status = "citizen"
    elif citizenship == 1:
        citizen_status = "permanent_resident"
    else:
        raise SAIDValidationError(
            f"Invalid citizenship digit: {citizenship}. Must be 0 (citizen) or 1 (permanent resident)"
        )
    
    # Luhn algorithm validation
    if not _luhn_check(id_number):
        raise SAIDValidationError("ID number fails Luhn checksum validation")
    
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
    """
    digits = [int(d) for d in id_number]
    checksum = 0
    
    # Process from right to left, doubling every second digit
    for i, digit in enumerate(reversed(digits)):
        if i % 2 == 1:  # Every second digit from right (0-indexed)
            doubled = digit * 2
            if doubled > 9:
                doubled -= 9
            checksum += doubled
        else:
            checksum += digit
    
    return checksum % 10 == 0


def _calculate_age(dob: date) -> int:
    """Calculate age from date of birth."""
    today = date.today()
    age = today.year - dob.year
    if (today.month, today.day) < (dob.month, dob.day):
        age -= 1
    return age


def validate_phone_number(phone: str) -> str:
    """
    Validate and normalize a South African phone number.
    
    Accepts: 0821234567, +27821234567, 27821234567
    Returns: +27821234567 (E.164 format)
    """
    # Remove spaces, dashes, parentheses
    phone = re.sub(r'[\s\-\(\)]', '', phone)
    
    # Handle different formats
    if phone.startswith('+27'):
        normalized = phone
    elif phone.startswith('27') and len(phone) == 11:
        normalized = '+' + phone
    elif phone.startswith('0') and len(phone) == 10:
        normalized = '+27' + phone[1:]
    else:
        raise SAIDValidationError(
            f"Invalid SA phone number format: {phone}. "
            "Expected format: 0821234567, +27821234567, or 27821234567"
        )
    
    # Validate length
    if len(normalized) != 12:
        raise SAIDValidationError(f"Phone number wrong length: {normalized}")
    
    # Validate it's all digits after +
    if not normalized[1:].isdigit():
        raise SAIDValidationError(f"Phone number contains non-digits: {normalized}")
    
    return normalized
