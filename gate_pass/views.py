import random
import string
from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from humanfriendly import format_timespan

from auth.models import User
from gate_pass.models import VisitorToken

gate_pass_view = Blueprint('gate_pass', __name__)


@gate_pass_view.route("/generate_gate_pass", methods=["POST"])
@jwt_required()
def generate_gate_pass():
    current_user = get_jwt_identity()
    user = User.objects(email=current_user).first()
    if not user or user.status not in ["Resident", "Admin"]:
        return jsonify({"error": "Unauthorized"}), 403

    data = request.json
    required_fields = ["visitor_name", "visitor_phone", "expiration"]
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    try:
        expiration_minutes = int(data["expiration"])
        if expiration_minutes <= 0:
            raise ValueError()
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid expiration value"}), 400

    VisitorToken.objects(resident=user, is_active=True).delete()

    token_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    expires_at = datetime.now() + timedelta(minutes=expiration_minutes)

    token = VisitorToken(
        token_id=token_id,
        visitor_name=data["visitor_name"],
        visitor_phone=data["visitor_phone"],
        expires_at=expires_at,
        resident=user,
        is_active=True
    ).save()

    return jsonify({
        "token_id": token_id,
        "expires_in": format_timespan(expiration_minutes * 60)
    }), 201


@gate_pass_view.route("/validate_gate_pass/<token_id>", methods=["GET"])
@jwt_required()
def validate_gate_pass(token_id):
    auth_user = get_jwt_identity()
    current_user = User.objects(email=auth_user).first()
    if current_user.status != "Security":
        return jsonify({"error": "Unauthorized"}), 403

    token = VisitorToken.objects(token_id=token_id, is_active=True).first()
    if not token:
        return jsonify({"error": "Token not found or already invalidated"}), 404

    if datetime.now() > token.expires_at:
        return jsonify({"error": "Token has expired"}), 410

    return jsonify({
        "visitor_name": token.visitor_name,
        "visitor_phone": token.visitor_phone,
        "expires_at": token.expires_at.isoformat(),
        "purpose": token.purpose
    }), 200


@gate_pass_view.route("/generate_exit_gate_pass/<token_id>", methods=["POST"])
@jwt_required()
def generate_exit_gate_pass(token_id):
    current_user = get_jwt_identity()
    user = User.objects(email=current_user).first()
    if not user or user.status not in ["Resident", "Admin"]:
        return jsonify({"error": "Unauthorized"}), 403

    token = VisitorToken.objects(token_id=token_id, is_active=True).first()
    if not token or str(token.resident.id) != user.id:
        return jsonify({"error": "Token not found or already invalidated"}), 404

    token.update(set__is_active=False)

    exit_token_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    exit_expires_at = datetime.now() + timedelta(minutes=15)

    exit_token = VisitorToken(
        token_id=exit_token_id,
        visitor_name=token.visitor_name,
        visitor_phone=token.visitor_phone,
        expires_at=exit_expires_at,
        resident=user,
        is_active=True,
        purpose="exit"
    ).save()

    time_to_expire = format_timespan(15 * 60)
    return jsonify({
        "exit_token_id": exit_token_id,
        "expires_in": time_to_expire
    }), 201
