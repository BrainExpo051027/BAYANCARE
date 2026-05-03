from flask import Blueprint, request, jsonify, session
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.models.user import User

auth_bp = Blueprint("auth_routes", __name__)

@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    role = data.get("role", "RESIDENT")

    if User.query.filter_by(username=username).first():
        return {"error": "Username already exists"}, 400
    if User.query.filter_by(email=email).first():
        return {"error": "Email already exists"}, 400

    # BHW accounts require admin approval
    is_approved = True
    if role == "BHW":
        is_approved = False

    user = User(username=username, email=email, role=role, is_approved=is_approved)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    response_message = "User registered"
    if role == "BHW" and not is_approved:
        response_message += " (BHW account requires admin approval)"

    return {"message": response_message, "user_id": user.id, "is_approved": is_approved}, 201

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    remember = data.get("remember", False)

    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        # Check if user is approved (for BHW accounts)
        if not user.is_approved:
            return {"error": "Account pending admin approval"}, 403
        
        login_user(user, remember=remember)
        session["role"] = user.role.value  # optional: store role in session for quick checks
        return {"message": "Login successful", "user_id": user.id, "role": user.role.value}
    else:
        return {"error": "Invalid credentials"}, 401

@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    session.clear()
    return {"message": "Logged out"}

@auth_bp.route("/me", methods=["GET"])
@login_required
def me():
    return {
        "user_id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role.value
    }
