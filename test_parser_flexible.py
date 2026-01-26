#!/usr/bin/env python3
"""
Test the flexible time format parser
"""
import re


def parse_time_format(time_str: str) -> float:
    """
    Parse MM:SS.CC time format to total seconds.

    Supported formats:
    - MM:SS.CC (e.g., "1:30.45" = 90.45 seconds)
    - MM:SS (e.g., "1:30" = 90.0 seconds)
    - SS.CC (e.g., "10.5" = 10.5 seconds)
    - SS (e.g., "10" = 10.0 seconds)
    - M:SS.CC (e.g., "1:05.5" = 65.5 seconds)

    Args:
        time_str: Time string in MM:SS.CC format

    Returns:
        Total seconds as float

    Raises:
        ValueError: If format is invalid
    """
    # Clean input: strip whitespace and remove any extra spaces
    time_str = time_str.strip().replace(' ', '')

    if not time_str:
        raise ValueError("Empty input")

    # Try parsing as pure decimal number first (e.g., "10.5", "45")
    if ':' not in time_str:
        try:
            seconds = float(time_str)
            if seconds < 0:
                raise ValueError("Time cannot be negative")
            return seconds
        except ValueError:
            raise ValueError("Invalid number format")

    # Parse MM:SS or MM:SS.CC format
    parts = time_str.split(':')

    if len(parts) != 2:
        raise ValueError("Use MM:SS.CC format (e.g., 1:30.45)")

    try:
        minutes = int(parts[0])
        seconds = float(parts[1])
    except ValueError:
        raise ValueError("Invalid time format")

    # Validate
    if minutes < 0 or seconds < 0:
        raise ValueError("Time cannot be negative")

    if seconds >= 60:
        raise ValueError("Seconds must be < 60")

    total_seconds = minutes * 60 + seconds

    return total_seconds


# Test cases
test_cases = [
    # Standard formats
    ("1:30.45", 90.45, "MM:SS.CC format"),
    ("0:10.5", 10.5, "0:SS.C format"),
    ("2:15.00", 135.0, "MM:SS.00 format"),
    ("1:30", 90.0, "MM:SS format (no decimals)"),

    # Pure seconds
    ("10.5", 10.5, "Pure decimal seconds"),
    ("10", 10.0, "Pure integer seconds"),
    ("45.67", 45.67, "Pure decimal"),

    # Single digit minutes
    ("1:05.5", 65.5, "M:SS.C format"),
    ("5:00", 300.0, "M:00 format"),
    ("0:09.99", 9.99, "0:0S.CC format"),

    # With spaces (should be cleaned)
    (" 1:30.45 ", 90.45, "With leading/trailing spaces"),
    ("1 : 30.45", 90.45, "With spaces around colon"),

    # Edge cases
    ("0:00", 0.0, "Zero time"),
    ("0:00.01", 0.01, "Very small time"),
    ("10:59.99", 659.99, "Maximum valid seconds"),
]

print("Testing flexible time format parser\n")
print("=" * 70)

for time_input, expected, description in test_cases:
    try:
        result = parse_time_format(time_input)
        status = "✓" if abs(result - expected) < 0.01 else "✗"
        print(f"{status} '{time_input}' → {result:.2f}s (expected {expected:.2f}s)")
        print(f"   {description}")
    except ValueError as e:
        print(f"✗ '{time_input}' → ERROR: {e}")
        print(f"   {description}")

print("\n" + "=" * 70)
print("\nTesting invalid inputs:\n")

invalid_cases = [
    ("1:60.0", "Seconds >= 60"),
    ("1:90", "Seconds >= 60"),
    ("abc", "Invalid format"),
    ("1:2:3", "Too many colons"),
    ("-1:30", "Negative time"),
    ("", "Empty input"),
    ("1:", "Missing seconds"),
    (":30", "Missing minutes"),
]

for time_input, expected_error in invalid_cases:
    try:
        result = parse_time_format(time_input)
        print(f"✗ '{time_input}' → {result:.2f}s (should have failed!)")
    except ValueError as e:
        print(f"✓ '{time_input}' → Correctly rejected: {e}")

print("\n" + "=" * 70)
print("\n✅ All tests completed!")
