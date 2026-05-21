from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from app.extensions import db
from app.models.consultation_request import ConsultationRequest, ConsultationStatus
from app.models.assessment import Assessment
from app.models.referral import ReferralSlip
from app.models.user import User, Role
from app.services.referral_service import generate_referral_code
from app.utils.decorators import role_required
from app.utils.bhw_scope import (
    can_bhw_access_consultation,
    deny_bhw_out_of_scope,
    filter_consultations_query_by_bhw_scope,
    is_admin_user,
)
from app.services.notification_service import notify_assessment_status_update, notify_referral_generated
from datetime import datetime
import json

consultation_bp = Blueprint("consultation_routes", __name__)


@consultation_bp.route("/request", methods=["POST"])
@login_required
@role_required(Role.RESIDENT)
def request_consultation():
    """
    Resident requests a consultation for a HIGH risk assessment.
    Creates a consultation request that BHWs/Admins can see and handle.
    """
    data = request.get_json()
    assessment_id = data.get("assessment_id")
    symptoms = data.get("symptoms", [])
    
    if not assessment_id:
        return {"error": "Assessment ID is required"}, 400
    
    # Verify the assessment exists and belongs to current user
    assessment = Assessment.query.filter_by(
        id=assessment_id, 
        user_id=current_user.id
    ).first_or_404()
    
    # Verify it's a HIGH risk assessment
    if assessment.risk_level.value != "HIGH":
        return {"error": "Consultation is only available for HIGH risk assessments"}, 400
    
    # Check if a consultation request already exists for this assessment
    existing = ConsultationRequest.query.filter_by(
        assessment_id=assessment_id,
        status=ConsultationStatus.PENDING
    ).first()
    
    if existing:
        return {
            "message": "Consultation request already exists",
            "consultation_id": existing.id,
            "status": existing.status.value
        }, 200
    
    # Create new consultation request
    consultation = ConsultationRequest(
        assessment_id=assessment_id,
        resident_id=current_user.id,
        symptoms=json.dumps(symptoms) if symptoms else None,
        risk_level=assessment.risk_level.value,
        status=ConsultationStatus.PENDING,
        notes=f"HIGH risk assessment. Resident requesting consultation."
    )
    
    db.session.add(consultation)
    db.session.commit()
    
    return {
        "message": "Consultation request submitted successfully",
        "consultation_id": consultation.id,
        "status": consultation.status.value,
        "requested_at": consultation.created_at.isoformat()
    }, 201


@consultation_bp.route("/pending", methods=["GET"])
@login_required
@role_required(Role.BHW, Role.ADMIN)
def get_pending_consultations():
    """
    Get all pending consultation requests for BHWs/Admins to handle.
    Returns list of consultations that need attention.
    """
    status_filter = request.args.get("status", "PENDING")
    
    query = ConsultationRequest.query
    
    if status_filter != "ALL":
        try:
            status_enum = ConsultationStatus[status_filter]
            query = query.filter(ConsultationRequest.status == status_enum)
        except KeyError:
            return {"error": f"Invalid status: {status_filter}"}, 400
    
    query = filter_consultations_query_by_bhw_scope(query)
    consultations = query.order_by(ConsultationRequest.created_at.desc()).all()
    
    return {
        "consultations": [c.to_dict() for c in consultations],
        "count": len(consultations),
        "filter": status_filter
    }, 200


@consultation_bp.route("/my-consultations", methods=["GET"])
@login_required
@role_required(Role.RESIDENT)
def get_my_consultations():
    """
    Get consultation requests for the current resident.
    """
    consultations = ConsultationRequest.query.filter_by(
        resident_id=current_user.id
    ).order_by(ConsultationRequest.created_at.desc()).all()
    
    return {
        "consultations": [c.to_dict() for c in consultations],
        "count": len(consultations)
    }, 200


