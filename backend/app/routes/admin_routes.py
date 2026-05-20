from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from app.extensions import db
from app.models.user import User, Role

admin_bp = Blueprint("admin_routes", __name__)

def require_admin():
    """Check if current user is admin"""
    if not current_user.is_authenticated or current_user.role != Role.ADMIN:
        return False
    return True

def require_admin_or_bhw():
    """Check if current user is admin or BHW"""
    if not current_user.is_authenticated or current_user.role not in [Role.ADMIN, Role.BHW]:
        return False
    return True

@admin_bp.route("/pending-bhw", methods=["GET"])
@login_required
def get_pending_bhw():
    """Get all pending BHW account approvals"""
    if not require_admin():
        return {"error": "Admin access required"}, 403
    
    pending_users = User.query.filter_by(role=Role.BHW, is_approved=False).all()
    
    return {
        "pending_users": [
            {
                "id": user.id,
                "username": user.username,
                "email": user.email
            }
            for user in pending_users
        ]
    }

@admin_bp.route("/approve-bhw/<int:user_id>", methods=["POST"])
@login_required
def approve_bhw(user_id):
    """Approve a BHW account"""
    if not require_admin():
        return {"error": "Admin access required"}, 403
    
    user = User.query.get_or_404(user_id)
    
    if user.role != Role.BHW:
        return {"error": "User is not a BHW"}, 400
    
    if user.is_approved:
        return {"error": "User is already approved"}, 400
    
    user.is_approved = True
    db.session.commit()
    
    return {"message": f"BHW account {user.username} approved successfully"}

@admin_bp.route("/reject-bhw/<int:user_id>", methods=["DELETE"])
@login_required
def reject_bhw(user_id):
    """Reject/delete a pending BHW account"""
    if not require_admin():
        return {"error": "Admin access required"}, 403
    
    user = User.query.get_or_404(user_id)
    
    if user.role != Role.BHW:
        return {"error": "User is not a BHW"}, 400
    
    if user.is_approved:
        return {"error": "Cannot delete approved user"}, 400
    
    db.session.delete(user)
    db.session.commit()
    
    return {"message": f"BHW account {user.username} rejected and deleted"}

@admin_bp.route("/all-users", methods=["GET"])
@login_required
def get_all_users():
    """Get all users (admin only)"""
    if not require_admin():
        return {"error": "Admin access required"}, 403
    
    users = User.query.all()
    
    return {
        "users": [
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role.value,
                "is_approved": user.is_approved
            }
            for user in users
        ]
    }


@admin_bp.route("/stats", methods=["GET"])
@login_required
def get_system_stats():
    """Get system statistics (admin and BHW)."""
    if not require_admin_or_bhw():
        return {"error": "Admin access required"}, 403

    from app.models.assessment import Assessment
    from app.models.referral import ReferralSlip
    from app.models.announcement import Announcement
    from app.models.follow_up_notification import FollowUpNotification, FollowUpStatus

    total_users = User.query.count()
    total_assessments = Assessment.query.count()
    total_referrals = ReferralSlip.query.count()
    active_announcements = Announcement.query.filter_by(status="ACTIVE").count()
    pending_bhw = User.query.filter_by(role=Role.BHW, is_approved=False).count()

    # Assessment status breakdown based on Assessment.status field
    all_assessments = Assessment.query.all()
    
    # Count by status - ignoring HIGH risk assessments as they are handled by professionals/hospitals via consultations
    resolved_count = sum(1 for a in all_assessments if a.status == 'RESOLVED' and (not a.risk_level or a.risk_level.value != 'HIGH'))
    needs_referral_clinic = sum(1 for a in all_assessments if a.status == 'REFERRED' and (not a.risk_level or a.risk_level.value != 'HIGH'))
    same_status_count = sum(1 for a in all_assessments if a.status == 'FOLLOW_UP' and (not a.risk_level or a.risk_level.value != 'HIGH'))
    open_no_recovery = sum(1 for a in all_assessments if a.status == 'OPEN' and a.recovery_end_date is None and (not a.risk_level or a.risk_level.value != 'HIGH'))
    open_with_recovery = sum(1 for a in all_assessments if a.status == 'OPEN' and a.recovery_end_date is not None and (not a.risk_level or a.risk_level.value != 'HIGH'))
    
    # Recovered = RESOLVED + OPEN assessments without recovery dates (completed normally)
    recovered_from_home_care = resolved_count + open_no_recovery
    
    # Pending = OPEN status with recovery dates (waiting for patient response)
    pending_response_count = open_with_recovery

    from app.models.consultation_request import ConsultationRequest, ConsultationStatus
    from sqlalchemy import or_
    # Count consultations that need a referral generated.
    # Using or_() with individual == comparisons is more reliable than .in_()
    # for SQLAlchemy Enum-typed columns.
    pending_consultations = ConsultationRequest.query.filter(
        or_(
            ConsultationRequest.status == ConsultationStatus.PENDING,
            ConsultationRequest.status == ConsultationStatus.ASSIGNED
        )
    ).count()
    # ASSIGNED-only: picked up by a BHW and actively awaiting referral generation
    needs_referral_now = ConsultationRequest.query.filter(
        ConsultationRequest.status == ConsultationStatus.ASSIGNED
    ).count()

    return {
        "total_users": total_users,
        "total_assessments": total_assessments,
        "total_referrals": total_referrals,
        "active_announcements": active_announcements,
        "pending_bhw": pending_bhw,
        "recovered_from_home_care": recovered_from_home_care,
        "needs_referral_clinic": needs_referral_clinic,
        "same_status_count": same_status_count,
        "pending_response_count": pending_response_count,
        "pending_consultations": pending_consultations,
        "needs_referral_now": needs_referral_now,
    }


@admin_bp.route("/users/<int:user_id>", methods=["DELETE"])
@login_required
def delete_user(user_id):
    """Delete a user account (admin only)."""
    if not require_admin():
        return {"error": "Admin access required"}, 403

    if current_user.id == user_id:
        return {"error": "You cannot delete your own account"}, 400

    user = User.query.get_or_404(user_id)

    # Prevent deleting other admins by default (safety)
    if user.role == Role.ADMIN:
        return {"error": "Cannot delete an admin account"}, 400

    try:
        # Delete related data first to avoid foreign key constraints
        
        # Delete user's assessments and related data
        from app.models.assessment import Assessment
        from app.models.assessment import AssessmentSymptom
        from app.models.follow_up_notification import FollowUpNotification
        from app.models.consultation_request import ConsultationRequest
        from app.models.referral import ReferralSlip
        
        user_assessments = Assessment.query.filter_by(user_id=user_id).all()
        for assessment in user_assessments:
            # Delete follow-up notifications
            FollowUpNotification.query.filter_by(assessment_id=assessment.id).delete()
            # Delete consultation requests
            ConsultationRequest.query.filter_by(assessment_id=assessment.id).delete()
            # Delete referrals
            ReferralSlip.query.filter_by(assessment_id=assessment.id).delete()
            # Delete assessment symptoms
            AssessmentSymptom.query.filter_by(assessment_id=assessment.id).delete()
            # Delete the assessment
            db.session.delete(assessment)
        
        # Delete user's health profile if exists
        from app.models.health_profile import HealthProfile
        health_profile = HealthProfile.query.filter_by(user_id=user_id).first()
        if health_profile:
            db.session.delete(health_profile)
        
        # Delete the user
        db.session.delete(user)
        db.session.commit()

        return {"message": f"User {user.username} and all related data deleted successfully"}
        
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Failed to delete user %s", user_id)
        return {"error": "Failed to delete user"}, 500
