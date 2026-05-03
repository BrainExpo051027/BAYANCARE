"""
Recovery Notification Routes
API endpoints for managing recovery dates and notifications
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.services.recovery_notification_service import RecoveryNotificationService
from app.models.assessment import Assessment, RiskLevel
from app.utils.decorators import role_required
from app.models.user import Role
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

recovery_bp = Blueprint("recovery_routes", __name__)

@recovery_bp.route("/assessment/<int:assessment_id>/timeline", methods=["GET"])
@login_required
def get_recovery_timeline(assessment_id):
    """Get recovery timeline for an assessment"""
    try:
        # Check if user has access to this assessment
        assessment = Assessment.query.get_or_404(assessment_id)
        
        # Users can only see their own assessments, BHWs can see all
        if current_user.role not in (Role.BHW, Role.ADMIN) and assessment.user_id != current_user.id:
            return {"error": "Access denied"}, 403
        
        timeline = RecoveryNotificationService.get_recovery_timeline(assessment_id)
        if not timeline:
            return {"error": "Assessment not found"}, 404
        
        return jsonify(timeline)
        
    except Exception as e:
        logger.error(f"Error getting recovery timeline: {str(e)}")
        return {"error": "Internal server error"}, 500

@recovery_bp.route("/assessment/<int:assessment_id>/recovery-dates", methods=["PUT"])
@login_required
@role_required(Role.BHW, Role.ADMIN)
def update_recovery_dates(assessment_id):
    """Update recovery dates for an assessment (BHW only)"""
    try:
        data = request.get_json()
        new_recovery_end_date = data.get('recovery_end_date')
        
        success = RecoveryNotificationService.update_recovery_dates(
            assessment_id, 
            new_recovery_end_date
        )
        
        if not success:
            return {"error": "Failed to update recovery dates"}, 400
        
        return {"message": "Recovery dates updated successfully"}
        
    except Exception as e:
        logger.error(f"Error updating recovery dates: {str(e)}")
        return {"error": "Internal server error"}, 500

@recovery_bp.route("/assessment/<int:assessment_id>/send-notification", methods=["POST"])
@login_required
@role_required(Role.BHW, Role.ADMIN)
def send_recovery_notification(assessment_id):
    """Send recovery notification for an assessment (BHW only)"""
    try:
        success = RecoveryNotificationService.send_recovery_notification(assessment_id)
        
        if not success:
            return {"error": "Failed to send recovery notification"}, 400
        
        return {"message": "Recovery notification sent successfully"}
        
    except Exception as e:
        logger.error(f"Error sending recovery notification: {str(e)}")
        return {"error": "Internal server error"}, 500

@recovery_bp.route("/check-due-notifications", methods=["POST"])
@login_required
@role_required(Role.BHW, Role.ADMIN)
def check_due_notifications():
    """Check and send due recovery notifications (BHW only)"""
    try:
        sent_count = RecoveryNotificationService.check_and_send_due_notifications()
        
        return jsonify({
            "message": f"Recovery notification check completed",
            "notifications_sent": sent_count
        })
        
    except Exception as e:
        logger.error(f"Error checking due notifications: {str(e)}")
        return {"error": "Internal server error"}, 500

@recovery_bp.route("/assessment/<int:assessment_id>/follow-up-response", methods=["POST"])
@login_required
def submit_follow_up_response(assessment_id):
    """Submit patient's follow-up response"""
    try:
        data = request.get_json()
        patient_response = data.get('response')  # 'OKAY', 'SAME', 'WORSENED'
        
        if patient_response not in ['OKAY', 'SAME', 'WORSENED']:
            return {"error": "Invalid response. Must be OKAY, SAME, or WORSENED"}, 400
        
        # Check if user has access to this assessment
        assessment = Assessment.query.get_or_404(assessment_id)
        
        # Users can only respond to their own assessments, BHWs can respond to any
        if current_user.role not in (Role.BHW, Role.ADMIN) and assessment.user_id != current_user.id:
            return {"error": "Access denied"}, 403
        
        success = RecoveryNotificationService.process_patient_follow_up(
            assessment_id, 
            patient_response
        )
        
        if not success:
            return {"error": "Failed to process follow-up response"}, 400
        
        return {"message": f"Follow-up response '{patient_response}' processed successfully"}
        
    except Exception as e:
        logger.error(f"Error submitting follow-up response: {str(e)}")
        return {"error": "Internal server error"}, 500

