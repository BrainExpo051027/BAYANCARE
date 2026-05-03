from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models.user import User, Role
from app.models.health_profile import HealthProfile
from app.models.assessment import Assessment
from app.utils.decorators import role_required

profile_bp = Blueprint("profile_routes", __name__)

def clean_na_value(value):
    """Convert 'N/A' strings to None for better frontend handling"""
    if value == 'N/A' or value == 'n/a' or value == 'N/A' or value == '':
        return None
    return value


@profile_bp.route("/search", methods=["GET"])
@login_required
@role_required(Role.BHW, Role.ADMIN)
def search_users():
    q = (request.args.get("q") or "").strip()
    role_filter = request.args.get("role", "RESIDENT").upper()  # Default to RESIDENT only

    # Build query
    query = db.session.query(User).outerjoin(HealthProfile)
    
    # Always filter by role (default RESIDENT to exclude BHW/Admin)
    try:
        target_role = Role[role_filter]
        query = query.filter(User.role == target_role)
    except KeyError:
        # Invalid role, default to RESIDENT
        query = query.filter(User.role == Role.RESIDENT)
    
    # Apply search filter if provided
    if q:
        query = query.filter(
            db.or_(
                User.username.ilike(f"%{q}%"),
                User.email.ilike(f"%{q}%"),
                HealthProfile.barangay.ilike(f"%{q}%"),
                HealthProfile.full_name.ilike(f"%{q}%"),
            )
        )
    
    users = query.order_by(User.username.asc()).limit(50).all()

    results = []
    for user in users:
        profile = user.health_profile
        
        results.append(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role.value,
                "is_approved": user.is_approved,
                "barangay": clean_na_value(profile.barangay) if profile else None,
                # Return individual name fields instead of full_name
                "last_name": clean_na_value(profile.last_name) if profile else None,
                "first_name": clean_na_value(profile.first_name) if profile else None,
                "middle_name": clean_na_value(profile.middle_name) if profile else None,
                "contact_number": clean_na_value(profile.contact_number) if profile else None,
            }
        )

    return jsonify(results)

@profile_bp.route("/me", methods=["GET"])
@login_required
def get_my_profile():
    profile = HealthProfile.query.filter_by(user_id=current_user.id).first()
    
    # Clean N/A values
    def clean_na(value):
        if value == 'N/A' or value == 'n/a' or value == '':
            return None
        return value
    
    return jsonify({
        "user_id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role.value,
        # I. PERSONAL IDENTIFICATION
        "last_name": clean_na(profile.last_name) if profile else None,
        "first_name": clean_na(profile.first_name) if profile else None,
        "middle_name": clean_na(profile.middle_name) if profile else None,
        "date_of_birth": profile.date_of_birth.isoformat() if profile and profile.date_of_birth else None,
        "age": profile.age if profile else None,
        "sex": clean_na(profile.sex) if profile else None,
        "civil_status": clean_na(profile.civil_status) if profile else None,
        "address": clean_na(profile.address) if profile else None,
        "barangay": clean_na(profile.barangay) if profile else None,
        "contact_number": clean_na(profile.contact_number) if profile else None,
        "philhealth_id": clean_na(profile.philhealth_id) if profile else None,
        # II. MEDICAL HISTORY & SOCIAL DETERMINANTS
        "blood_type": clean_na(profile.blood_type) if profile else None,
        "pwd_id": clean_na(profile.pwd_id) if profile else None,
        "allergies": clean_na(profile.allergies) if profile else None,
        "chronic_conditions": clean_na(profile.chronic_conditions) if profile else None,
        "current_medications": clean_na(profile.current_medications) if profile else None,
        "lifestyle": clean_na(profile.lifestyle) if profile else None,
        "household_details": clean_na(profile.household_details) if profile else None,
        # III. PUBLIC HEALTH PROGRAM STATUS
        "covid_vaccination": clean_na(profile.covid_vaccination) if profile else None,
        "other_immunizations": clean_na(profile.other_immunizations) if profile else None,
        "maternal_child_health": clean_na(profile.maternal_child_health) if profile else None,
        # IV. EMERGENCY CONTACT INFO & CERTIFICATION
        "emergency_contact_person": clean_na(profile.emergency_contact_person) if profile else None,
        "emergency_contact_relationship": clean_na(profile.emergency_contact_relationship) if profile else None,
        "emergency_contact_number": clean_na(profile.emergency_contact_number) if profile else None,
        "processed_by_bhw": clean_na(profile.processed_by_bhw) if profile else None,
        "processed_date": profile.processed_date.isoformat() if profile and profile.processed_date else None
    })

