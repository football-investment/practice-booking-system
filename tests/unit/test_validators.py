"""
Unit tests for app/utils/validators.py

Pure-function tests — no DB, no fixtures needed.
Covers all 3 validators: validate_phone_number, validate_address, validate_name.
"""
import pytest
from app.utils.validators import validate_phone_number, validate_address, validate_name


# ── validate_phone_number ─────────────────────────────────────────────────────

class TestValidatePhoneNumber:

    def test_empty_string_invalid(self):
        ok, fmt, err = validate_phone_number("")
        assert ok is False
        assert fmt is None
        assert "required" in err.lower()

    def test_whitespace_only_invalid(self):
        ok, fmt, err = validate_phone_number("   ")
        assert ok is False
        assert "required" in err.lower()

    def test_valid_e164_format(self):
        ok, fmt, err = validate_phone_number("+36201234567")
        assert ok is True
        assert fmt == "+36201234567"
        assert err is None

    def test_valid_with_spaces_international(self):
        ok, fmt, err = validate_phone_number("+36 20 123 4567")
        assert ok is True
        assert fmt == "+36201234567"
        assert err is None

    def test_valid_hungarian_without_plus(self):
        # No leading '+' → parsed with HU country code
        ok, fmt, err = validate_phone_number("06201234567")
        assert ok is True
        assert err is None

    def test_invalid_text_rejected(self):
        ok, fmt, err = validate_phone_number("invalid")
        assert ok is False
        assert fmt is None
        assert err is not None

    def test_too_short_number_rejected(self):
        ok, fmt, err = validate_phone_number("+1")
        assert ok is False
        assert fmt is None

    def test_valid_us_number(self):
        ok, fmt, err = validate_phone_number("+12125551234")
        assert ok is True
        assert fmt is not None

    def test_returns_e164_no_spaces(self):
        ok, fmt, err = validate_phone_number("+44 7911 123456")
        assert ok is True
        assert " " not in fmt
        assert fmt.startswith("+")

    @pytest.mark.parametrize("phone", [
        "+36201234567",
        "+36301234567",
        "+36701234567",
    ])
    def test_valid_hungarian_networks(self, phone):
        ok, fmt, err = validate_phone_number(phone)
        assert ok is True, f"Expected valid for {phone}, got: {err}"


# ── validate_address ──────────────────────────────────────────────────────────

class TestValidateAddress:

    def _ok(self, **kw):
        defaults = dict(
            street_address="Andrássy út 60",
            city="Budapest",
            postal_code="1062",
            country="Hungary",
        )
        defaults.update(kw)
        return validate_address(**defaults)

    def test_valid_address_passes(self):
        ok, err = self._ok()
        assert ok is True
        assert err is None

    def test_street_too_short_rejected(self):
        ok, err = self._ok(street_address="AB")
        assert ok is False
        assert "street" in err.lower()

    def test_street_none_rejected(self):
        ok, err = self._ok(street_address="")
        assert ok is False

    def test_city_too_short_rejected(self):
        ok, err = self._ok(city="X")
        assert ok is False
        assert "city" in err.lower()

    def test_city_with_numbers_rejected(self):
        ok, err = self._ok(city="Buda123")
        assert ok is False
        assert "city" in err.lower()

    def test_city_with_hyphen_valid(self):
        ok, err = self._ok(city="Milton-Keynes")
        assert ok is True

    def test_city_with_period_valid(self):
        ok, err = self._ok(city="St. Louis")
        assert ok is True

    def test_postal_code_too_short_rejected(self):
        ok, err = self._ok(postal_code="AB")
        assert ok is False
        assert "postal" in err.lower()

    def test_postal_code_with_special_chars_rejected(self):
        ok, err = self._ok(postal_code="1062@!")
        assert ok is False

    def test_postal_code_alphanumeric_valid(self):
        ok, err = self._ok(postal_code="SW1A 2AA")
        assert ok is True

    def test_country_too_short_rejected(self):
        ok, err = self._ok(country="X")
        assert ok is False
        assert "country" in err.lower()

    def test_country_with_numbers_rejected(self):
        ok, err = self._ok(country="Hungar1")
        assert ok is False

    def test_country_with_hyphen_valid(self):
        ok, err = self._ok(country="Bosnia-Herzegovina")
        assert ok is True

    @pytest.mark.parametrize("street,city,postal,country", [
        ("Kossuth tér 1-3", "Budapest", "1055", "Hungary"),
        ("10 Downing Street", "London", "SW1A 2AA", "United Kingdom"),
        ("Paseo de la Castellana 259D", "Madrid", "28046", "Spain"),
    ])
    def test_valid_international_addresses(self, street, city, postal, country):
        ok, err = validate_address(street, city, postal, country)
        assert ok is True, f"Expected valid address, got: {err}"


# ── validate_name ─────────────────────────────────────────────────────────────

class TestValidateName:

    def test_empty_name_rejected(self):
        ok, err = validate_name("")
        assert ok is False
        assert "required" in err.lower()

    def test_whitespace_only_rejected(self):
        ok, err = validate_name("   ")
        assert ok is False

    def test_single_char_rejected(self):
        ok, err = validate_name("A")
        assert ok is False
        assert "2 characters" in err

    def test_digits_only_rejected(self):
        ok, err = validate_name("123")
        assert ok is False
        assert "letter" in err.lower()

    def test_valid_simple_name(self):
        ok, err = validate_name("Péter")
        assert ok is True
        assert err is None

    def test_valid_two_chars(self):
        ok, err = validate_name("Li")
        assert ok is True

    def test_custom_field_name_in_error(self):
        ok, err = validate_name("", field_name="Last Name")
        assert ok is False
        assert "Last Name" in err

    def test_name_with_spaces_valid(self):
        ok, err = validate_name("Gábor Kiss")
        assert ok is True

    def test_name_with_hyphen_valid(self):
        ok, err = validate_name("Jean-Pierre")
        assert ok is True

    def test_name_with_digits_and_letters_valid(self):
        # Has at least one letter → passes
        ok, err = validate_name("R2D2")
        assert ok is True

    @pytest.mark.parametrize("name,field", [
        ("Anna", "First Name"),
        ("Kovács", "Last Name"),
        ("Gabi", "Nickname"),
    ])
    def test_parametrized_valid_names(self, name, field):
        ok, err = validate_name(name, field_name=field)
        assert ok is True, f"Expected valid for {name!r} ({field}), got: {err}"
