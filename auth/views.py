from datetime import datetime, timedelta
import jwt
from flask import request, jsonify
from flask import Blueprint
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
)
from werkzeug.security import check_password_hash, generate_password_hash
from auth.models import User
from helpers.db_config import Config
from helpers.utils import send_mail


auth_view = Blueprint('auth', __name__)


def get_user_by_email(email):
    return User.objects(email=email).first()


def verify_password(email, password):
    user = get_user_by_email(email)
    if user and check_password_hash(user.password, password):
        return user
    return None


@auth_view.route("/register", methods=["POST"])
def register():
    data = request.json
    try:
        fullname = data["fullname"]
        email = data["email"]
        phone = data["phone"]
        status = data.get("status", "Visitor")

        payload = {
            "user_data": {
                "fullname": fullname,
                "email": email,
                "phone": phone,
                "status": status
            },
            "exp": datetime.now() + timedelta(days=2)
        }
        token = jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm="HS256")
        verification_link = f"{Config.FRONTEND_URL}/api/auth/verify/{token}"
        print(f"Verification link: {verification_link}")

        try:
            send_mail(
                subject="Verify Your Email",
                body=f"Click this link to verify your email: {verification_link}",
                from_email="gerardnwazk@gmail.com",
                to_email=[email]
            )
        except Exception as e:
            print(e)
            return jsonify({"error": "Failed to send email"}), 500
        return jsonify({"message": "Verification email sent."}), 201

    except KeyError:
        return jsonify({"error": "Missing required fields"}), 400


@auth_view.route("/verify/<token>", methods=["POST"])
def verify(token):
    try:
        decoded = jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=["HS256"])
        user_data = decoded["user_data"]

        if datetime.now().timestamp() > decoded.get("exp", 0):
            return jsonify({"error": "Token expired."}), 400

        if User.objects(email=user_data["email"]).first():
            return jsonify({"error": "Email already registered."}), 400

        data = request.json
        password = data.get("password")
        if not password:
            return jsonify({"error": "Password is required for verification."}), 400

        hashed_password = generate_password_hash(password)
        user = User(
            fullname=user_data["fullname"],
            email=user_data["email"],
            phone=user_data["phone"],
            password=hashed_password,
            status=user_data.get("status", "Visitor"),
            is_active=True
        ).save()

        access_token = create_access_token(identity=user.email)
        refresh_token = create_refresh_token(identity=user.email)

        return jsonify({
            "access_token": access_token,
            "refresh_token": refresh_token
        }), 200

    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return jsonify({"error": "Invalid token."}), 400


@auth_view.route("/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    user = verify_password(email, password)
    if not user:
        return jsonify({"error": "Invalid credentials"}), 401

    access_token = create_access_token(identity=user.email, expires_delta=timedelta(days=1))
    refresh_token = create_refresh_token(identity=user.email)

    return jsonify({
        "access_token": access_token,
        "refresh_token": refresh_token
    }), 200
