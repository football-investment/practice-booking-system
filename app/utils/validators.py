"""
Validation utilities for user registration and profile data
"""
import re
import phonenumbers
from typing import Optional, Tuple


def validate_phone_number(phone: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate and format phone number using international format

    Args:
        phone: Phone number string (e.g., "+36 20 123 4567" or "06201234567")

    Returns:
        Tuple of (is_valid, formatted_number, error_message)
        - is_valid: True if phone number is valid
        - formatted_number: Formatted phone number in international format (E164)
        - error_message: Error message if invalid, None otherwise

    Examples:
        >>> validate_phone_number("+36 20 123 4567")
        (True, "+36201234567", None)

        >>> validate_phone_number("invalid")
        (False, None, "Invalid phone number format")
    """
    if not phone or not phone.strip():
        return False, None, "Phone number is required"

    try:
        # Try to parse phone number
        # If no country code provided, assume Hungary (HU)
        if not phone.strip().startswith('+'):
            # Try with Hungary country code
            parsed = phonenumbers.parse(phone, "HU")
        else:
            parsed = phonenumbers.parse(phone, None)

        # Validate phone number
        if not phonenumbers.is_valid_number(parsed):
            return False, None, "Invalid phone number"

        # Format to E164 international format (+36201234567)
        formatted = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)

        return True, formatted, None

    except phonenumbers.NumberParseException as e:
        return False, None, f"Invalid phone number format: {str(e)}"
    except Exception as e:
        return False, None, f"Phone validation error: {str(e)}"


def validate_address(
    street_address: str,
    city: str,
    postal_code: str,
    country: str
) -> Tuple[bool, Optional[str]]:
    """
    Validate address fields

    Args:
        street_address: Street address
        city: City name
        postal_code: Postal/ZIP code
        country: Country name

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Street Address validation
    if not street_address or len(street_address.strip()) < 5:
        return False, "Street address must be at least 5 characters"

    # City validation
    if not city or len(city.strip()) < 2:
        return False, "City name must be at least 2 characters"

    # City should only contain letters, spaces, and hyphens
    if not re.match(r'^[a-zA-Z\s\-\.]+$', city):
        return False, "City name can only contain letters, spaces, hyphens, and periods"

    # Postal Code validation (basic - just check it's not empty)
    if not postal_code or len(postal_code.strip()) < 3:
        return False, "Postal code must be at least 3 characters"

    # Postal code format validation (alphanumeric, spaces, hyphens)
    if not re.match(r'^[a-zA-Z0-9\s\-]+$', postal_code):
        return False, "Postal code can only contain letters, numbers, spaces, and hyphens"

    # Country validation
    if not country or len(country.strip()) < 2:
        return False, "Country name must be at least 2 characters"

    # Country should only contain letters, spaces, and hyphens
    if not re.match(r'^[a-zA-Z\s\-]+$', country):
        return False, "Country name can only contain letters, spaces, and hyphens"

    return True, None


def validate_name(name: str, field_name: str = "Name") -> Tuple[bool, Optional[str]]:
    """
    Validate name field (first name, last name, nickname)

    Args:
        name: Name string
        field_name: Name of the field (for error messages)

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not name or not name.strip():
        return False, f"{field_name} is required"

    if len(name.strip()) < 2:
        return False, f"{field_name} must be at least 2 characters"

    # Name should contain at least one letter
    if not re.search(r'[a-zA-Z]', name):
        return False, f"{field_name} must contain at least one letter"

    return True, None
