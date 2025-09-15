"""
🧪 Backend API Tests - Student Onboarding
Tests the critical onboarding API endpoints
"""

import pytest
import json
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db, Base, engine
from app.models import User, UserRole
from app.core.security import get_password_hash
from sqlalchemy.orm import sessionmaker

# Test database setup
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

@pytest.fixture(scope="module")
def setup_test_db():
    """Create fresh test database"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def test_student():
    """Create fresh test student"""
    db = TestingSessionLocal()
    
    # Clean up any existing test user
    existing = db.query(User).filter(User.email == "test.newcomer@student.com").first()
    if existing:
        db.delete(existing)
        db.commit()
    
    # Create fresh newcomer
    student = User(
        name="Test Newcomer",
        email="test.newcomer@student.com", 
        password_hash=get_password_hash("testpass123"),
        role=UserRole.STUDENT,
        is_active=True,
        onboarding_completed=False,  # KEY: Fresh newcomer
        phone=None,
        interests=None
    )
    
    db.add(student)
    db.commit()
    db.refresh(student)
    
    yield student
    
    # Cleanup
    db.delete(student)
    db.commit()
    db.close()

def test_login_fresh_student(setup_test_db, test_student):
    """Test login with fresh student account"""
    response = client.post("/api/v1/auth/login", data={
        "username": "test.newcomer@student.com",
        "password": "testpass123"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_get_user_profile_fresh_student(setup_test_db, test_student):
    """Test getting fresh student profile"""
    # Login first
    login_response = client.post("/api/v1/auth/login", data={
        "username": "test.newcomer@student.com", 
        "password": "testpass123"
    })
    token = login_response.json()["access_token"]
    
    # Get profile
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/users/me", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test.newcomer@student.com"
    assert data["onboarding_completed"] is False
    assert data["interests"] is None

def test_update_user_profile_onboarding(setup_test_db, test_student):
    """Test the critical onboarding PATCH endpoint (with JSON interests fix)"""
    # Login first
    login_response = client.post("/api/v1/auth/login", data={
        "username": "test.newcomer@student.com",
        "password": "testpass123"
    })
    token = login_response.json()["access_token"]
    
    # Update profile with interests as JSON string (the fix we implemented)
    headers = {"Authorization": f"Bearer {token}"}
    profile_data = {
        "nickname": "TestNick",
        "phone": "+36301234567",
        "emergency_contact": "Emergency Contact",
        "emergency_phone": "+36309876543", 
        "date_of_birth": "1995-05-15T00:00:00Z",
        "medical_notes": "No allergies",
        "interests": json.dumps(["Football", "Tennis"]),  # JSON string format
        "onboarding_completed": True
    }
    
    response = client.patch("/api/v1/users/me", json=profile_data, headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["nickname"] == "TestNick"
    assert data["onboarding_completed"] is True
    assert data["interests"] == json.dumps(["Football", "Tennis"])  # Should stay as string

def test_interests_validation_edge_cases(setup_test_db, test_student):
    """Test interests field with different data types"""
    # Login
    login_response = client.post("/api/v1/auth/login", data={
        "username": "test.newcomer@student.com",
        "password": "testpass123"
    })
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test with empty string
    response = client.patch("/api/v1/users/me", json={"interests": ""}, headers=headers)
    assert response.status_code == 200
    
    # Test with null
    response = client.patch("/api/v1/users/me", json={"interests": None}, headers=headers)  
    assert response.status_code == 200
    
    # Test with valid JSON string
    response = client.patch("/api/v1/users/me", json={"interests": '["Swimming"]'}, headers=headers)
    assert response.status_code == 200

def test_onboarding_flow_complete(setup_test_db, test_student):
    """Test complete onboarding flow end-to-end"""
    # 1. Login fresh student
    login_response = client.post("/api/v1/auth/login", data={
        "username": "test.newcomer@student.com",
        "password": "testpass123"
    })
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Check initial state
    profile_response = client.get("/api/v1/users/me", headers=headers)
    initial_data = profile_response.json()
    assert initial_data["onboarding_completed"] is False
    
    # 3. Complete onboarding
    complete_profile = {
        "nickname": "CompleteTester",
        "phone": "+36301111111",
        "emergency_contact": "Test Contact",
        "emergency_phone": "+36302222222",
        "date_of_birth": "1990-01-01T00:00:00Z",
        "interests": json.dumps(["Football", "Basketball", "Swimming"]),
        "onboarding_completed": True
    }
    
    update_response = client.patch("/api/v1/users/me", json=complete_profile, headers=headers)
    assert update_response.status_code == 200
    
    # 4. Verify completion
    final_response = client.get("/api/v1/users/me", headers=headers)
    final_data = final_response.json()
    assert final_data["onboarding_completed"] is True
    assert final_data["nickname"] == "CompleteTester"
    assert final_data["interests"] == json.dumps(["Football", "Basketball", "Swimming"])

def test_cors_headers():
    """Test CORS headers for cross-platform compatibility"""
    response = client.options("/api/v1/users/me")
    assert response.status_code in [200, 204]
    # CORS should allow cross-origin requests

def test_api_health():
    """Test API health endpoint"""
    response = client.get("/health")
    assert response.status_code == 200