@profile_bp.route("/me", methods=["PUT"])
@login_required
def update_my_profile():
    from datetime import datetime
    profile = HealthProfile.query.filter_by(user_id=current_user.id).first()
    data = request.get_json()
    if not profile:
        profile = HealthProfile(user_id=current_user.id)
        db.session.add(profile)
    
    # I. PERSONAL IDENTIFICATION
    profile.full_name = data.get("full_name", profile.full_name)
    profile.last_name = data.get("last_name", profile.last_name)
    profile.first_name = data.get("first_name", profile.first_name)
    profile.middle_name = data.get("middle_name", profile.middle_name)
    if data.get("date_of_birth"):
        profile.date_of_birth = datetime.fromisoformat(data["date_of_birth"]).date()
    profile.age = data.get("age", profile.age)
    profile.sex = data.get("sex", profile.sex)
    profile.civil_status = data.get("civil_status", profile.civil_status)
    profile.address = data.get("address", profile.address)
    profile.barangay = data.get("barangay", profile.barangay)
    profile.contact_number = data.get("contact_number", profile.contact_number)
    profile.philhealth_id = data.get("philhealth_id", profile.philhealth_id)
    
    # II. MEDICAL HISTORY & SOCIAL DETERMINANTS
    profile.blood_type = data.get("blood_type", profile.blood_type)
    profile.pwd_id = data.get("pwd_id", profile.pwd_id)
    profile.allergies = data.get("allergies", profile.allergies)
    profile.chronic_conditions = data.get("chronic_conditions", profile.chronic_conditions)
    profile.current_medications = data.get("current_medications", profile.current_medications)
    profile.lifestyle = data.get("lifestyle", profile.lifestyle)
    profile.household_details = data.get("household_details", profile.household_details)
    
    # III. PUBLIC HEALTH PROGRAM STATUS
    profile.covid_vaccination = data.get("covid_vaccination", profile.covid_vaccination)
    profile.other_immunizations = data.get("other_immunizations", profile.other_immunizations)
    profile.maternal_child_health = data.get("maternal_child_health", profile.maternal_child_health)
    
    # IV. EMERGENCY CONTACT INFO & CERTIFICATION
    profile.emergency_contact_person = data.get("emergency_contact_person", profile.emergency_contact_person)
    profile.emergency_contact_relationship = data.get("emergency_contact_relationship", profile.emergency_contact_relationship)
    profile.emergency_contact_number = data.get("emergency_contact_number", profile.emergency_contact_number)
    profile.processed_by_bhw = data.get("processed_by_bhw", profile.processed_by_bhw)
    if data.get("processed_date"):
        profile.processed_date = datetime.fromisoformat(data["processed_date"]).date()
    
    db.session.commit()
    return {"message": "Profile updated"}

@profile_bp.route("/me/history", methods=["GET"])
@login_required
def get_my_assessment_history():
    assessments = Assessment.query.filter_by(user_id=current_user.id).order_by(Assessment.created_at.desc()).all()
    return jsonify([
        {
            "id": a.id,
            "risk_level": a.risk_level.value,
            "assessment_summary": a.assessment_summary,
            "recommendations": a.recommendations,
            "predicted_condition": a.predicted_condition,
            "confidence_score": a.confidence_score,
            "home_care_plan": a.home_care_plan,
            "temperature": a.temperature,
            "duration_days": a.duration_days,
            "follow_up_required": a.follow_up_required,
            "follow_up_date": a.follow_up_date.isoformat() if a.follow_up_date else None,
            "status": a.status,
            "created_at": a.created_at.isoformat(),
            "symptoms": [s.symptom_name for s in a.symptoms],
            "referral_id": a.referral.id if a.referral else None,
            "referral_code": a.referral.referral_code if a.referral else None
        }
        for a in assessments
    ])

# BHW-only endpoints to view other profiles
@profile_bp.route("/<int:user_id>", methods=["GET"])
@login_required
@role_required(Role.BHW, Role.ADMIN)
def get_profile(user_id):
    user = User.query.get_or_404(user_id)
    profile = HealthProfile.query.filter_by(user_id=user_id).first()
    
    # Clean N/A values
    def clean_na(value):
        if value == 'N/A' or value == 'n/a' or value == '':
            return None
        return value
    
    return jsonify({
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role.value,
        # I. PERSONAL IDENTIFICATION
        "last_name": clean_na(profile.last_name) if profile else None,
        "first_name": clean_na(profile.first_name) if profile else None,
        "middle_name": clean_na(profile.middle_name) if profile else None,
        "date_of_birth": profile.date_of_birth.isoformat() if profile and profile.date_of_birth else None,
        "age": profile.age if profile else None,
        "sex": clean_na(profile.sex) if profile else None,
        "civil_status": clean_na(profile.civil_status) if profile else None,
        "address": clean_na(profile.address) if profile else None,
        "barangay": clean_na(profile.barangay) if profile else None,
        "contact_number": clean_na(profile.contact_number) if profile else None,
        "philhealth_id": clean_na(profile.philhealth_id) if profile else None,
        # II. MEDICAL HISTORY & SOCIAL DETERMINANTS
        "blood_type": clean_na(profile.blood_type) if profile else None,
        "pwd_id": clean_na(profile.pwd_id) if profile else None,
        "allergies": clean_na(profile.allergies) if profile else None,
        "chronic_conditions": clean_na(profile.chronic_conditions) if profile else None,
        "current_medications": clean_na(profile.current_medications) if profile else None,
        "lifestyle": clean_na(profile.lifestyle) if profile else None,
        "household_details": clean_na(profile.household_details) if profile else None,
        # III. PUBLIC HEALTH PROGRAM STATUS
        "covid_vaccination": clean_na(profile.covid_vaccination) if profile else None,
        "other_immunizations": clean_na(profile.other_immunizations) if profile else None,
        "maternal_child_health": clean_na(profile.maternal_child_health) if profile else None,
        # IV. EMERGENCY CONTACT INFO & CERTIFICATION
        "emergency_contact_person": clean_na(profile.emergency_contact_person) if profile else None,
        "emergency_contact_relationship": clean_na(profile.emergency_contact_relationship) if profile else None,
        "emergency_contact_number": clean_na(profile.emergency_contact_number) if profile else None,
        "processed_by_bhw": clean_na(profile.processed_by_bhw) if profile else None,
        "processed_date": profile.processed_date.isoformat() if profile and profile.processed_date else None
    })

