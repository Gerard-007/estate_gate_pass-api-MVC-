import unittest
from app import app
from auth.views import *
from gate_pass.views import *
from pymongo import MongoClient
from datetime import datetime, timedelta
import jwt

class FlaskAppTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['JWT_SECRET_KEY'] = 'test_jwt_secret_key'
        self.app = app.test_client()


        self.client = MongoClient("mongodb://localhost:27017/")
        self.db = self.client["test_estate_db"]
        self.users = self.db["users"]
        self.estates = self.db["estates"]
        self.apartments = self.db["apartments"]
        self.visitor_tokens = self.db["visitor_tokens"]


        self.users.delete_many({})
        self.estates.delete_many({})
        self.apartments.delete_many({})
        self.visitor_tokens.delete_many({})

    def tearDown(self):
        self.db.drop_collection("users")
        self.db.drop_collection("visitor_tokens")

    def get_access_token(self, email="testuser@example.com", password="securepassword", status="Resident"):
        self.register_and_verify_user(email=email, password=password, status=status)

        response = self.app.post(
            "/api/auth/login",
            json={"email": email, "password": password}
        )
        data = response.get_json()
        return data["access_token"]

    def register_and_verify_user(self, email="testuser@example.com", password="securepassword", status="Resident"):
        self.app.post(
            "/api/auth/register",
            json={
                "fullname": "Test User",
                "email": email,
                "phone": "09123456789",
                "status": status
            }
        )

        user_data = {
            "email": email,
            "phone": "09123456789",
            "status": status
        }
        payload = {
            "user_data": user_data,
            "exp": datetime.now() + timedelta(days=2)
        }
        token = jwt.encode(payload, app.config['JWT_SECRET_KEY'], algorithm="HS256")

        self.app.post(
            f"/api/auth/verify/{token}",
            json={"password": password}
        )

    def test_register_user(self):
        response = self.app.post(
            "/api/auth/register",
            json={
                "fullname": "New User",
                "email": "newuser@example.com",
                "phone": "09123456789",
                "status": "Resident"
            }
        )
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data["message"], "Verification email sent.")

    def test_verify_email(self):
        self.app.post(
            "/api/auth/register",
            json={
                "fullname": "Verify User",
                "email": "verifyuser@example.com",
                "phone": "09123456789",
                "status": "Resident"
            }
        )

        # TODO: email should be sent here for verification
        user_data = {
            "email": "verifyuser@example.com",
            "phone": "09123456789",
            "status": "Resident"
        }

        payload = {
            "user_data": user_data,
            "exp": datetime.now() + timedelta(days=2)
        }

        token = jwt.encode(payload, app.config['JWT_SECRET_KEY'], algorithm="HS256")

        verify_response = self.app.post(
            f"/api/auth/verify/{token}",
            json={"password": "securepassword"}
        )
        self.assertEqual(verify_response.status_code, 200)
        data = verify_response.get_json()
        self.assertIn("access_token", data)
        self.assertIn("refresh_token", data)

    def test_login(self):
        self.register_and_verify_user(email="loginuser@example.com", password="securepassword")

        login_response = self.app.post(
            "/api/auth/login",
            json={"email": "loginuser@example.com", "password": "securepassword"}
        )
        self.assertEqual(login_response.status_code, 200)
        data = login_response.get_json()
        self.assertIn("access_token", data)
        self.assertIn("refresh_token", data)

    def test_generate_visitor_token(self):
        access_token = self.get_access_token(
            email="resident@example.com",
            password="residentpassword",
            status="Resident"
        )

        generate_response = self.app.post(
            "/api/gate_pass/generate_token",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "visitor_name": "John Doe",
                "visitor_phone": "+1234567890",
                "expiration": 60
            }
        )
        self.assertEqual(generate_response.status_code, 201)
        data = generate_response.get_json()
        self.assertIn("token_id", data)
        self.assertIn("expires_in", data)

    def test_validate_visitor_token(self):
        security_access_token = self.get_access_token(
            email="security@example.com",
            password="securitypassword",
            status="Security"
        )
        resident_access_token = self.get_access_token(
            email="resident@example.com",
            password="residentpassword",
            status="Resident"
        )

        generate_response = self.app.post(
            "/api/gate_pass/generate_token",
            headers={"Authorization": f"Bearer {resident_access_token}"},
            json={
                "visitor_name": "John Doe",
                "visitor_phone": "+1234567890",
                "expiration": 60
            }
        )
        self.assertEqual(generate_response.status_code, 201)
        token_data = generate_response.get_json()
        token_id = token_data["token_id"]

        validate_response = self.app.get(
            f"/api/gate_pass/validate_token/{token_id}",
            headers={"Authorization": f"Bearer {security_access_token}"}
        )
        self.assertEqual(validate_response.status_code, 200)
        validate_data = validate_response.get_json()
        self.assertEqual(validate_data["visitor_name"], "John Doe")


