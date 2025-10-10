"""
Certificate Management API endpoints
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session

from ....dependencies import get_current_user
from ....database import get_db
from ....models import User
from ....services.certificate_service import CertificateService, CertificateGenerationError
from ....schemas.certificate import (
    CertificateResponse, CertificateVerificationResponse,
    CertificateAnalyticsResponse
)

router = APIRouter()


@router.get("/my", response_model=List[CertificateResponse])
def get_my_certificates(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's certificates"""
    certificate_service = CertificateService(db)
    certificates = certificate_service.get_user_certificates(str(current_user.id))
    
    result = []
    for cert in certificates:
        cert_data = {
            "id": str(cert.id),
            "unique_identifier": cert.unique_identifier,
            "track_name": cert.template.track.name,
            "track_code": cert.template.track.code,
            "issue_date": cert.issue_date,
            "completion_date": cert.completion_date,
            "final_grade": cert.cert_metadata.get("final_grade"),
            "verification_url": cert.verification_url,
            "is_revoked": cert.is_revoked
        }
        result.append(cert_data)
    
    return result


@router.get("/verify/{unique_identifier}", response_model=CertificateVerificationResponse)
def verify_certificate(
    unique_identifier: str,
    db: Session = Depends(get_db)
):
    """Publicly verify a certificate by its unique identifier"""
    certificate_service = CertificateService(db)
    verification_result = certificate_service.verify_certificate(unique_identifier)
    
    return verification_result


@router.get("/{certificate_id}/download")
def download_certificate_pdf(
    certificate_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download certificate as PDF"""
    certificate_service = CertificateService(db)
    
    # Verify ownership or admin access
    certificates = certificate_service.get_user_certificates(str(current_user.id))
    user_certificate_ids = [str(cert.id) for cert in certificates]
    
    if certificate_id not in user_certificate_ids and current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this certificate"
        )
    
    try:
        pdf_content = certificate_service.generate_certificate_pdf(certificate_id)
        
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=certificate_{certificate_id}.pdf"}
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("/{certificate_id}/revoke")
def revoke_certificate(
    certificate_id: str,
    reason: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Revoke a certificate (admin only)"""
    if current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can revoke certificates"
        )
    
    certificate_service = CertificateService(db)
    
    try:
        revoked_certificate = certificate_service.revoke_certificate(certificate_id, reason)
        return {
            "message": "Certificate revoked successfully",
            "certificate_id": str(revoked_certificate.id),
            "revoked_at": revoked_certificate.revoked_at
        }
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/analytics", response_model=CertificateAnalyticsResponse)
def get_certificate_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get certificate analytics (admin/instructor only)"""
    if current_user.role.value not in ["admin", "instructor"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    
    certificate_service = CertificateService(db)
    analytics = certificate_service.get_certificate_analytics()
    
    return analytics


@router.get("/public/verify/{unique_identifier}")
def public_certificate_verification_page(
    unique_identifier: str,
    db: Session = Depends(get_db)
):
    """Public certificate verification page (returns HTML)"""
    certificate_service = CertificateService(db)
    verification_result = certificate_service.verify_certificate(unique_identifier)
    
    if verification_result["valid"]:
        # Generate HTML verification page
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Certificate Verification - LFA Academy</title>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
                .verified {{ color: green; }} .invalid {{ color: red; }}
                .cert-details {{ background: #f5f5f5; padding: 20px; margin: 20px 0; border-radius: 8px; }}
            </style>
        </head>
        <body>
            <h1>LFA Academy Certificate Verification</h1>
            <div class="verified">
                <h2>✅ Certificate Valid</h2>
                <div class="cert-details">
                    <p><strong>Certificate ID:</strong> {verification_result['certificate_id']}</p>
                    <p><strong>Recipient:</strong> {verification_result['user_name']}</p>
                    <p><strong>Track:</strong> {verification_result['track_name']} ({verification_result['track_code']})</p>
                    <p><strong>Issue Date:</strong> {verification_result['issue_date']}</p>
                    <p><strong>Completion Date:</strong> {verification_result['completion_date']}</p>
                    <p><strong>Final Grade:</strong> {verification_result['final_grade']}%</p>
                    <p><strong>Duration:</strong> {verification_result['duration_days']} days</p>
                </div>
                <p><small>Verification Hash: {verification_result['verification_hash'][:16]}...</small></p>
            </div>
        </body>
        </html>
        """
    else:
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Certificate Verification - LFA Academy</title>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
                .invalid {{ color: red; }}
            </style>
        </head>
        <body>
            <h1>LFA Academy Certificate Verification</h1>
            <div class="invalid">
                <h2>❌ Certificate Invalid</h2>
                <p><strong>Error:</strong> {verification_result.get('error', 'Unknown error')}</p>
            </div>
        </body>
        </html>
        """
    
    return Response(content=html_content, media_type="text/html")