@profile_bp.route("/<int:user_id>/history", methods=["GET"])
@login_required
@role_required(Role.BHW, Role.ADMIN)
def get_assessment_history(user_id):
    assessments = Assessment.query.filter_by(user_id=user_id).order_by(Assessment.created_at.desc()).all()
    return jsonify([
        {
            "id": a.id,
            "risk_level": a.risk_level.value,
            "assessment_summary": a.assessment_summary,
            "recommendations": a.recommendations,
            "temperature": a.temperature,
            "duration_days": a.duration_days,
            "follow_up_required": a.follow_up_required,
            "follow_up_date": a.follow_up_date.isoformat() if a.follow_up_date else None,
            "status": a.status,
            "created_at": a.created_at.isoformat(),
            "symptoms": [s.symptom_name for s in a.symptoms]
        }
        for a in assessments
    ])

@profile_bp.route("/<int:user_id>", methods=["PUT"])
@login_required
@role_required(Role.BHW, Role.ADMIN)
def update_profile(user_id):
    """BHW/Admin can update resident health profiles"""
    from datetime import datetime
    user = User.query.get_or_404(user_id)
    profile = HealthProfile.query.filter_by(user_id=user_id).first()
    data = request.get_json()
    
    if not profile:
        profile = HealthProfile(user_id=user_id)
        db.session.add(profile)
    
    # I. PERSONAL IDENTIFICATION
    profile.full_name = data.get("full_name", profile.full_name)
    profile.last_name = data.get("last_name", profile.last_name)
    profile.first_name = data.get("first_name", profile.first_name)
    profile.middle_name = data.get("middle_name", profile.middle_name)
    if data.get("date_of_birth"):
        profile.date_of_birth = datetime.fromisoformat(data["date_of_birth"]).date()
    profile.age = data.get("age", profile.age)
    profile.sex = data.get("sex", profile.sex)
    profile.civil_status = data.get("civil_status", profile.civil_status)
    profile.address = data.get("address", profile.address)
    profile.barangay = data.get("barangay", profile.barangay)
    profile.contact_number = data.get("contact_number", profile.contact_number)
    profile.philhealth_id = data.get("philhealth_id", profile.philhealth_id)
    
    # II. MEDICAL HISTORY & SOCIAL DETERMINANTS
    profile.blood_type = data.get("blood_type", profile.blood_type)
    profile.pwd_id = data.get("pwd_id", profile.pwd_id)
    profile.allergies = data.get("allergies", profile.allergies)
    profile.chronic_conditions = data.get("chronic_conditions", profile.chronic_conditions)
    profile.current_medications = data.get("current_medications", profile.current_medications)
    profile.lifestyle = data.get("lifestyle", profile.lifestyle)
    profile.household_details = data.get("household_details", profile.household_details)
    
    # III. PUBLIC HEALTH PROGRAM STATUS
    profile.covid_vaccination = data.get("covid_vaccination", profile.covid_vaccination)
    profile.other_immunizations = data.get("other_immunizations", profile.other_immunizations)
    profile.maternal_child_health = data.get("maternal_child_health", profile.maternal_child_health)
    
    # IV. EMERGENCY CONTACT INFO & CERTIFICATION
    profile.emergency_contact_person = data.get("emergency_contact_person", profile.emergency_contact_person)
    profile.emergency_contact_relationship = data.get("emergency_contact_relationship", profile.emergency_contact_relationship)
    profile.emergency_contact_number = data.get("emergency_contact_number", profile.emergency_contact_number)
    profile.processed_by_bhw = data.get("processed_by_bhw", profile.processed_by_bhw)
    if data.get("processed_date"):
        profile.processed_date = datetime.fromisoformat(data["processed_date"]).date()
    
    db.session.commit()
    return {"message": "Profile updated successfully"}
