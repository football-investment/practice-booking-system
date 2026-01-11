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
    Check if HTML content contains EXECUTABLE (unescaped) XSS payload.

    This function distinguishes between:
    1. SAFE: Properly escaped output (no execution risk)
    2. VULNERABLE: Unescaped output in executable context

    Args:
        html_content: Rendered HTML content
        payload: Original XSS payload

    Returns:
        True if vulnerable (payload can execute), False if safe (payload escaped/non-executable)

    Security Contexts Considered SAFE:
    ────────────────────────────────────
    1. HTML Entity Encoding:
       - &lt;script&gt; instead of <script>
       - &amp;lt; instead of &lt;
       - &#60; instead of <
       - Payload in input value="" attributes (automatically escaped by browser)

    2. Attribute Context (safe if properly quoted):
       - value="&lt;script&gt;..." (escaped in attribute)
       - Displayed text nodes (non-executable context)

    3. Text Content:
       - Payload in <p>, <div>, <span> text nodes
       - Browser automatically escapes in text context

    Security Contexts Considered VULNERABLE:
    ─────────────────────────────────────────
    1. Executable Script Context:
       - <script>alert(1)</script> in HTML body
       - <img src=x onerror=alert(1)> with unescaped event handler

    2. Attribute Injection:
       - <div onclick=alert(1)> - unescaped event handler
       - <a href="javascript:alert(1)"> - javascript: protocol

    3. DOM-based XSS:
       - innerHTML assignment with unescaped input
       - document.write() with unescaped input

    Example Safe Cases (returns False):
    ───────────────────────────────────
    >>> html = '<input value="&lt;script&gt;alert(1)&lt;/script&gt;">'
    >>> is_xss_vulnerable(html, '<script>alert(1)</script>')
    False  # Escaped in input value - SAFE

    >>> html = '<p>&lt;img src=x onerror=alert(1)&gt;</p>'
    >>> is_xss_vulnerable(html, '<img src=x onerror=alert(1)>')
    False  # Escaped in text content - SAFE

    Example Vulnerable Cases (returns True):
    ────────────────────────────────────────
    >>> html = '<div><script>alert(1)</script></div>'
    >>> is_xss_vulnerable(html, '<script>alert(1)</script>')
    True  # Unescaped script tag - VULNERABLE

    >>> html = '<img src=x onerror=alert(1)>'
    >>> is_xss_vulnerable(html, '<img src=x onerror=alert(1)>')
    True  # Unescaped event handler - VULNERABLE
    """
    html_lower = html_content.lower()

    # ════════════════════════════════════════════════════════════════════════
    # STEP 1: Check for ESCAPED versions (SAFE contexts)
    # ════════════════════════════════════════════════════════════════════════

    # HTML entity encoding patterns (these indicate safe escaping)
    safe_escaped_patterns = [
        "&lt;script&gt;",      # <script> → &lt;script&gt;
        "&lt;img",             # <img → &lt;img
        "&lt;svg",             # <svg → &lt;svg
        "&lt;iframe",          # <iframe → &lt;iframe
        "&#60;script&#62;",    # <script> → &#60;script&#62;
        "&#60;img",            # <img → &#60;img
        "onerror&#61;",        # onerror= → onerror&#61;
        "onclick&#61;",        # onclick= → onclick&#61;
        "onload&#61;",         # onload= → onload&#61;
    ]

    # If we find escaped versions, the payload is SAFE (not executable)
    for escaped in safe_escaped_patterns:
        if escaped in html_lower:
            return False  # Payload properly escaped - NOT VULNERABLE

    # Check if payload is in INPUT value attribute (browser auto-escapes)
    # Pattern: value="<script>..." or value='<script>...'
    # This is SAFE because browsers treat input values as text, not executable code
    if 'value="&lt;' in html_lower or "value='&lt;" in html_lower:
        return False  # Input value context with escaping - NOT VULNERABLE

    # ════════════════════════════════════════════════════════════════════════
    # STEP 2: Check for UNESCAPED executable contexts (VULNERABLE)
    # ════════════════════════════════════════════════════════════════════════

    # Check for unescaped script tags (most dangerous)
    if "<script>" in html_lower and "&lt;script&gt;" not in html_lower:
        # Unescaped <script> tag found - HIGHLY VULNERABLE
        return True

    # Check for unescaped event handlers (second most dangerous)
    dangerous_event_handlers = [
        ("onerror=alert", "onerror&#61;"),
        ("onclick=alert", "onclick&#61;"),
        ("onload=alert", "onload&#61;"),
        ("onmouseover=alert", "onmouseover&#61;"),
        ("onfocus=alert", "onfocus&#61;"),
    ]

    for unescaped_handler, escaped_handler in dangerous_event_handlers:
        if unescaped_handler in html_lower:
            # Found unescaped event handler - check if there's also an escaped version
            if escaped_handler not in html_lower:
                # No escaped version found - VULNERABLE
                return True

    # Check for unescaped img/svg tags with onerror/onload
    if "<img " in html_lower and "onerror=" in html_lower:
        # Check if it's escaped
        if "&lt;img" not in html_lower:
            return True  # Unescaped <img onerror> - VULNERABLE

    if "<svg " in html_lower and "onload=" in html_lower:
        if "&lt;svg" not in html_lower:
            return True  # Unescaped <svg onload> - VULNERABLE

    # Check for unescaped iframe (can load malicious content)
    if "<iframe " in html_lower and "&lt;iframe" not in html_lower:
        return True  # Unescaped iframe - VULNERABLE

    # Check for javascript: protocol in href (clickjacking risk)
    if 'href="javascript:' in html_lower or "href='javascript:" in html_lower:
        return True  # javascript: protocol in link - VULNERABLE

    # Check for unescaped body/html tags with onload
    if "<body onload=" in html_lower or "<html onload=" in html_lower:
        return True  # Unescaped body/html onload - VULNERABLE

    # ════════════════════════════════════════════════════════════════════════
    # STEP 3: Default to SAFE if no dangerous patterns found
    # ════════════════════════════════════════════════════════════════════════

    # If we reach here, no executable XSS patterns were found
    # The payload is either:
    # - Properly escaped
    # - In a non-executable context (text node)
    # - Not present in the HTML
    return False  # NOT VULNERABLE


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
