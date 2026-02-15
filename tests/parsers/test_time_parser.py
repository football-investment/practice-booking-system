#!/usr/bin/env python3
"""
Test the MM:SS.CC time format parser
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

    Args:
        time_str: Time string in MM:SS.CC format

    Returns:
        Total seconds as float

    Raises:
        ValueError: If format is invalid
    """
    time_str = time_str.strip()

    # Pattern: optional minutes, required seconds, optional decimal
    # Examples: "1:30.45", "1:30", "0:10.5", "10.5", "10"
    pattern = r'^(?:(\d+):)?(\d+(?:\.\d+)?)$'
    match = re.match(pattern, time_str)

    if not match:
        raise ValueError("Invalid format. Use MM:SS.CC (e.g., 1:30.45)")

    minutes_str, seconds_str = match.groups()

    minutes = int(minutes_str) if minutes_str else 0
    seconds = float(seconds_str)

    # Validate seconds range
    if seconds >= 60:
        raise ValueError("Seconds must be < 60")

    total_seconds = minutes * 60 + seconds

    return total_seconds


# Test cases
test_cases = [
    ("1:30.45", 90.45, "1 minute, 30.45 seconds"),
    ("0:10.5", 10.5, "10.5 seconds"),
    ("2:15.00", 135.0, "2 minutes, 15 seconds"),
    ("1:30", 90.0, "1 minute, 30 seconds"),
    ("10.5", 10.5, "10.5 seconds"),
    ("10", 10.0, "10 seconds"),
    ("0:09.99", 9.99, "9.99 seconds"),
    ("5:00", 300.0, "5 minutes"),
]

print("Testing MM:SS.CC time format parser\n")
print("=" * 60)

for time_input, expected, description in test_cases:
    try:
        result = parse_time_format(time_input)
        status = "✓" if abs(result - expected) < 0.01 else "✗"
        print(f"{status} '{time_input}' → {result:.2f}s (expected {expected:.2f}s) - {description}")
    except ValueError as e:
        print(f"✗ '{time_input}' → ERROR: {e}")

print("\n" + "=" * 60)
print("\nTesting invalid inputs:\n")

invalid_cases = [
    ("1:60.0", "Seconds >= 60"),
    ("1:90", "Seconds >= 60"),
    ("abc", "Invalid format"),
    ("1:2:3", "Invalid format"),
    ("-1:30", "Invalid format"),
    ("", "Invalid format"),
]

for time_input, expected_error in invalid_cases:
    try:
        result = parse_time_format(time_input)
        print(f"✗ '{time_input}' → {result:.2f}s (should have failed!)")
    except ValueError as e:
        print(f"✓ '{time_input}' → ERROR: {e}")

print("\n" + "=" * 60)
print("\n✅ All tests completed!")
