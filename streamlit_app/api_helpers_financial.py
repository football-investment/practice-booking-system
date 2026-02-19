"""
Financial Management API Helper Functions
Functions for coupons, invoices, and payment verification
Bearer token authentication (CSRF-safe)
"""

import requests
from typing import Tuple, Optional, List, Dict
from config import API_BASE_URL, API_TIMEOUT


# ========================================
# COUPON MANAGEMENT
# ========================================

def validate_coupon(token: str, coupon_code: str) -> Tuple[bool, str, dict]:
    """
    Validate coupon code and get discount info (for student use)

    Args:
        token: Authentication token
        coupon_code: Coupon code to validate

    Returns:
        (success: bool, error: str, data: dict)
        data = {
            "code": str,
            "type": "PERCENTAGE" | "FIXED_AMOUNT" | "CREDITS",
            "discount_value": float,
            "description": str,
            "valid": bool
        }
    """
    try:
        response = requests.post(  # POST endpoint!
            f"{API_BASE_URL}/api/v1/coupons/validate/{coupon_code}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            return True, "", response.json()
        elif response.status_code == 404:
            return False, "Coupon not found", {}
        elif response.status_code == 400:
            error_detail = response.json().get("detail", "Coupon is not valid")
            return False, error_detail, {}
        else:
            return False, "Failed to validate coupon", {}

    except Exception as e:
        return False, f"Error: {str(e)}", {}


def apply_coupon(token: str, coupon_code: str) -> Tuple[bool, str, dict]:
    """
    Apply BONUS_CREDITS coupon to user account (instant redemption)

    Args:
        token: Authentication token
        coupon_code: Coupon code to apply

    Returns:
        (success: bool, error: str, data: dict)
        data = {
            "message": str,
            "coupon_code": str,
            "coupon_type": str,
            "credits_awarded": int,
            "new_balance": int
        }
    """
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/coupons/apply",
            headers={"Authorization": f"Bearer {token}"},
            json={"code": coupon_code},
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            return True, "", response.json()
        elif response.status_code == 404:
            error_detail = response.json().get("detail", {})
            if isinstance(error_detail, dict):
                error_msg = error_detail.get("message", "Coupon not found")
            else:
                error_msg = str(error_detail)
            return False, error_msg, {}
        elif response.status_code == 400:
            error_detail = response.json().get("detail", {})
            if isinstance(error_detail, dict):
                error_msg = error_detail.get("message", "Coupon is not valid")
            else:
                error_msg = str(error_detail)
            return False, error_msg, {}
        else:
            return False, "Failed to apply coupon", {}

    except Exception as e:
        return False, f"Error: {str(e)}", {}


def get_coupons(token: str) -> Tuple[bool, Optional[List[Dict]]]:
    """
    Get all coupons (admin only)
    Returns: (success, coupons_list)
    """
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/admin/coupons",
            headers={"Authorization": f"Bearer {token}"},
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            return True, response.json()
        else:
            print(f"Coupon API error: {response.status_code} - {response.text}")
            return False, None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching coupons: {e}")
        return False, None


def create_coupon(token: str, coupon_data: Dict) -> Tuple[bool, Optional[str], Optional[Dict]]:
    """
    Create a new coupon - uses Bearer token auth (not cookie)
    Returns: (success, error_message, coupon_dict)
    """
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/admin/coupons",
            headers={"Authorization": f"Bearer {token}"},  # Bearer token instead of cookie
            json=coupon_data,
            timeout=API_TIMEOUT
        )

        if response.status_code == 201:
            return True, None, response.json()
        else:
            error_msg = response.json().get('detail', 'Failed to create coupon')
            return False, error_msg, None
    except requests.exceptions.RequestException as e:
        return False, f"Request failed: {str(e)}", None


