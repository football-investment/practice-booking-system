"""
Unit tests for app/api/api_v1/endpoints/certificates.py.

Targets 70% branch coverage gap on all 5 endpoint functions.
Endpoints are synchronous (def not async def) — call directly.
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from app.api.api_v1.endpoints import certificates as cert_module


_BASE = "app.api.api_v1.endpoints.certificates"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _user(role: str = "student") -> MagicMock:
    u = MagicMock()
    u.id = 42
    u.role = MagicMock()
    u.role.value = role
    return u


def _mock_cert(cert_id: str = "cert-123") -> MagicMock:
    cert = MagicMock()
    cert.id = cert_id
    cert.unique_identifier = "UNIQUE-001"
    cert.template.track.name = "Football Pro"
    cert.template.track.code = "FP"
    cert.issue_date = "2026-01-01"
    cert.completion_date = "2026-03-01"
    cert.cert_metadata = {"final_grade": 95}
    cert.verification_url = "https://verify.lfa.com/UNIQUE-001"
    cert.is_revoked = False
    return cert


# ---------------------------------------------------------------------------
# GET /my — get_my_certificates
# ---------------------------------------------------------------------------

class TestGetMyCertificates:

    def test_returns_empty_list_when_no_certs(self):
        mock_svc = MagicMock()
        mock_svc.get_user_certificates.return_value = []

        with patch(f"{_BASE}.CertificateService", return_value=mock_svc):
            result = cert_module.get_my_certificates(
                current_user=_user("student"),
                db=MagicMock()
            )

        assert result == []

    def test_returns_mapped_cert_data(self):
        cert = _mock_cert("cert-abc")
        mock_svc = MagicMock()
        mock_svc.get_user_certificates.return_value = [cert]

        with patch(f"{_BASE}.CertificateService", return_value=mock_svc):
            result = cert_module.get_my_certificates(
                current_user=_user("student"),
                db=MagicMock()
            )

        assert len(result) == 1
        assert result[0]["id"] == "cert-abc"
        assert result[0]["track_code"] == "FP"


# ---------------------------------------------------------------------------
# GET /{id}/download — download_certificate_pdf
# ---------------------------------------------------------------------------

class TestDownloadCertificatePdf:

    def test_non_owner_non_admin_raises_403(self):
        mock_svc = MagicMock()
        mock_svc.get_user_certificates.return_value = [_mock_cert("cert-other")]

        with patch(f"{_BASE}.CertificateService", return_value=mock_svc):
            with pytest.raises(HTTPException) as exc_info:
                cert_module.download_certificate_pdf(
                    certificate_id="cert-owned-by-someone-else",
                    current_user=_user("student"),
                    db=MagicMock()
                )

        assert exc_info.value.status_code == 403

    def test_admin_bypasses_ownership_check(self):
        mock_svc = MagicMock()
        # Admin does NOT own cert-999, but role="admin"
        mock_svc.get_user_certificates.return_value = [_mock_cert("cert-owned-by-other")]
        mock_svc.generate_certificate_pdf.return_value = b"%PDF-1.4"

        with patch(f"{_BASE}.CertificateService", return_value=mock_svc):
            result = cert_module.download_certificate_pdf(
                certificate_id="cert-999",
                current_user=_user("admin"),
                db=MagicMock()
            )

        assert result.media_type == "application/pdf"

    def test_download_success_returns_pdf_response(self):
        cert = _mock_cert("cert-xyz")
        mock_svc = MagicMock()
        mock_svc.get_user_certificates.return_value = [cert]
        mock_svc.generate_certificate_pdf.return_value = b"%PDF-1.4 content"

        with patch(f"{_BASE}.CertificateService", return_value=mock_svc):
            result = cert_module.download_certificate_pdf(
                certificate_id="cert-xyz",
                current_user=_user("student"),
                db=MagicMock()
            )

        assert result.media_type == "application/pdf"
        assert b"%PDF" in result.body

    def test_valueerror_raises_404(self):
        cert = _mock_cert("cert-xyz")
        mock_svc = MagicMock()
        mock_svc.get_user_certificates.return_value = [cert]
        mock_svc.generate_certificate_pdf.side_effect = ValueError("not found")

        with patch(f"{_BASE}.CertificateService", return_value=mock_svc):
            with pytest.raises(HTTPException) as exc_info:
                cert_module.download_certificate_pdf(
                    certificate_id="cert-xyz",
                    current_user=_user("student"),
                    db=MagicMock()
                )

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# POST /{id}/revoke — revoke_certificate
# ---------------------------------------------------------------------------

class TestRevokeCertificate:

    def test_non_admin_raises_403(self):
        with pytest.raises(HTTPException) as exc_info:
            cert_module.revoke_certificate(
                certificate_id="cert-123",
                reason="bad cert",
                current_user=_user("student"),
                db=MagicMock()
            )

        assert exc_info.value.status_code == 403

    def test_admin_revoke_success(self):
        revoked = MagicMock()
        revoked.id = "cert-123"
        revoked.revoked_at = "2026-03-08T00:00:00"

        mock_svc = MagicMock()
        mock_svc.revoke_certificate.return_value = revoked

        with patch(f"{_BASE}.CertificateService", return_value=mock_svc):
            result = cert_module.revoke_certificate(
                certificate_id="cert-123",
                reason="fraud",
                current_user=_user("admin"),
                db=MagicMock()
            )

        assert result["certificate_id"] == str(revoked.id)
        assert "revoked_at" in result

    def test_valueerror_raises_404(self):
        mock_svc = MagicMock()
        mock_svc.revoke_certificate.side_effect = ValueError("cert not found")

        with patch(f"{_BASE}.CertificateService", return_value=mock_svc):
            with pytest.raises(HTTPException) as exc_info:
                cert_module.revoke_certificate(
                    certificate_id="bad-id",
                    reason="fraud",
                    current_user=_user("admin"),
                    db=MagicMock()
                )

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# GET /analytics — get_certificate_analytics
# ---------------------------------------------------------------------------

class TestGetCertificateAnalytics:

    def test_student_role_raises_403(self):
        with pytest.raises(HTTPException) as exc_info:
            cert_module.get_certificate_analytics(
                current_user=_user("student"),
                db=MagicMock()
            )

        assert exc_info.value.status_code == 403

    def test_admin_gets_analytics(self):
        mock_svc = MagicMock()
        mock_svc.get_certificate_analytics.return_value = {"total": 5}

        with patch(f"{_BASE}.CertificateService", return_value=mock_svc):
            result = cert_module.get_certificate_analytics(
                current_user=_user("admin"),
                db=MagicMock()
            )

        assert result == {"total": 5}

    def test_instructor_gets_analytics(self):
        mock_svc = MagicMock()
        mock_svc.get_certificate_analytics.return_value = {"total": 2}

        with patch(f"{_BASE}.CertificateService", return_value=mock_svc):
            result = cert_module.get_certificate_analytics(
                current_user=_user("instructor"),
                db=MagicMock()
            )

        assert result == {"total": 2}


# ---------------------------------------------------------------------------
# GET /public/verify/{uid} — public_certificate_verification_page
# ---------------------------------------------------------------------------

class TestPublicCertificateVerificationPage:

    def test_valid_certificate_returns_valid_html(self):
        mock_svc = MagicMock()
        mock_svc.verify_certificate.return_value = {
            "valid": True,
            "certificate_id": "cert-abc",
            "user_name": "John Doe",
            "track_name": "Football Pro",
            "track_code": "FP",
            "issue_date": "2026-01-01",
            "completion_date": "2026-03-01",
            "final_grade": 95,
            "duration_days": 60,
            "verification_hash": "abc123def456abc123def456",
        }

        with patch(f"{_BASE}.CertificateService", return_value=mock_svc):
            result = cert_module.public_certificate_verification_page(
                unique_identifier="UNIQUE-001",
                db=MagicMock()
            )

        assert result.media_type == "text/html"
        assert b"Certificate Valid" in result.body or b"verified" in result.body.lower()

    def test_invalid_certificate_returns_invalid_html(self):
        mock_svc = MagicMock()
        mock_svc.verify_certificate.return_value = {
            "valid": False,
            "error": "Certificate not found",
        }

        with patch(f"{_BASE}.CertificateService", return_value=mock_svc):
            result = cert_module.public_certificate_verification_page(
                unique_identifier="BAD-ID",
                db=MagicMock()
            )

        assert result.media_type == "text/html"
        assert b"Invalid" in result.body or b"invalid" in result.body.lower()
