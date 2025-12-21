"""
Financial Management API Helper Functions
Functions for coupons, invoices, and payment verification
"""

import requests
from typing import Tuple, Optional, List, Dict
from config import API_BASE_URL, API_TIMEOUT


# ========================================
# COUPON MANAGEMENT
# ========================================

def get_coupons(token: str) -> Tuple[bool, Optional[List[Dict]]]:
    """
    Get all coupons (admin only) - uses cookie auth
    Returns: (success, coupons_list)
    """
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/admin/coupons",
            cookies={"access_token": token},
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
    Create a new coupon - uses cookie auth
    Returns: (success, error_message, coupon_dict)
    """
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/admin/coupons",
            cookies={"access_token": token},
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
    Update existing coupon - uses cookie auth
    Returns: (success, error_message, coupon_dict)
    """
    try:
        response = requests.put(
            f"{API_BASE_URL}/api/v1/admin/coupons/{coupon_id}",
            cookies={"access_token": token},
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
    Toggle coupon active status - uses cookie auth + PUT method
    Returns: (success, error_message, coupon_dict)
    """
    try:
        # Toggle by updating is_active field (check backend endpoint)
        response = requests.put(
            f"{API_BASE_URL}/api/v1/admin/coupons/{coupon_id}",
            cookies={"access_token": token},
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
    Get all invoice requests - uses cookie auth
    Returns: (success, invoices_list)
    """
    try:
        url = f"{API_BASE_URL}/api/v1/invoices/list"
        params = {}
        if status_filter:
            params['status'] = status_filter

        response = requests.get(
            url,
            cookies={"access_token": token},
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
    Verify (approve) invoice request - uses cookie auth
    Returns: (success, error_message)
    """
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/invoices/{invoice_id}/verify",
            cookies={"access_token": token},
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
    Unverify (revert approval) invoice request - uses cookie auth
    Returns: (success, error_message)
    """
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/invoices/{invoice_id}/unverify",
            cookies={"access_token": token},
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
    Cancel invoice request - uses cookie auth
    Returns: (success, error_message)
    """
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/invoices/{invoice_id}/cancel",
            cookies={"access_token": token},
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
# PAYMENT VERIFICATION
# ========================================

def get_payment_verifications(token: str, verified: Optional[bool] = None) -> Tuple[bool, Optional[List[Dict]]]:
    """
    Get payment verification requests (students) - uses cookie auth
    Returns: (success, students_list)
    """
    try:
        url = f"{API_BASE_URL}/api/v1/payment-verification/students"

        response = requests.get(
            url,
            cookies={"access_token": token},
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
    Verify payment for student - uses cookie auth
    Returns: (success, error_message)
    """
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/payment-verification/students/{student_id}/verify",
            cookies={"access_token": token},
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
    Reject/unverify payment for student - uses cookie auth
    Returns: (success, error_message)
    """
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/payment-verification/students/{student_id}/unverify",
            cookies={"access_token": token},
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            return True, None
        else:
            error_msg = response.json().get('detail', 'Failed to unverify payment')
            return False, error_msg
    except requests.exceptions.RequestException as e:
        return False, f"Request failed: {str(e)}"
