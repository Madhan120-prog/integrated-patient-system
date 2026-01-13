"""
DocAssist API Tests - Voice AI Clinical Assistant
Tests for:
- Login endpoint
- Patient search
- Deep query (AI-powered clinical assistant)
- Data initialization
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestHealthAndAuth:
    """Health check and authentication tests"""
    
    def test_api_root(self):
        """Test API root endpoint"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "United Patient Record System API" in data["message"]
        print(f"✓ API root endpoint working: {data['message']}")
    
    def test_login_success(self):
        """Test successful login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/login", json={
            "username": "doctor",
            "password": "doctor123"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "user" in data
        assert data["user"]["username"] == "doctor"
        assert data["user"]["role"] == "Doctor"
        print(f"✓ Login successful: {data['user']['name']} ({data['user']['role']})")
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/login", json={
            "username": "invalid",
            "password": "wrongpass"
        })
        assert response.status_code == 401
        print("✓ Invalid credentials correctly rejected with 401")
    
    def test_login_nurse(self):
        """Test login as nurse"""
        response = requests.post(f"{BASE_URL}/api/login", json={
            "username": "nurse",
            "password": "nurse123"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["role"] == "Nurse"
        print(f"✓ Nurse login successful: {data['user']['name']}")


class TestDataInitialization:
    """Test data initialization endpoints"""
    
    def test_init_data(self):
        """Test data initialization endpoint"""
        response = requests.post(f"{BASE_URL}/api/init-data")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        # Either data already exists or was created
        assert "patients_created" in data or "Data already exists" in data.get("message", "")
        print(f"✓ Data initialization: {data['message']}")
    
    def test_get_all_patients(self):
        """Test getting all patients list"""
        response = requests.get(f"{BASE_URL}/api/patients")
        assert response.status_code == 200
        data = response.json()
        assert "patients" in data
        assert len(data["patients"]) > 0
        print(f"✓ Retrieved {len(data['patients'])} patients")
        # Verify patient structure
        patient = data["patients"][0]
        assert "patient_id" in patient
        assert "name" in patient


class TestPatientSearch:
    """Patient search functionality tests"""
    
    def test_search_by_patient_id(self):
        """Test searching patient by ID (P1002)"""
        response = requests.get(f"{BASE_URL}/api/search?term=P1002")
        assert response.status_code == 200
        data = response.json()
        
        # Verify profile exists
        assert data["profile"] is not None
        assert data["profile"]["patient_id"] == "P1002"
        print(f"✓ Found patient: {data['profile']['name']} (ID: {data['profile']['patient_id']})")
        
        # Verify profile structure
        profile = data["profile"]
        assert "name" in profile
        assert "age" in profile
        assert "gender" in profile
        assert "blood_group" in profile
        
        # Verify records structure
        assert "mri_records" in data
        assert "xray_records" in data
        assert "ecg_records" in data
        assert "treatment_records" in data
        assert "blood_profile_records" in data
        assert "ct_scan_records" in data
        
        # Count total records
        total_records = (
            len(data["mri_records"]) + 
            len(data["xray_records"]) + 
            len(data["ecg_records"]) + 
            len(data["treatment_records"]) + 
            len(data["blood_profile_records"]) + 
            len(data["ct_scan_records"])
        )
        print(f"✓ Patient has {total_records} total records across all departments")
    
    def test_search_nonexistent_patient(self):
        """Test searching for non-existent patient"""
        response = requests.get(f"{BASE_URL}/api/search?term=NONEXISTENT999")
        assert response.status_code == 200
        data = response.json()
        assert data["profile"] is None
        print("✓ Non-existent patient correctly returns null profile")
    
    def test_search_by_name_partial(self):
        """Test searching patient by partial name"""
        # First get a patient name
        patients_response = requests.get(f"{BASE_URL}/api/patients")
        patients = patients_response.json()["patients"]
        if patients:
            # Get first 3 characters of first patient's name
            partial_name = patients[0]["name"][:3]
            response = requests.get(f"{BASE_URL}/api/search?term={partial_name}")
            assert response.status_code == 200
            print(f"✓ Partial name search for '{partial_name}' returned results")


class TestDeepQuery:
    """DocAssist AI-powered deep query tests"""
    
    def test_deep_query_basic(self):
        """Test basic deep query with patient P1002"""
        response = requests.post(f"{BASE_URL}/api/deep-query", json={
            "patient_id": "P1002",
            "question": "What is the patient's medical history summary?"
        })
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "answer" in data
        assert "evidence" in data
        assert "matched_departments" in data
        
        # Verify answer is not empty
        assert len(data["answer"]) > 0
        print(f"✓ Deep query returned answer with {len(data['answer'])} characters")
        print(f"✓ Matched departments: {data['matched_departments']}")
        print(f"✓ Evidence cards: {len(data['evidence'])}")
    
    def test_deep_query_blood_specific(self):
        """Test deep query about blood tests"""
        response = requests.post(f"{BASE_URL}/api/deep-query", json={
            "patient_id": "P1002",
            "question": "What are the blood test results?"
        })
        assert response.status_code == 200
        data = response.json()
        
        assert "answer" in data
        # Blood-related query should match Blood Profile department
        if data["matched_departments"]:
            print(f"✓ Blood query matched departments: {data['matched_departments']}")
    
    def test_deep_query_treatment_specific(self):
        """Test deep query about treatments and medications"""
        response = requests.post(f"{BASE_URL}/api/deep-query", json={
            "patient_id": "P1002",
            "question": "What medications has the patient been prescribed?"
        })
        assert response.status_code == 200
        data = response.json()
        
        assert "answer" in data
        print(f"✓ Treatment query returned answer")
        if data["evidence"]:
            for ev in data["evidence"][:2]:
                if "medicines" in ev:
                    print(f"  - Evidence includes medicines: {ev.get('medicines', 'N/A')}")
    
    def test_deep_query_nonexistent_patient(self):
        """Test deep query with non-existent patient"""
        response = requests.post(f"{BASE_URL}/api/deep-query", json={
            "patient_id": "INVALID999",
            "question": "What is the patient's history?"
        })
        assert response.status_code == 404
        print("✓ Non-existent patient correctly returns 404")
    
    def test_deep_query_empty_question(self):
        """Test deep query with empty question"""
        response = requests.post(f"{BASE_URL}/api/deep-query", json={
            "patient_id": "P1002",
            "question": ""
        })
        # Should still work but return generic response
        # The API doesn't validate empty questions, so it should return 200
        assert response.status_code in [200, 400, 422]
        print(f"✓ Empty question handled with status {response.status_code}")


class TestPatientAnalytics:
    """Patient analytics endpoint tests"""
    
    def test_get_patient_analytics(self):
        """Test getting patient analytics"""
        response = requests.get(f"{BASE_URL}/api/analytics/P1002")
        assert response.status_code == 200
        data = response.json()
        
        # Verify analytics structure
        assert "total_visits" in data
        assert "total_tests" in data
        assert "departments_visited" in data
        assert "visit_timeline" in data
        assert "treatment_summary" in data
        assert "health_trend" in data
        assert "recent_results" in data
        
        print(f"✓ Analytics for P1002:")
        print(f"  - Total visits: {data['total_visits']}")
        print(f"  - Total tests: {data['total_tests']}")
        print(f"  - Health trend: {data['health_trend']}")
        print(f"  - Departments: {data['departments_visited']}")


class TestDepartmentRecords:
    """Department-specific record tests"""
    
    def test_get_mri_department(self):
        """Test getting MRI department records"""
        response = requests.get(f"{BASE_URL}/api/department/mri")
        assert response.status_code == 200
        data = response.json()
        assert "department" in data
        assert "records" in data
        assert "total" in data
        print(f"✓ MRI department has {data['total']} records")
    
    def test_get_xray_department(self):
        """Test getting X-Ray department records"""
        response = requests.get(f"{BASE_URL}/api/department/xray")
        assert response.status_code == 200
        data = response.json()
        print(f"✓ X-Ray department has {data['total']} records")
    
    def test_get_treatment_department(self):
        """Test getting Treatment department records"""
        response = requests.get(f"{BASE_URL}/api/department/treatment")
        assert response.status_code == 200
        data = response.json()
        print(f"✓ Treatment department has {data['total']} records")
        
        # Verify treatment records have medicines
        if data["records"]:
            record = data["records"][0]
            assert "medicines" in record
            print(f"  - Sample medicines: {record['medicines']}")
    
    def test_invalid_department(self):
        """Test getting invalid department"""
        response = requests.get(f"{BASE_URL}/api/department/invalid")
        assert response.status_code == 404
        print("✓ Invalid department correctly returns 404")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
