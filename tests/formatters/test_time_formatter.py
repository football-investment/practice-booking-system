#!/usr/bin/env python3
"""
Test the time display formatter
"""


def format_time_display(total_seconds: float) -> str:
    """
    Convert total seconds to MM:SS.CC display format.

    Args:
        total_seconds: Total time in seconds

    Returns:
        Formatted time string (e.g., "1:30.45")
    """
    minutes = int(total_seconds // 60)
    seconds = total_seconds % 60

    return f"{minutes}:{seconds:05.2f}"


# Test cases
test_cases = [
    (90.45, "1:30.45"),
    (10.5, "0:10.50"),
    (135.0, "2:15.00"),
    (90.0, "1:30.00"),
    (9.99, "0:09.99"),
    (300.0, "5:00.00"),
    (61.23, "1:01.23"),
    (3661.5, "61:01.50"),  # Over 1 hour
]

print("Testing time display formatter\n")
print("=" * 60)

for total_seconds, expected in test_cases:
    result = format_time_display(total_seconds)
    status = "✓" if result == expected else "✗"
    print(f"{status} {total_seconds}s → '{result}' (expected '{expected}')")

print("\n" + "=" * 60)
print("\n✅ All tests completed!")