@consultation_bp.route("/<int:consultation_id>/assign", methods=["POST"])
@login_required
@role_required(Role.BHW, Role.ADMIN)
def assign_consultation(consultation_id):
    """
    BHW/Admin assigns a consultation to themselves.
    """
    consultation = ConsultationRequest.query.get_or_404(consultation_id)

    if not is_admin_user() and not can_bhw_access_consultation(consultation):
        return deny_bhw_out_of_scope()
    
    if consultation.status != ConsultationStatus.PENDING:
        return {"error": f"Cannot assign consultation with status: {consultation.status.value}"}, 400
    
    consultation.assigned_bhw_id = current_user.id
    consultation.status = ConsultationStatus.ASSIGNED
    consultation.assigned_at = datetime.utcnow()
    
    db.session.commit()

    # Notify the resident that their assessment is being reviewed
    try:
        resident = User.query.get(consultation.resident_id)
        if resident:
            bhw_name = current_user.health_profile.full_name if (current_user.health_profile and current_user.health_profile.full_name) else current_user.username
            status_msg = (
                f"A Barangay Health Worker has reviewed your high-risk health assessment "
                f"and will follow up with you shortly. Please monitor your symptoms and "
                f"contact your BHW if your condition worsens."
            )
            notify_assessment_status_update(resident, consultation.assessment, status_msg, bhw_name=bhw_name)
    except Exception as e:
        current_app.logger.error(f"Failed to send assessment status email: {e}")
    
    return {
        "message": "Consultation assigned successfully",
        "consultation_id": consultation.id,
        "assigned_bhw": current_user.username,
        "status": consultation.status.value
    }, 200


@consultation_bp.route("/<int:consultation_id>/generate-referral", methods=["POST"])
@login_required
@role_required(Role.BHW, Role.ADMIN)
def generate_consultation_referral(consultation_id):
    """
    BHW/Admin generates a referral for a consultation.
    This is the manual referral generation after reviewing the consultation.
    """
    data = request.get_json()
    referred_to_center = data.get("referred_to_center", "Barangay Health Center")
    notes = data.get("notes", "")
    
    consultation = ConsultationRequest.query.get_or_404(consultation_id)

    if not is_admin_user() and not can_bhw_access_consultation(consultation):
        return deny_bhw_out_of_scope()
    
    # Verify the consultation is assigned to current user or user is admin
    if consultation.assigned_bhw_id != current_user.id and current_user.role != Role.ADMIN:
        return {"error": "You can only generate referrals for consultations assigned to you"}, 403
    
    if consultation.status != ConsultationStatus.ASSIGNED:
        return {"error": f"Cannot generate referral. Consultation must be ASSIGNED first. Current status: {consultation.status.value}"}, 400
    
    # Check if referral already exists
    if consultation.assessment.referral:
        return {
            "error": "Referral already exists for this assessment",
            "referral_id": consultation.assessment.referral.id,
            "referral_code": consultation.assessment.referral.referral_code
        }, 400
    
    # Get resident's barangay
    resident = User.query.get(consultation.resident_id)
    barangay = resident.health_profile.barangay if resident and resident.health_profile else "Unknown"
    
    from datetime import timedelta
    
    # Generate the referral
    referral = ReferralSlip(
        assessment_id=consultation.assessment_id,
        referral_code=generate_referral_code(),
        referred_to_center=referred_to_center,
        barangay=barangay,
        created_by=current_user.id,
        symptoms=consultation.symptoms,  # Include symptoms from consultation
        expires_at=datetime.utcnow() + timedelta(days=7),  # Valid for 7 days
        status="PENDING"
    )
    
    db.session.add(referral)
    
    # Mark consultation as completed
    consultation.status = ConsultationStatus.COMPLETED
    consultation.completed_at = datetime.utcnow()
    if notes:
        consultation.notes += f"\nReferral generated by {current_user.username}: {notes}"
    
    db.session.commit()

    # Notify the resident that a referral slip was generated
    try:
        resident = User.query.get(consultation.resident_id)
        if resident:
            notify_referral_generated(resident, referral)
    except Exception as e:
        current_app.logger.error(f"Failed to send referral notification email: {e}")
    
    # Get symptoms for display
    symptoms_list = []
    if consultation.symptoms:
        try:
            symptoms_list = json.loads(consultation.symptoms)
        except:
            symptoms_list = [consultation.symptoms]
    
    # Get BHW name for display
    if current_user.health_profile and current_user.health_profile.full_name:
        bhw_name = current_user.health_profile.full_name
    elif current_user.health_profile:
        # Construct from individual parts
        name_parts = []
        if current_user.health_profile.first_name:
            name_parts.append(current_user.health_profile.first_name)
        if current_user.health_profile.middle_name:
            name_parts.append(current_user.health_profile.middle_name)
        if current_user.health_profile.last_name:
            name_parts.append(current_user.health_profile.last_name)
        bhw_name = ' '.join(name_parts) if name_parts else current_user.username
    else:
        bhw_name = current_user.username
    
    return {
        "message": "Referral generated successfully",
        "referral_id": referral.id,
        "referral_code": referral.referral_code,
        "consultation_id": consultation.id,
        "created_by_name": bhw_name,
        "created_by_username": current_user.username,
        "symptoms": symptoms_list,
        "referred_to_center": referred_to_center,
        "barangay": barangay,
        "created_at": referral.created_at.isoformat() if referral.created_at else None,
        "expires_at": referral.expires_at.isoformat() if referral.expires_at else None,
        "valid_for_days": 7
    }, 201


