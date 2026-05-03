"""
Notification routes for testing email functionality
"""

from flask import Blueprint, request, jsonify
from app.utils.email_utils import send_email, send_welcome_email

notification_bp = Blueprint('notifications', __name__)

@notification_bp.route('/test-email', methods=['POST'])
def test_email():
    """Send a test email"""
    try:
        data = request.get_json()
        recipient = data.get('recipient', 'test@bayancare.local')
        subject = data.get('subject', 'BAYANCARE Test Email')
        message = data.get('message', 'This is a test email from BAYANCARE notification system.')
        
        # Use standardized signature: send_email(to, subject, body)
        success = send_email(recipient, subject, message)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Test email sent successfully to {recipient}'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to send test email'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@notification_bp.route('/welcome-notification', methods=['POST'])
def welcome_notification():
    """Send welcome email to a new user"""
    try:
        data = request.get_json()
        email = data.get('email')
        name = data.get('name', 'User')
        
        if not email:
            return jsonify({
                'success': False,
                'message': 'Email address is required'
            }), 400
        
        results = {}
        
        # Send welcome email
        email_success = send_welcome_email(email, name)
        results['email'] = {
            'success': email_success,
            'message': f'Welcome email {"sent" if email_success else "failed"} to {email}'
        }
        
        return jsonify({
            'success': True,
            'message': 'Welcome notification processed',
            'results': results
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@notification_bp.route('/appointment-reminder', methods=['POST'])
def appointment_reminder():
    """Send appointment reminder email"""
    try:
        data = request.get_json()
        email = data.get('email')
        name = data.get('name', 'Patient')
        appointment_date = data.get('appointment_date', 'Tomorrow')
        appointment_time = data.get('appointment_time', '10:00 AM')
        
        if not email:
            return jsonify({
                'success': False,
                'message': 'Email address is required'
            }), 400
        
        results = {}
        
        # Send appointment reminder email
        from app.utils.email_utils import send_appointment_reminder
        email_success = send_appointment_reminder(email, name, appointment_date, appointment_time)
        results['email'] = {
            'success': email_success,
            'message': f'Appointment reminder email {"sent" if email_success else "failed"} to {email}'
        }
        
        return jsonify({
            'success': True,
            'message': 'Appointment reminder processed',
            'results': results
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@notification_bp.route('/status', methods=['GET'])
def notification_status():
    """Get notification system status"""
    try:
        return jsonify({
            'success': True,
            'email_configured': True,
            'sms_enabled': False,
            'message': 'Email notification system is operational (SMS removed)'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500
