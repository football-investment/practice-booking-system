"""Unit tests for app/utils/country_codes.py"""
import pytest
from app.utils.country_codes import (
    COUNTRY_CODES,
    COUNTRY_LIST,
    COUNTRY_OPTIONS,
    LEGACY_NATIONALITY_MAP,
    flag_emoji,
    country_display_name,
    nationalities_display,
    normalize_legacy_nationality,
)


class TestFlagEmoji:
    def test_hu(self):
        assert flag_emoji("HU") == "🇭🇺"

    def test_us(self):
        assert flag_emoji("US") == "🇺🇸"

    def test_de(self):
        assert flag_emoji("DE") == "🇩🇪"

    def test_lowercase_accepted(self):
        assert flag_emoji("hu") == "🇭🇺"

    def test_none_returns_empty(self):
        assert flag_emoji(None) == ""

    def test_empty_string_returns_empty(self):
        assert flag_emoji("") == ""

    def test_invalid_length_returns_empty(self):
        assert flag_emoji("HUN") == ""


class TestCountryDisplayName:
    def test_hu(self):
        assert country_display_name("HU") == "🇭🇺 Hungary"

    def test_de(self):
        assert country_display_name("DE") == "🇩🇪 Germany"

    def test_none_returns_dash(self):
        assert country_display_name(None) == "—"

    def test_empty_string_returns_dash(self):
        assert country_display_name("") == "—"

    def test_unknown_code_returns_code_not_500(self):
        result = country_display_name("ZZ")
        assert result == "ZZ"

    def test_lowercase_normalized(self):
        assert country_display_name("hu") == "🇭🇺 Hungary"


class TestCountryCodes:
    def test_hu_in_codes(self):
        assert "HU" in COUNTRY_CODES

    def test_legacy_text_not_in_codes(self):
        assert "Hungarian" not in COUNTRY_CODES
        assert "Magyar" not in COUNTRY_CODES

    def test_country_list_sorted_by_name(self):
        names = [name for _, name in COUNTRY_LIST]
        assert names == sorted(names)

    def test_country_options_length_matches_list(self):
        assert len(COUNTRY_OPTIONS) == len(COUNTRY_LIST)

    def test_country_options_format(self):
        for code, label in COUNTRY_OPTIONS:
            assert code in COUNTRY_CODES
            assert flag_emoji(code) in label
            name = dict(COUNTRY_LIST)[code]
            assert name in label


class TestLegacyMap:
    def test_hungarian_maps_to_hu(self):
        assert LEGACY_NATIONALITY_MAP["Hungarian"] == "HU"

    def test_magyar_maps_to_hu(self):
        assert LEGACY_NATIONALITY_MAP["Magyar"] == "HU"

    def test_german_maps_to_de(self):
        assert LEGACY_NATIONALITY_MAP["German"] == "DE"


class TestNationalitiesDisplay:
    def test_primary_only(self):
        assert nationalities_display("HU") == "🇭🇺 Hungary"

    def test_primary_and_secondary(self):
        assert nationalities_display("HU", "BR") == "🇭🇺 Hungary · 🇧🇷 Brazil"

    def test_none_primary(self):
        assert nationalities_display(None, None) == "—"

    def test_empty_secondary_treated_as_none(self):
        assert nationalities_display("HU", None) == "🇭🇺 Hungary"
        assert nationalities_display("HU", "") == "🇭🇺 Hungary"

    def test_no_separator_when_secondary_missing(self):
        result = nationalities_display("HU", None)
        assert "·" not in result

    def test_separator_present_when_secondary_set(self):
        result = nationalities_display("HU", "BR")
        assert "·" in result

    def test_unknown_primary_graceful(self):
        result = nationalities_display("ZZ", None)
        assert result == "ZZ"
        assert "500" not in result

    def test_unknown_secondary_graceful(self):
        result = nationalities_display("HU", "ZZ")
        assert "🇭🇺 Hungary" in result
        assert "ZZ" in result
        assert "500" not in result


class TestNormalizeLegacyNationality:
    def test_legacy_text_maps(self):
        assert normalize_legacy_nationality("Hungarian") == "HU"
        assert normalize_legacy_nationality("Magyar") == "HU"

    def test_valid_iso_passthrough(self):
        assert normalize_legacy_nationality("HU") == "HU"
        assert normalize_legacy_nationality("DE") == "DE"

    def test_lowercase_iso_normalized(self):
        assert normalize_legacy_nationality("hu") == "HU"

    def test_none_returns_none(self):
        assert normalize_legacy_nationality(None) is None

    def test_unknown_returns_none(self):
        assert normalize_legacy_nationality("Martian") is None