@consultation_bp.route("/<int:consultation_id>", methods=["GET"])
@login_required
def get_consultation(consultation_id):
    """
    Get details of a specific consultation.
    Residents can only see their own, BHWs/Admins can see all.
    Includes full resident health profile for BHW/Admin.
    """
    from datetime import datetime
    
    consultation = ConsultationRequest.query.get_or_404(consultation_id)
    
    # Check permissions
    if current_user.role == Role.RESIDENT and consultation.resident_id != current_user.id:
        return {"error": "You can only view your own consultations"}, 403
    if current_user.role == Role.BHW and not can_bhw_access_consultation(consultation):
        return deny_bhw_out_of_scope()
    
    result = consultation.to_dict()
    
    # Include full resident health profile for BHW/Admin
    if current_user.role in [Role.BHW, Role.ADMIN]:
        resident = consultation.resident
        if resident and resident.health_profile:
            # Helper function to clean N/A values
            def clean_na(value):
                if value == 'N/A' or value == 'n/a' or value == '':
                    return None
                return value
            
            # Get full name - try full_name first, then construct from parts in "last, first, middle" format
            full_name = resident.health_profile.full_name
            if not full_name:
                # Construct from individual parts in "last, first, middle" format
                name_parts = []
                if resident.health_profile.last_name and resident.health_profile.last_name != 'N/A':
                    name_parts.append(resident.health_profile.last_name)
                if resident.health_profile.first_name and resident.health_profile.first_name != 'N/A':
                    name_parts.append(resident.health_profile.first_name)
                if resident.health_profile.middle_name and resident.health_profile.middle_name != 'N/A':
                    name_parts.append(resident.health_profile.middle_name)
                full_name = ', '.join(name_parts) if name_parts else resident.username
            
            result["resident_profile"] = {
                "full_name": full_name,
                "username": resident.username,
                "email": resident.email,
                "contact_number": clean_na(resident.health_profile.contact_number),
                "barangay": clean_na(resident.health_profile.barangay),
                "date_of_birth": resident.health_profile.date_of_birth.isoformat() if resident.health_profile.date_of_birth else None,
                "age": resident.health_profile.age,
                "sex": clean_na(resident.health_profile.sex),
                "address": clean_na(resident.health_profile.address),
                "emergency_contact_person": clean_na(resident.health_profile.emergency_contact_person),
                "emergency_contact_number": clean_na(resident.health_profile.emergency_contact_number),
                "blood_type": clean_na(resident.health_profile.blood_type),
                "allergies": clean_na(resident.health_profile.allergies),
                "chronic_conditions": clean_na(resident.health_profile.chronic_conditions)
            }
    
    # Include assessment details
    assessment = consultation.assessment
    if assessment:
        result["assessment"] = {
            "id": assessment.id,
            "predicted_condition": assessment.predicted_condition,
            "assessment_summary": assessment.assessment_summary,
            "temperature": assessment.temperature,
            "duration_days": assessment.duration_days,
            "created_at": assessment.created_at.isoformat() if assessment.created_at else None,
            "risk_level": assessment.risk_level.value if assessment.risk_level else None
        }
    
    # Include referral details if exists
    if consultation.assessment and consultation.assessment.referral:
        referral = consultation.assessment.referral
        # Get creator full name - try full_name first, then construct from parts
        if referral.creator and referral.creator.health_profile:
            if referral.creator.health_profile.full_name:
                creator_name = referral.creator.health_profile.full_name
            else:
                name_parts = []
                if referral.creator.health_profile.first_name:
                    name_parts.append(referral.creator.health_profile.first_name)
                if referral.creator.health_profile.middle_name:
                    name_parts.append(referral.creator.health_profile.middle_name)
                if referral.creator.health_profile.last_name:
                    name_parts.append(referral.creator.health_profile.last_name)
                creator_name = ' '.join(name_parts) if name_parts else referral.creator.username
        else:
            creator_name = "Unknown"
        
        result["referral"] = {
            "id": referral.id,
            "referral_code": referral.referral_code,
            "referred_to_center": referral.referred_to_center,
            "barangay": referral.barangay,
            "status": referral.status,
            "created_at": referral.created_at.isoformat() if referral.created_at else None,
            "expires_at": referral.expires_at.isoformat() if referral.expires_at else None,
            "is_expired": referral.is_expired() if hasattr(referral, 'is_expired') else False,
            "created_by_name": creator_name
        }
    
    return result, 200