def update_coupon(token: str, coupon_id: int, coupon_data: Dict) -> Tuple[bool, Optional[str], Optional[Dict]]:
    """
    Update existing coupon
    Returns: (success, error_message, coupon_dict)
    """
    try:
        response = requests.put(
            f"{API_BASE_URL}/api/v1/admin/coupons/{coupon_id}",
            headers={"Authorization": f"Bearer {token}"},
            json=coupon_data,
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            return True, None, response.json()
        else:
            error_msg = response.json().get('detail', 'Failed to update coupon')
            return False, error_msg, None
    except requests.exceptions.RequestException as e:
        return False, f"Request failed: {str(e)}", None


def delete_coupon(token: str, coupon_id: int) -> Tuple[bool, Optional[str]]:
    """
    Delete coupon
    Returns: (success, error_message)
    """
    try:
        response = requests.delete(
            f"{API_BASE_URL}/api/v1/admin/coupons/{coupon_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=API_TIMEOUT
        )

        if response.status_code == 204:
            return True, None
        else:
            error_msg = response.json().get('detail', 'Failed to delete coupon')
            return False, error_msg
    except requests.exceptions.RequestException as e:
        return False, f"Request failed: {str(e)}"


def toggle_coupon_status(token: str, coupon_id: int) -> Tuple[bool, Optional[str], Optional[Dict]]:
    """
    Toggle coupon active status
    Returns: (success, error_message, coupon_dict)
    """
    try:
        # Toggle by updating is_active field (check backend endpoint)
        response = requests.put(
            f"{API_BASE_URL}/api/v1/admin/coupons/{coupon_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"is_active": None},  # Backend will toggle
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            return True, None, response.json()
        else:
            error_msg = response.json().get('detail', 'Failed to toggle coupon status')
            return False, error_msg, None
    except requests.exceptions.RequestException as e:
        return False, f"Request failed: {str(e)}", None


# ========================================
# INVOICE MANAGEMENT
# ========================================

def get_invoices(token: str, status_filter: Optional[str] = None) -> Tuple[bool, Optional[List[Dict]]]:
    """
    Get all invoice requests
    Returns: (success, invoices_list)
    """
    try:
        url = f"{API_BASE_URL}/api/v1/invoices/list"
        params = {}
        if status_filter:
            params['status'] = status_filter

        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            params=params,
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            return True, response.json()
        else:
            return False, None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching invoices: {e}")
        return False, None


def verify_invoice(token: str, invoice_id: int) -> Tuple[bool, Optional[str]]:
    """
    Verify (approve) invoice request
    Returns: (success, error_message)
    """
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/invoices/{invoice_id}/verify",
            headers={"Authorization": f"Bearer {token}"},
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            return True, None
        else:
            error_msg = response.json().get('detail', 'Failed to verify invoice')
            return False, error_msg
    except requests.exceptions.RequestException as e:
        return False, f"Request failed: {str(e)}"


def unverify_invoice(token: str, invoice_id: int) -> Tuple[bool, Optional[str]]:
    """
    Unverify (revert approval) invoice request
    Returns: (success, error_message)
    """
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/invoices/{invoice_id}/unverify",
            headers={"Authorization": f"Bearer {token}"},
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            return True, None
        else:
            error_msg = response.json().get('detail', 'Failed to unverify invoice')
            return False, error_msg
    except requests.exceptions.RequestException as e:
        return False, f"Request failed: {str(e)}"


def cancel_invoice(token: str, invoice_id: int) -> Tuple[bool, Optional[str]]:
    """
    Cancel invoice request
    Returns: (success, error_message)
    """
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/invoices/{invoice_id}/cancel",
            headers={"Authorization": f"Bearer {token}"},
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            return True, None
        else:
            error_msg = response.json().get('detail', 'Failed to cancel invoice')
            return False, error_msg
    except requests.exceptions.RequestException as e:
        return False, f"Request failed: {str(e)}"


# ========================================
# FINANCIAL SUMMARY
# ========================================

def get_financial_summary(token: str) -> Tuple[bool, Optional[Dict]]:
    """
    Get aggregated financial summary (admin only).
    Returns revenue, credit balances, and invoice statistics.
    """
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/invoices/summary",
            headers={"Authorization": f"Bearer {token}"},
            timeout=API_TIMEOUT
        )
        if response.status_code == 200:
            return True, response.json()
        return False, None
    except requests.exceptions.RequestException:
        return False, None


# ========================================
# PAYMENT VERIFICATION
# ========================================

def get_payment_verifications(token: str, verified: Optional[bool] = None) -> Tuple[bool, Optional[List[Dict]]]:
    """
    Get payment verification requests (students)
    Returns: (success, students_list)
    """
    try:
        url = f"{API_BASE_URL}/api/v1/payment-verification/students"

        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            students = response.json()
            # Filter by verified status if specified
            if verified is not None:
                students = [s for s in students if s.get('payment_verified') == verified]
            return True, students
        else:
            return False, None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching payment verifications: {e}")
        return False, None


def verify_payment(token: str, student_id: int, specializations: List[str]) -> Tuple[bool, Optional[str]]:
    """
    Verify payment for student
    Returns: (success, error_message)
    """
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/payment-verification/students/{student_id}/verify",
            headers={"Authorization": f"Bearer {token}"},
            json={"specializations": specializations},
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            return True, None
        else:
            error_msg = response.json().get('detail', 'Failed to verify payment')
            return False, error_msg
    except requests.exceptions.RequestException as e:
        return False, f"Request failed: {str(e)}"


def reject_payment(token: str, student_id: int) -> Tuple[bool, Optional[str]]:
    """
    Reject/unverify payment for student
    Returns: (success, error_message)
    """
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/payment-verification/students/{student_id}/unverify",
            headers={"Authorization": f"Bearer {token}"},
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            return True, None
        else:
            error_msg = response.json().get('detail', 'Failed to unverify payment')
            return False, error_msg
    except requests.exceptions.RequestException as e:
        return False, f"Request failed: {str(e)}"
