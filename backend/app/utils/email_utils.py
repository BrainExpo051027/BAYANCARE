from flask import current_app
from flask_mail import Message
from app.extensions import mail
import os

def send_email(to, subject, body, html_body=None):
    """
    Send an email using the configured mail server.
    Standardized signature: send_email(to, subject, body)
    
    Args:
        to (str): Recipient email address
        subject (str): Email subject
        body (str): Plain text email body
        html_body (str, optional): HTML email body
    
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    try:
        msg = Message(
            subject=subject,
            sender=current_app.config['MAIL_DEFAULT_SENDER'],
            recipients=[to]
        )
        msg.body = body
        if html_body:
            msg.html = html_body
        
        mail.send(msg)
        current_app.logger.info(f"Email sent successfully to {to}")
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to send email to {to}: {str(e)}")
        return False

def send_welcome_email(user_email, user_name):
    """Send welcome email to new users"""
    subject = "Welcome to BAYANCARE"
    body = f"""
    Dear {user_name},
    
    Welcome to BAYANCARE! Your account has been successfully created.
    
    If you have any questions, please don't hesitate to contact us.
    
    Best regards,
    The BAYANCARE Team
    """
    
    return send_email(user_email, subject, body)

def send_appointment_reminder(user_email, user_name, appointment_date, appointment_time):
    """Send appointment reminder email"""
    subject = "Appointment Reminder - BAYANCARE"
    body = f"""
    Dear {user_name},
    
    This is a reminder that you have an appointment scheduled:
    Date: {appointment_date}
    Time: {appointment_time}
    
    Please arrive 10 minutes before your scheduled time.
    
    Best regards,
    The BAYANCARE Team
    """
    
    return send_email(user_email, subject, body)
