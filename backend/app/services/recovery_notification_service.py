"""
Recovery Notification Service
Handles sending notifications when recovery dates are reached or adjusted
"""

from datetime import datetime, timedelta
from app.extensions import db
from app.models.assessment import Assessment
from app.models.user import User
from app.services.notification_service import notify_recovery_date_reached, send_email
import logging

logger = logging.getLogger(__name__)

class RecoveryNotificationService:
    
    @staticmethod
    def calculate_recovery_dates(risk_level, duration_days, symptoms):
        """
        Calculate recovery start and end dates based on risk level and symptoms
        """
        now = datetime.utcnow()
        
        # Base recovery periods in days
        base_recovery_periods = {
            'LOW': 3,      # 3 days for mild symptoms
            'MODERATE': 7, # 1 week for moderate symptoms
            'HIGH': 14     # 2 weeks for severe symptoms
        }
        
        # Get base period
        base_days = base_recovery_periods.get(risk_level.value, 7)
        
        # Adjust based on duration and number of symptoms
        if duration_days:
            base_days += min(duration_days // 2, 7)  # Add up to 7 days based on duration
        
        # Recovery starts tomorrow (gives time for treatment to begin)
        recovery_start = now + timedelta(days=1)
        recovery_end = recovery_start + timedelta(days=base_days)
        
        return recovery_start, recovery_end
    
    @staticmethod
    def update_recovery_dates(assessment_id, new_recovery_end_date=None):
        """
        Update recovery dates for an assessment and send notifications
        """
        try:
            assessment = Assessment.query.get(assessment_id)
            if not assessment:
                logger.error(f"Assessment {assessment_id} not found")
                return False
            
            user = assessment.user
            
            # If no new date provided, calculate based on current assessment
            if not new_recovery_end_date:
                recovery_start, recovery_end = RecoveryNotificationService.calculate_recovery_dates(
                    assessment.risk_level, 
                    assessment.duration_days,
                    assessment.symptoms
                )
                assessment.recovery_start_date = recovery_start
                assessment.recovery_end_date = recovery_end
            else:
                # Parse the new date if provided as string
                if isinstance(new_recovery_end_date, str):
                    recovery_end = datetime.fromisoformat(new_recovery_end_date.replace('Z', '+00:00'))
                else:
                    recovery_end = new_recovery_end_date
                
                assessment.recovery_end_date = recovery_end
                # Keep original start date or set to tomorrow if not exists
                if not assessment.recovery_start_date:
                    assessment.recovery_start_date = datetime.utcnow() + timedelta(days=1)
            
            assessment.recovery_notified = False  # Reset notification flag
            db.session.commit()
            
            logger.info(f"Updated recovery dates for assessment {assessment_id}: "
                       f"start={assessment.recovery_start_date}, end={assessment.recovery_end_date}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating recovery dates: {str(e)}")
            db.session.rollback()
            return False
    
    @staticmethod
    def send_recovery_notification(assessment_id):
        """
        Send recovery notification to user via email and SMS
        """
        try:
            assessment = Assessment.query.get(assessment_id)
            if not assessment:
                logger.error(f"Assessment {assessment_id} not found")
                return False
            
            if assessment.recovery_notified:
                logger.info(f"Recovery notification already sent for assessment {assessment_id}")
                return True
            
            user = assessment.user
            
            # Use the centralized notification helper (rich HTML email + correct arg order)
            success = notify_recovery_date_reached(user, assessment)
            
            # Mark as notified
            assessment.recovery_notified = True
            assessment.recovery_notification_sent_at = datetime.utcnow()
            db.session.commit()
            
            if success:
                logger.info(f"Recovery notification sent for assessment {assessment_id}")
            else:
                logger.warning(f"Could not deliver recovery email for assessment {assessment_id} (no email address or send failure)")
            
            return True
                
        except Exception as e:
            logger.error(f"Error sending recovery notification: {str(e)}")
            return False
    
    @staticmethod
    def check_and_send_due_notifications():
        """
        Check for assessments that are due for recovery notifications and send them
        This should be called periodically (e.g., daily)
        """
        try:
            now = datetime.utcnow()
            
            # Find assessments where recovery date is today or past, and not yet notified
            due_assessments = Assessment.query.filter(
                Assessment.recovery_end_date <= now,
                Assessment.recovery_notified == False,
                Assessment.status.in_(['OPEN', 'FOLLOW_UP'])
            ).all()
            
            sent_count = 0
            for assessment in due_assessments:
                if RecoveryNotificationService.send_recovery_notification(assessment.id):
                    sent_count += 1
            
            logger.info(f"Recovery notification check completed: {sent_count}/{len(due_assessments)} notifications sent")
            return sent_count
            
        except Exception as e:
            logger.error(f"Error in recovery notification check: {str(e)}")
            return 0
    
    @staticmethod
    def process_patient_follow_up(assessment_id, patient_response):
        """
        Process patient's follow-up response and take appropriate action
        patient_response: 'OKAY', 'SAME', 'WORSENED'
        """
        try:
            assessment = Assessment.query.get(assessment_id)
            if not assessment:
                logger.error(f"Assessment {assessment_id} not found")
                return False
            
            user = assessment.user
            
            # Update assessment status based on response
            if patient_response == 'OKAY':
                assessment.status = 'RESOLVED'
                message = "Great news! We're glad you're feeling better. Continue to monitor your health and don't hesitate to reach out if you need further assistance."
                
            elif patient_response == 'SAME':
                assessment.status = 'FOLLOW_UP'
                assessment.follow_up_required = True
                # Extend recovery by 3 days
                if assessment.recovery_end_date:
                    assessment.recovery_end_date = assessment.recovery_end_date + timedelta(days=3)
                    assessment.recovery_notified = False  # Reset notification flag
                
                message = "We understand you're still experiencing symptoms. Your recovery period has been extended. Please continue your treatment and monitor your symptoms closely."
                
            elif patient_response == 'WORSENED':
                from app.models.assessment import RiskLevel
                assessment.status = 'OPEN'
                assessment.risk_level = RiskLevel.HIGH
                assessment.follow_up_required = True
                assessment.recovery_end_date = None
                assessment.recovery_start_date = None
                
                # Generate automatic consultation request instead of a referral
                from app.models.consultation_request import ConsultationRequest, ConsultationStatus
                
                import json
                existing_request = ConsultationRequest.query.filter_by(assessment_id=assessment_id).first()
                if not existing_request:
                    symptoms_list = [s.symptom_name for s in assessment.symptoms]
                    new_request = ConsultationRequest(
                        assessment_id=assessment_id,
                        resident_id=assessment.user_id,
                        symptoms=json.dumps(symptoms_list),
                        risk_level='HIGH',
                        status=ConsultationStatus.PENDING
                    )
                    db.session.add(new_request)
                
                message = "Your symptoms appear to have worsened. Your assessment has been escalated to HIGH risk, and a consultation request has been automatically sent to a Barangay Health Worker to review your case."
                
            else:
                logger.error(f"Invalid patient response: {patient_response}")
                return False
            
            db.session.commit()
            
            # Send confirmation message to patient
            RecoveryNotificationService._send_follow_up_confirmation(user, assessment, patient_response, message)
            
            # Also notify the BHW/Admin about the patient's response
            from app.services.notification_service import notify_bhw_patient_response
            notify_bhw_patient_response(user, assessment, patient_response)
            
            logger.info(f"Processed follow-up response {patient_response} for assessment {assessment_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing patient follow-up: {str(e)}")
            db.session.rollback()
            return False
    
    @staticmethod
    def _send_follow_up_confirmation(user, assessment, response, message):
        """Send follow-up confirmation to patient"""
        try:
            # Import notification service to use their HTML builder and mail integration
            from app.services.notification_service import _html_wrap, send_email as notif_send_email, _get_display_name
            import logging
            logger = logging.getLogger(__name__)
            
            symptom_list = ', '.join([s.symptom_name for s in assessment.symptoms])
            display_name = _get_display_name(user)
            
            if response == 'OKAY':
                badge_color = "#198754" # Success green
                status_text = "Recovered"
            elif response == 'SAME':
                badge_color = "#fd7e14" # Warning orange
                status_text = "Still Recovering"
            else: # WORSENED
                badge_color = "#dc3545" # Danger red
                status_text = "Requires Medical Care"
                
            email_subject = f"BAYANCARE - Follow-up Update: {status_text}"
            
            content_html = f"""
            <p>Dear {display_name},</p>
            <p>Thank you for submitting your health follow-up check-in.</p>
            
            <table style="width: 100%; border-collapse: collapse; margin-top: 15px; margin-bottom: 20px;">
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #dee2e6; width: 30%; color: #6c757d; font-weight: bold;">Condition</td>
                    <td style="padding: 10px; border-bottom: 1px solid #dee2e6; font-weight: bold;">{response} ({status_text})</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #dee2e6; color: #6c757d; font-weight: bold;">Symptoms Assessed</td>
                    <td style="padding: 10px; border-bottom: 1px solid #dee2e6;">{symptom_list}</td>
                </tr>
            </table>

            <div style="background-color: #f8f9fa; border-left: 4px solid {badge_color}; padding: 15px; margin: 20px 0; border-radius: 4px;">
                <h4 style="margin-top: 0; color: {badge_color}; font-size: 16px;">System Recommendation</h4>
                <p style="margin-bottom: 0;">{message}</p>
            </div>
            
            <p style="font-size: 14px; color: #6c757d;">If you have any questions or concerns, please don't hesitate to contact your Barangay Health Worker.</p>
            
            <div style="text-align: center; margin-top: 30px;">
                <a href="http://localhost:5000/resident/dashboard" style="display: inline-block; padding: 12px 24px; background-color: {badge_color}; color: white; text-decoration: none; border-radius: 4px; font-weight: bold;">Go to Dashboard</a>
            </div>
            """
            
            html_body = _html_wrap("Follow-up Recorded", content_html, badge_color=badge_color, badge_text=status_text)
            email_body_plain = f"Follow-up Update: {response}\n\n{message}\n\nPlease visit the BAYANCARE dashboard for more details."
            
            # SMS content
            sms_message = f"BAYANCARE: Follow-up received ({response}). {message[:100]}... Health hotline: +639076956467"
            
            email_sent = False
            sms_sent = False
            
            if user.email:
                try:
                    email_sent = notif_send_email(user.email, email_subject, email_body_plain, html_body)
                except Exception as e:
                    logger.error(f"Failed to send follow-up email: {str(e)}")
            
            # Get phone number from health profile if available
            user_phone = None
            if hasattr(user, 'health_profile') and user.health_profile:
                user_phone = user.health_profile.contact_number
            
            if user_phone:
                try:
                    from app.utils.sms_provider import send_sms
                    sms_sent = send_sms(user_phone, sms_message)
                except Exception as e:
                    logger.error(f"Failed to send follow-up SMS: {str(e)}")
            
            logger.info(f"Follow-up confirmation sent - Email: {email_sent}, SMS: {sms_sent}")
            
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error sending follow-up confirmation: {str(e)}")
    
    @staticmethod
    def get_recovery_timeline(assessment_id):
        """
        Get recovery timeline information for an assessment
        """
        try:
            assessment = Assessment.query.get(assessment_id)
            if not assessment:
                return None
            
            now = datetime.utcnow()
            
            timeline = {
                'assessment_id': assessment.id,
                'assessment_status': assessment.status,
                'recovery_start_date': assessment.recovery_start_date.isoformat() if assessment.recovery_start_date else None,
                'recovery_end_date': assessment.recovery_end_date.isoformat() if assessment.recovery_end_date else None,
                'recovery_notified': assessment.recovery_notified,
                'days_until_recovery': None,
                'recovery_status': None
            }
            
            if assessment.recovery_end_date:
                days_until = (assessment.recovery_end_date - now).days
                timeline['days_until_recovery'] = days_until
                
                if days_until < 0:
                    timeline['recovery_status'] = 'OVERDUE'
                elif days_until == 0:
                    timeline['recovery_status'] = 'DUE_TODAY'
                elif days_until <= 3:
                    timeline['recovery_status'] = 'DUE_SOON'
                else:
                    timeline['recovery_status'] = 'ON_TRACK'
            
            return timeline
            
        except Exception as e:
            logger.error(f"Error getting recovery timeline: {str(e)}")
            return None
