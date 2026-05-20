from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from app.extensions import db
from app.models.assessment import Assessment, AssessmentSymptom, RiskLevel
from app.models.user import User, Role
from app.models.referral import ReferralSlip
from app.services.risk_engine import classify_risk, get_home_care_plan
from app.services.referral_service import generate_referral_code
from app.services.recovery_notification_service import RecoveryNotificationService
from app.utils.decorators import role_required
from datetime import datetime, timedelta

assessment_bp = Blueprint("assessment_routes", __name__)

@assessment_bp.route("", methods=["POST"])
@login_required
@role_required(Role.RESIDENT)
def create_assessment():
    data = request.get_json()
    # Use current_user.id; ignore user_id from payload for security
    user_id = current_user.id
    symptoms = data.get("symptoms", [])
    temperature = data.get("temperature")
    duration_days = data.get("duration_days")
    age = data.get("age")
    allergies = data.get("allergies", [])
    chronic_conditions = data.get("chronic_conditions", [])

    # Run risk engine (hybrid rule-based + ML-ready interface)
    (
        risk,
        summary,
        recommendations,
        follow_up_required,
        predicted_condition,
        confidence_score,
        has_medication_allergy,
    ) = classify_risk(
        symptoms, temperature, duration_days, age, allergies, chronic_conditions
    )

    # Create the assessment record
    assessment = Assessment(
        user_id=current_user.id,
        risk_level=risk,
        assessment_summary=summary,
        recommendations=recommendations,
        predicted_condition=predicted_condition,
        confidence_score=confidence_score,
        home_care_plan=get_home_care_plan(risk, symptoms, has_medication_allergy) if risk != RiskLevel.HIGH else None,
        temperature=temperature,
        duration_days=duration_days,
        follow_up_required=follow_up_required,
        follow_up_date=(datetime.utcnow() + timedelta(days=3)) if follow_up_required else None,
    )
    db.session.add(assessment)
    db.session.flush()  # get assessment.id

    # Save symptoms
    for symptom in symptoms:
        db.session.add(
            AssessmentSymptom(
                assessment_id=assessment.id,
                symptom_name=symptom,
                severity=None  # you can add severity later
            )
        )

    # Calculate and set recovery dates only for LOW/MODERATE risk
    if risk != RiskLevel.HIGH:
        recovery_start, recovery_end = RecoveryNotificationService.calculate_recovery_dates(
            risk, duration_days, symptoms
        )
        assessment.recovery_start_date = recovery_start
        assessment.recovery_end_date = recovery_end
    else:
        assessment.recovery_start_date = None
        assessment.recovery_end_date = None

    db.session.commit()

    # HIGH risk assessments now require consultation request instead of auto-referral
    consultation_required = False
    if risk == RiskLevel.HIGH:
        consultation_required = True

    return {
        "assessment_id": assessment.id,
        "risk_level": risk.value,
        "predicted_condition": predicted_condition,
        "confidence_score": confidence_score,
        "summary": summary,
        "recommendations": recommendations,
        "follow_up_required": follow_up_required,
        "follow_up_date": assessment.follow_up_date.isoformat() if assessment.follow_up_date else None,
        "recovery_start_date": assessment.recovery_start_date.isoformat() if assessment.recovery_start_date else None,
        "recovery_end_date": assessment.recovery_end_date.isoformat() if assessment.recovery_end_date else None,
        "consultation_required": consultation_required,
        "has_medication_allergy": has_medication_allergy,
        "home_care_plan": get_home_care_plan(risk, symptoms, has_medication_allergy) if risk != RiskLevel.HIGH else None,
        "symptoms": symptoms  # Include symptoms for consultation request
    }, 201


@assessment_bp.route("/<int:assessment_id>/similar", methods=["GET"])
@login_required
@role_required(Role.RESIDENT)
def get_similar_assessments(assessment_id):
    """
    Find past assessments with similar symptoms to help user review
    how they previously managed similar conditions.
    """
    target = Assessment.query.filter_by(id=assessment_id, user_id=current_user.id).first_or_404()
    target_symptoms = {s.symptom_name.lower() for s in target.symptoms}
    
    if not target_symptoms:
        return {"similar_assessments": [], "message": "No symptoms to compare"}
    
    # Get all user's past assessments (excluding current)
    past_assessments = Assessment.query.filter(
        Assessment.user_id == current_user.id,
        Assessment.id != assessment_id
    ).order_by(Assessment.created_at.desc()).all()
    
    similar = []
    for pa in past_assessments:
        pa_symptoms = {s.symptom_name.lower() for s in pa.symptoms}
        if not pa_symptoms:
            continue
        
        # Calculate symptom overlap
        common = target_symptoms & pa_symptoms
        total_unique = target_symptoms | pa_symptoms
        
        if common:
            similarity_score = len(common) / len(total_unique) if total_unique else 0
            # Include if at least 50% symptom overlap or 2+ symptoms match
            if similarity_score >= 0.5 or len(common) >= 2:
                similar.append({
                    "id": pa.id,
                    "created_at": pa.created_at.isoformat(),
                    "risk_level": pa.risk_level.value,
                    "symptoms": list(pa_symptoms),
                    "matching_symptoms": list(common),
                    "similarity_score": round(similarity_score, 2),
                    "recommendations": pa.recommendations,
                    "assessment_summary": pa.assessment_summary,
                    "has_referral": pa.referral is not None,
                    "follow_up_required": pa.follow_up_required
                })
    
    # Sort by similarity score (descending)
    similar.sort(key=lambda x: x["similarity_score"], reverse=True)
    
    return {
        "current_assessment_symptoms": list(target_symptoms),
        "similar_assessments": similar[:5],  # Top 5 most similar
        "count": len(similar)
    }


@assessment_bp.route("/<int:assessment_id>", methods=["DELETE"])
@login_required
@role_required(Role.RESIDENT)
def delete_assessment(assessment_id):
    assessment = Assessment.query.get_or_404(assessment_id)
    if assessment.user_id != current_user.id:
        return {"error": "Forbidden"}, 403
    try:
        # Delete related records first to avoid foreign key constraint violations
        from app.models.follow_up_notification import FollowUpNotification
        from app.models.consultation_request import ConsultationRequest
        from app.models.referral import ReferralSlip
        
        # Delete follow-up notifications
        FollowUpNotification.query.filter_by(assessment_id=assessment_id).delete()
        
        # Delete consultation requests related to this assessment
        ConsultationRequest.query.filter_by(assessment_id=assessment_id).delete()
        
        # Delete referrals related to this assessment
        ReferralSlip.query.filter_by(assessment_id=assessment_id).delete()
        
        # Delete assessment symptoms
        from app.models.assessment import AssessmentSymptom
        AssessmentSymptom.query.filter_by(assessment_id=assessment_id).delete()
        
        # Delete the assessment
        db.session.delete(assessment)
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Failed to delete assessment %s", assessment_id)
        return {"error": "Failed to delete assessment"}, 500
    return ("", 204)
