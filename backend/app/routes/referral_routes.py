from flask import Blueprint, request, jsonify, send_file, make_response
from flask_login import login_required, current_user
from app.extensions import db
from app.models.referral import ReferralSlip
from app.models.assessment import Assessment
from app.models.user import User
from app.models.health_profile import HealthProfile
from app.services.referral_service import generate_referral_code
from app.services.notification_service import notify_referral_generated
from app.utils.pdf_generator import generate_referral_pdf
from app.models.user import Role
from app.utils.decorators import role_required

referral_bp = Blueprint("referral_routes", __name__)

@referral_bp.route("", methods=["GET"])
@login_required
@role_required(Role.BHW, Role.ADMIN)
def list_referrals():
    barangay = request.args.get("barangay")
    query = ReferralSlip.query
    if barangay:
        query = query.join(Assessment).join(Assessment.user).filter(ReferralSlip.barangay == barangay)
    referrals = query.order_by(ReferralSlip.created_at.desc()).all()
    return jsonify([
        {
            "id": r.id,
            "assessment_id": r.assessment_id,
            "referral_code": r.referral_code,
            "referred_to_center": r.referred_to_center,
            "created_at": r.created_at.isoformat(),
            "status": r.status
        }
        for r in referrals
    ])


@referral_bp.route("/me", methods=["GET"])
@login_required
@role_required(Role.RESIDENT, Role.ADMIN)
def list_my_referrals():
    referrals = (
        ReferralSlip.query.join(Assessment)
        .filter(Assessment.user_id == current_user.id)
        .order_by(ReferralSlip.created_at.desc())
        .all()
    )
    return jsonify([
        {
            "id": r.id,
            "assessment_id": r.assessment_id,
            "referral_code": r.referral_code,
            "referred_to_center": r.referred_to_center,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "expires_at": r.expires_at.isoformat() if r.expires_at else None,
            "is_expired": r.is_expired() if hasattr(r, 'is_expired') else False,
            "status": r.status,
        }
        for r in referrals
    ])

@referral_bp.route("/generate/<int:assessment_id>", methods=["POST"])
@login_required
@role_required(Role.BHW, Role.ADMIN)
def create_referral(assessment_id):
    assessment = Assessment.query.get_or_404(assessment_id)
    data = request.get_json()
    referrals = ReferralSlip.query.filter_by(assessment_id=assessment.id).order_by(ReferralSlip.created_at.desc()).all()
    referral = ReferralSlip(
        assessment_id=assessment_id,
        referral_code=generate_referral_code(),
        referred_to_center=data.get("referred_to_center", "Barangay Health Center"),
        barangay=data.get("barangay", "Polomolok"),
        created_by=current_user.id
    )
    db.session.add(referral)
    db.session.commit()
    # Notify user
    notify_referral_generated(assessment.user, referral)
    return {"message": "Referral generated", "referral_code": referral.referral_code, "id": referral.id}, 201

@referral_bp.route("/<int:id>", methods=["GET"])
@login_required
def get_referral(id):
    """Get a single referral by ID. Residents can only view their own."""
    referral = ReferralSlip.query.get_or_404(id)
    assessment = referral.assessment
    
    # Access control: resident can only view their own referral
    if current_user.role.value == "RESIDENT" and assessment.user_id != current_user.id:
        return {"error": "Forbidden"}, 403
    
    return jsonify({
        "id": referral.id,
        "assessment_id": referral.assessment_id,
        "referral_code": referral.referral_code,
        "referred_to_center": referral.referred_to_center,
        "barangay": referral.barangay,
        "status": referral.status,
        "created_at": referral.created_at.isoformat() if referral.created_at else None,
        "expires_at": referral.expires_at.isoformat() if referral.expires_at else None,
        "is_expired": referral.is_expired() if hasattr(referral, 'is_expired') else False,
        "created_by_name": referral.creator.health_profile.full_name if referral.creator and referral.creator.health_profile else (referral.creator.username if referral.creator else "Unknown"),
        "user_id": assessment.user_id,
        "username": assessment.user.username
    })

@referral_bp.route("/<int:id>/status", methods=["PUT"])
@login_required
@role_required(Role.BHW, Role.ADMIN)
def update_referral_status(id):
    referral = ReferralSlip.query.get_or_404(id)
    data = request.get_json()
    referral.status = data.get("status")  # PENDING, ATTENDED, CLOSED
    db.session.commit()
    return {"message": "Referral status updated"}

@referral_bp.route("/<int:id>/download", methods=["GET"])
@login_required
def download_referral_pdf(id):
    referral = ReferralSlip.query.get_or_404(id)
    assessment = referral.assessment
    user = assessment.user
    # Access control: resident can only download their own referral
    if current_user.role.value == "RESIDENT" and assessment.user_id != current_user.id:
        return {"error": "Forbidden"}, 403
    
    # Check if referral is expired
    if hasattr(referral, 'is_expired') and referral.is_expired():
        return {"error": "This referral has expired and can no longer be downloaded. Please request a new consultation."}, 403
    
    health_profile = HealthProfile.query.filter_by(user_id=user.id).first()

    pdf_buffer = generate_referral_pdf(referral, assessment, user, health_profile)
    response = make_response(send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=f"referral_{referral.referral_code}.pdf",
        mimetype="application/pdf"
    ))
    return response
