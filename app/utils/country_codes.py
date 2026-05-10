# TODO: Expand COUNTRY_LIST to full ISO 3166-1 alpha-2 list in a separate data-only PR.

COUNTRY_LIST: list[tuple[str, str]] = [
    ("AR", "Argentina"),
    ("AU", "Australia"),
    ("AT", "Austria"),
    ("BE", "Belgium"),
    ("BR", "Brazil"),
    ("CA", "Canada"),
    ("HR", "Croatia"),
    ("CZ", "Czechia"),
    ("DK", "Denmark"),
    ("FI", "Finland"),
    ("FR", "France"),
    ("DE", "Germany"),
    ("HU", "Hungary"),
    ("IE", "Ireland"),
    ("IT", "Italy"),
    ("JP", "Japan"),
    ("NL", "Netherlands"),
    ("NO", "Norway"),
    ("PL", "Poland"),
    ("PT", "Portugal"),
    ("RO", "Romania"),
    ("SK", "Slovakia"),
    ("SI", "Slovenia"),
    ("KR", "South Korea"),
    ("ES", "Spain"),
    ("SE", "Sweden"),
    ("CH", "Switzerland"),
    ("GB", "United Kingdom"),
    ("US", "United States"),
]

COUNTRY_CODES: frozenset[str] = frozenset(code for code, _ in COUNTRY_LIST)

_CODE_TO_NAME: dict[str, str] = {code: name for code, name in COUNTRY_LIST}

# Pre-formatted (code, "🇭🇺 Hungary") pairs — use directly in <select> option labels
COUNTRY_OPTIONS: list[tuple[str, str]] = []  # populated after flag_emoji is defined

LEGACY_NATIONALITY_MAP: dict[str, str] = {
    "Hungarian": "HU",
    "Magyar": "HU",
    "German": "DE",
    "Austrian": "AT",
    "Croatian": "HR",
    "Slovak": "SK",
    "Romanian": "RO",
    "Czech": "CZ",
    "Polish": "PL",
    "Slovenian": "SI",
    "British": "GB",
    "American": "US",
    "Brazilian": "BR",
    "Argentine": "AR",
    "Argentinian": "AR",
    "Spanish": "ES",
    "French": "FR",
    "Italian": "IT",
    "Dutch": "NL",
    "Belgian": "BE",
    "Portuguese": "PT",
    "Swiss": "CH",
    "Swedish": "SE",
    "Norwegian": "NO",
    "Danish": "DK",
    "Finnish": "FI",
    "Irish": "IE",
    "Canadian": "CA",
    "Australian": "AU",
    "Japanese": "JP",
    "Korean": "KR",
    "South Korean": "KR",
}


def flag_emoji(alpha2: str | None) -> str:
    if not alpha2 or len(alpha2) != 2:
        return ""
    a, b = alpha2.upper()
    return chr(0x1F1E6 + ord(a) - 65) + chr(0x1F1E6 + ord(b) - 65)


COUNTRY_OPTIONS = [(code, f"{flag_emoji(code)} {name}") for code, name in COUNTRY_LIST]


def country_display_name(alpha2: str | None) -> str:
    if not alpha2:
        return "—"
    code = alpha2.strip().upper()
    name = _CODE_TO_NAME.get(code)
    if not name:
        return code
    return f"{flag_emoji(code)} {name}"


def normalize_legacy_nationality(value: str | None) -> str | None:
    if not value:
        return None
    stripped = value.strip()
    if stripped.upper() in COUNTRY_CODES:
        return stripped.upper()
    return LEGACY_NATIONALITY_MAP.get(stripped)


def nationalities_display(primary: str | None, secondary: str | None = None) -> str:
    p = country_display_name(primary)
    if not secondary:
        return p
    return f"{p} · {country_display_name(secondary)}"


def register_filters(env) -> None:
    env.filters["country_display_name"] = country_display_name
    env.filters["flag_emoji"] = flag_emoji
    env.filters["nationalities_display"] = nationalities_display
