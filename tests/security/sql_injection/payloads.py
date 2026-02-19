"""
SQL Injection Payload Library

Comprehensive collection of SQL injection vectors for security testing.
These payloads test different SQL injection techniques and database systems.
"""

from typing import List, Dict


class SQLInjectionPayloads:
    """Library of SQL injection attack vectors"""

    # Classic SQL injection payloads
    CLASSIC = [
        "' OR '1'='1",
        "' OR '1'='1' --",
        "' OR '1'='1' /*",
        "' OR 1=1--",
        "' OR 1=1#",
        "' OR 1=1/*",
        "admin' --",
        "admin' #",
        "admin'/*",
        "' or 1=1--",
        "' or 1=1#",
        "' or 1=1/*",
        "') or '1'='1--",
        "') or ('1'='1--",
    ]

    # Union-based injection
    UNION_BASED = [
        "' UNION SELECT NULL--",
        "' UNION SELECT NULL, NULL--",
        "' UNION SELECT NULL, NULL, NULL--",
        "' UNION SELECT username, password FROM users--",
        "' UNION SELECT table_name FROM information_schema.tables--",
        "' UNION SELECT column_name FROM information_schema.columns--",
    ]

    # Boolean-based blind injection
    BOOLEAN_BLIND = [
        "' AND '1'='1",
        "' AND '1'='2",
        "' AND 1=1--",
        "' AND 1=2--",
        "' AND SLEEP(5)--",
        "' AND (SELECT COUNT(*) FROM users) > 0--",
    ]

    # Time-based blind injection
    TIME_BASED = [
        "' AND SLEEP(5)--",
        "'; WAITFOR DELAY '00:00:05'--",
        "' AND BENCHMARK(5000000, MD5('test'))--",
        "' AND pg_sleep(5)--",  # PostgreSQL
    ]

    # Stacked queries
    STACKED_QUERIES = [
        "'; DROP TABLE users--",
        "'; DELETE FROM users WHERE '1'='1",
        "'; UPDATE users SET password='hacked' WHERE '1'='1",
        "'; INSERT INTO users VALUES ('hacker', 'password')--",
    ]

    # PostgreSQL specific
    POSTGRESQL = [
        "' AND 1=CAST((SELECT version()) AS int)--",
        "' AND 1=CAST((SELECT current_database()) AS int)--",
        "' UNION SELECT NULL, version()--",
        "' AND pg_sleep(5)--",
        "'; SELECT pg_sleep(5)--",
    ]

    # Comment-based injection
    COMMENT_BASED = [
        "admin'--",
        "admin'#",
        "admin'/*",
        "' OR '1'='1'--",
        "' OR '1'='1'#",
        "' OR '1'='1'/*",
    ]

    # Encoded payloads (URL encoding)
    ENCODED = [
        "%27%20OR%20%271%27%3D%271",  # ' OR '1'='1
        "%27%20OR%201%3D1--",  # ' OR 1=1--
        "%27%20UNION%20SELECT%20NULL--",  # ' UNION SELECT NULL--
    ]

    # Second-order injection
    SECOND_ORDER = [
        "admin' --",
        "test'); DROP TABLE users--",
        "user<script>alert('XSS')</script>",  # Mixed attack
    ]

    # NoSQL injection (for MongoDB if used)
    NOSQL = [
        "' || '1'=='1",
        "{$gt: ''}",
        "{$ne: null}",
        "'; return true; //",
    ]

    @classmethod
    def get_all_payloads(cls) -> List[str]:
        """Get all SQL injection payloads"""
        all_payloads = []
        all_payloads.extend(cls.CLASSIC)
        all_payloads.extend(cls.UNION_BASED)
        all_payloads.extend(cls.BOOLEAN_BLIND)
        all_payloads.extend(cls.TIME_BASED)
        all_payloads.extend(cls.STACKED_QUERIES)
        all_payloads.extend(cls.POSTGRESQL)
        all_payloads.extend(cls.COMMENT_BASED)
        all_payloads.extend(cls.ENCODED)
        all_payloads.extend(cls.SECOND_ORDER)
        return all_payloads

    @classmethod
    def get_basic_payloads(cls) -> List[str]:
        """Get basic/essential SQL injection payloads for quick testing"""
        return [
            "' OR '1'='1",
            "' OR 1=1--",
            "admin' --",
            "' UNION SELECT NULL--",
            "' AND SLEEP(5)--",
            "'; DROP TABLE users--",
        ]

    @classmethod
    def get_payloads_by_category(cls, category: str) -> List[str]:
        """Get payloads by category"""
        categories = {
            "classic": cls.CLASSIC,
            "union": cls.UNION_BASED,
            "blind": cls.BOOLEAN_BLIND,
            "time": cls.TIME_BASED,
            "stacked": cls.STACKED_QUERIES,
            "postgresql": cls.POSTGRESQL,
            "comment": cls.COMMENT_BASED,
            "encoded": cls.ENCODED,
        }
        return categories.get(category.lower(), [])


# Expected secure behavior markers
SECURE_RESPONSES = {
    # Should NOT contain these in response (indicates vulnerability)
    "error_indicators": [
        "syntax error",
        "SQL syntax",
        "PostgreSQL",
        "mysql",
        "unclosed quotation",
        "quoted string not properly terminated",
        "syntax error near",
        "invalid input syntax",
    ],
    # Should contain these (indicates proper handling)
    "safe_indicators": [
        "Invalid credentials",
        "Bad Request",
        "Validation error",
        "Unprocessable Entity",
        "Forbidden",
        "Unauthorized",
    ],
}


def is_vulnerable_response(response_text: str, status_code: int) -> bool:
    """
    Check if response indicates SQL injection vulnerability

    Args:
        response_text: Response body text
        status_code: HTTP status code

    Returns:
        True if response indicates vulnerability, False if properly secured
    """
    # Check for SQL error messages in response
    for error_indicator in SECURE_RESPONSES["error_indicators"]:
        if error_indicator.lower() in response_text.lower():
            return True

    # If status is 200 with SQL injection payload, might be vulnerable
    if status_code == 200:
        # Additional checks for successful injection
        # (this is simplified - real detection would be more sophisticated)
        pass

    return False