@recovery_bp.route("/dashboard", methods=["GET"])
@login_required
@role_required(Role.BHW, Role.ADMIN)
def get_recovery_dashboard():
    """Get recovery dashboard data for BHWs"""
    try:
        now = datetime.utcnow()
        
        # Get all assessments with recovery dates — exclude HIGH risk (handled via Consultations)
        assessments_with_recovery = Assessment.query.filter(
            Assessment.recovery_end_date.isnot(None),
            Assessment.risk_level != RiskLevel.HIGH
        ).all()
        
        dashboard_data = {
            'total_active_recoveries': 0,
            'due_today': 0,
            'overdue': 0,
            'due_soon': 0,  # Next 3 days
            'notified': 0,
            'pending_notifications': 0,
            'recent_assessments': []
        }
        
        for assessment in assessments_with_recovery:
            days_until = (assessment.recovery_end_date - now).days
            
            # Count for stats regardless of status - any assessment with recovery date matters
            if days_until < 0:
                dashboard_data['overdue'] += 1
            elif days_until == 0:
                dashboard_data['due_today'] += 1
            elif days_until <= 3:
                dashboard_data['due_soon'] += 1
            
            # Only count as active recovery if status is OPEN or FOLLOW_UP
            if assessment.status in ['OPEN', 'FOLLOW_UP']:
                dashboard_data['total_active_recoveries'] += 1
                
                if assessment.recovery_notified:
                    dashboard_data['notified'] += 1
                else:
                    dashboard_data['pending_notifications'] += 1
        
        # Get recent assessments needing recovery tracking (exclude overdue and completed)
        recent_assessments = []
        for assessment in assessments_with_recovery:
            days_until = (assessment.recovery_end_date - now).days if assessment.recovery_end_date else None
            
            # Only include if not overdue and status is OPEN or FOLLOW_UP
            is_not_overdue = days_until >= 0 if days_until is not None else True
            is_active_status = assessment.status in ['OPEN', 'FOLLOW_UP']
            
            if is_not_overdue and is_active_status:
                recent_assessments.append({
                    'id': assessment.id,
                    'user_id': assessment.user_id,
                    'username': assessment.user.username,
                    'symptoms': [s.symptom_name for s in assessment.symptoms],
                    'risk_level': assessment.risk_level.value,
                    'recovery_end_date': assessment.recovery_end_date.isoformat() if assessment.recovery_end_date else None,
                    'days_until_recovery': days_until,
                    'recovery_notified': assessment.recovery_notified,
                    'status': assessment.status
                })
        
        # Limit to 10 most recent
        dashboard_data['recent_assessments'] = recent_assessments[:10]
        
        return jsonify(dashboard_data)
        
    except Exception as e:
        logger.error(f"Error getting recovery dashboard: {str(e)}")
        return {"error": "Internal server error"}, 500

@recovery_bp.route("/archived-recoveries", methods=["GET"])
@login_required
@role_required(Role.BHW, Role.ADMIN)
def get_archived_recoveries():
    """Get archived overdue recoveries for admin/BHW"""
    try:
        now = datetime.utcnow()
        
        # Get all assessments with recovery dates — exclude HIGH risk (handled via Consultations)
        assessments = Assessment.query.filter(
            Assessment.recovery_end_date.isnot(None),
            Assessment.risk_level != RiskLevel.HIGH
        ).order_by(Assessment.created_at.desc()).all()
        
        archived_recoveries = []
        for assessment in assessments:
            days_until = (assessment.recovery_end_date - now).days
            
            # Include if overdue (days_until < 0) or status is RESOLVED/REFERRED
            is_overdue = days_until < 0
            is_completed = assessment.status in ['RESOLVED', 'REFERRED']
            
            if is_overdue or is_completed:
                archived_recoveries.append({
                    'id': assessment.id,
                    'user_id': assessment.user_id,
                    'username': assessment.user.username,
                    'symptoms': [s.symptom_name for s in assessment.symptoms],
                    'risk_level': assessment.risk_level.value,
                    'recovery_end_date': assessment.recovery_end_date.isoformat(),
                    'days_until_recovery': days_until,
                    'recovery_notified': assessment.recovery_notified,
                    'status': assessment.status,
                    'archive_reason': 'overdue' if is_overdue else 'completed',
                    'created_at': assessment.created_at.isoformat()
                })
        
        return jsonify({
            'archived_recoveries': archived_recoveries,
            'total_count': len(archived_recoveries)
        })
        
    except Exception as e:
        logger.error(f"Error getting archived recoveries: {str(e)}")
        return {"error": "Internal server error"}, 500

@recovery_bp.route("/my-recoveries", methods=["GET"])
@login_required
def get_my_recoveries():
    """Get current user's recovery timelines"""
    try:
        # Get user's assessments with recovery dates — exclude HIGH risk (handled by professionals via Consultations)
        assessments = Assessment.query.filter(
            Assessment.user_id == current_user.id,
            Assessment.recovery_end_date.isnot(None),
            Assessment.risk_level != RiskLevel.HIGH
        ).order_by(Assessment.created_at.desc()).all()
        
        recoveries = []
        for assessment in assessments:
            timeline = RecoveryNotificationService.get_recovery_timeline(assessment.id)
            if timeline:
                timeline.update({
                    'symptoms': [s.symptom_name for s in assessment.symptoms],
                    'risk_level': assessment.risk_level.value,
                    'assessment_summary': assessment.assessment_summary,
                    'recommendations': assessment.recommendations
                })
                recoveries.append(timeline)
        
        return jsonify({
            'recoveries': recoveries,
            'total_count': len(recoveries)
        })
        
    except Exception as e:
        logger.error(f"Error getting user recoveries: {str(e)}")
        return {"error": "Internal server error"}, 500
