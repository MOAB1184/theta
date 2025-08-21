#!/usr/bin/env python3
"""
Test script for Scout Accelerator API
Run this script to test the basic API endpoints
"""

import requests
import json
import time

BASE_URL = "http://localhost:8001"

def test_root_endpoint():
    """Test the root endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"Root endpoint: {response.status_code}")
        print(f"Response: {response.json()}")
        return True
    except Exception as e:
        print(f"Root endpoint failed: {e}")
        return False

def test_docs_endpoint():
    """Test the API documentation endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/docs")
        print(f"Docs endpoint: {response.status_code}")
        return True
    except Exception as e:
        print(f"Docs endpoint failed: {e}")
        return False

def test_signup_endpoint():
    """Test user signup"""
    try:
        test_user = {
            "full_name": "Test Scout",
            "email": "test@example.com",
            "password": "testpassword123",
            "role": "scout",
            "troop_code": "ABC123"
        }

        response = requests.post(f"{BASE_URL}/auth/signup", json=test_user)
        print(f"Signup endpoint: {response.status_code}")
        if response.status_code == 200:
            print("Signup successful!")
            return response.json()
        else:
            print(f"Signup failed: {response.text}")
            return None
    except Exception as e:
        print(f"Signup endpoint failed: {e}")
        return None

def test_login_endpoint():
    """Test user login"""
    try:
        login_data = {
            "email": "scout@demo.com",
            "password": "demo123"
        }

        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        print(f"Login endpoint: {response.status_code}")
        if response.status_code == 200:
            print("Login successful!")
            return response.json()
        else:
            print(f"Login failed: {response.text}")
            return None
    except Exception as e:
        print(f"Login endpoint failed: {e}")
        return None

def test_protected_endpoint(token):
    """Test a protected endpoint"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/requirements/scout", headers=headers)
        print(f"Requirements endpoint: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Retrieved {len(data['requirements'])} scout requirements")
            return True
        else:
            print(f"Requirements failed: {response.text}")
            return False
    except Exception as e:
        print(f"Requirements endpoint failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing Scout Accelerator API")
    print("=" * 50)

    # Test basic endpoints
    print("\n1. Testing basic endpoints...")
    root_ok = test_root_endpoint()
    docs_ok = test_docs_endpoint()

    if not root_ok:
        print("❌ API server not running. Please start the server first:")
        print("   cd backend && python app.py")
        return

    # Test authentication
    print("\n2. Testing authentication...")
    login_result = test_login_endpoint()

    if login_result and 'access_token' in login_result:
        token = login_result['access_token']
        print(f"Got token: {token[:20]}...")

        # Test protected endpoint
        print("\n3. Testing protected endpoints...")
        protected_ok = test_protected_endpoint(token)

        if protected_ok:
            print("✅ All tests passed!")
        else:
            print("❌ Protected endpoint test failed")
    else:
        print("❌ Authentication test failed")

    print("\n📝 API Documentation available at:")
    print(f"   Swagger UI: {BASE_URL}/docs")
    print(f"   ReDoc: {BASE_URL}/redoc")

if __name__ == "__main__":
    main()
