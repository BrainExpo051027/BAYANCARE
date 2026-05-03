"""
BAYANCARE Notification Service
Centralized email notification helpers with HTML templates.
All functions use a consistent send_email(to, subject, body, html_body) signature.
"""
from flask import current_app
from flask_mail import Message
from app.extensions import mail, db
import os
from datetime import datetime, timedelta


# ---------------------------------------------------------------------------
# Core email sender
# ---------------------------------------------------------------------------

def send_email(to, subject, body, html_body=None):
    """
    Send an email using the configured mail server.

    Args:
        to (str): Recipient email address
        subject (str): Email subject
        body (str): Plain-text fallback
        html_body (str, optional): HTML body (preferred by modern clients)

    Returns:
        bool: True on success, False on failure
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
        current_app.logger.info(f"Email sent successfully to {to}: {subject}")
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to send email to {to}: {str(e)}")
        return False


# ---------------------------------------------------------------------------
# HTML template helper
# ---------------------------------------------------------------------------

def _html_wrap(title, content_html, badge_color="#0d6efd", badge_text=None):
    """Wrap content in a branded HTML email shell."""
    badge_html = ""
    if badge_text:
        badge_html = (
            f'<div style="text-align:center;margin:12px 0;">'
            f'<span style="display:inline-block;background:{badge_color};color:#fff;'
            f'padding:6px 18px;border-radius:999px;font-weight:700;font-size:14px;">'
            f'{badge_text}</span></div>'
        )
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title></head>
<body style="margin:0;padding:0;background:#f0f4f8;font-family:Arial,Helvetica,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f4f8;padding:30px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 16px rgba(0,0,0,.08);">
        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,#0d6efd,#0a58ca);padding:28px 32px;text-align:center;">
            <h1 style="margin:0;color:#fff;font-size:26px;letter-spacing:1px;">🏥 BAYANCARE</h1>
            <p style="margin:6px 0 0;color:#cfe2ff;font-size:13px;">Barangay Health Advisory System</p>
          </td>
        </tr>
        <!-- Body -->
        <tr>
          <td style="padding:28px 32px;">
            <h2 style="margin:0 0 6px;color:#1a1a2e;font-size:20px;">{title}</h2>
            {badge_html}
            <hr style="border:none;border-top:1px solid #e9ecef;margin:16px 0;">
            {content_html}
          </td>
        </tr>
        <!-- Footer -->
        <tr>
          <td style="background:#f8f9fa;padding:18px 32px;text-align:center;border-top:1px solid #e9ecef;">
            <p style="margin:0;font-size:12px;color:#6c757d;">
              This is an automated message from <strong>BAYANCARE</strong>.<br>
              Barangay Health Advisory System — Serving our community's health needs.
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def _get_display_name(user):
    """Return the best available display name for a user."""
    if user.health_profile:
        hp = user.health_profile
        if hp.full_name:
            return hp.full_name
        parts = [hp.first_name, hp.middle_name, hp.last_name]
        name = " ".join(p for p in parts if p)
        if name.strip():
            return name.strip()
    return user.username


# ---------------------------------------------------------------------------
# 1. Announcement notification
# ---------------------------------------------------------------------------

def notify_announcement_to_residents(barangay, title, body, is_emergency=False):
    """
    Notify ALL residents in a barangay when a new announcement is posted.
    Called from announcement_routes.create_announcement().
    """
    from app.models.user import User, Role
    from app.models.health_profile import HealthProfile

    # Notify all users (Residents, BHWs, Admins) who belong to the targeted barangay
    query = db.session.query(User)
    
    if barangay and barangay.lower() not in ['all', 'general', 'any', 'polomolok']:
        # Check HealthProfile barangay OR handle test accounts gracefully
        query = query.outerjoin(HealthProfile).filter(
            db.or_(
                db.func.lower(HealthProfile.barangay) == barangay.lower(),
                HealthProfile.barangay.is_(None)
            )
        )
        
    residents = query.all()

    subject = f"BAYANCARE: {'🚨 EMERGENCY — ' if is_emergency else 'New Announcement — '}{title}"

    emergency_banner = ""
    if is_emergency:
        emergency_banner = (
            '<div style="background:#dc3545;color:#fff;padding:12px 16px;border-radius:8px;'
            'margin-bottom:16px;font-weight:700;text-align:center;">🚨 EMERGENCY ANNOUNCEMENT — PLEASE READ IMMEDIATELY</div>'
        )

    for resident in residents:
        name = _get_display_name(resident)
        email = resident.email
        if not email:
            continue

        # Plain text fallback
        plain = (
            f"Hi {name},\n\n"
            f"{'⚠️ EMERGENCY ANNOUNCEMENT\n\n' if is_emergency else ''}"
            f"A new announcement has been posted for your barangay:\n\n"
            f"Title: {title}\n\n"
            f"{body}\n\n"
            f"{'This is an EMERGENCY announcement. Please take appropriate action immediately.\n\n' if is_emergency else ''}"
            f"Log in to BAYANCARE to view the full announcement.\n\n"
            f"Thank you,\nBAYANCARE Team"
        )

        # HTML body
        html_content = f"""
        {emergency_banner}
        <p style="color:#495057;font-size:15px;">Hi <strong>{name}</strong>,</p>
        <p style="color:#495057;font-size:15px;">
          A new announcement has been posted for your barangay:
        </p>
        <div style="background:#f8f9fa;border-left:4px solid {'#dc3545' if is_emergency else '#0d6efd'};
                    padding:16px 20px;border-radius:0 8px 8px 0;margin:16px 0;">
          <h3 style="margin:0 0 8px;color:#1a1a2e;">{title}</h3>
          <p style="margin:0;color:#495057;white-space:pre-wrap;">{body}</p>
        </div>
        <p style="color:#495057;font-size:14px;">
          Log in to <strong>BAYANCARE</strong> to view the full announcement and stay informed.
        </p>
        <div style="text-align:center;margin-top:24px;">
          <a href="http://localhost:5000/dashboard.html"
             style="background:#0d6efd;color:#fff;padding:12px 28px;border-radius:8px;
                    text-decoration:none;font-weight:700;font-size:15px;">
            View Announcement
          </a>
        </div>
        """

        badge_color = "#dc3545" if is_emergency else "#0d6efd"
        badge_text = "🚨 EMERGENCY" if is_emergency else "📢 New Announcement"
        html_body = _html_wrap(f"Announcement: {title}", html_content,
                               badge_color=badge_color, badge_text=badge_text)

        send_email(email, subject, plain, html_body)


def notify_emergency_announcement(barangay, title, body):
    """Legacy shim — calls the main notify function with is_emergency=True."""
    notify_announcement_to_residents(barangay, title, body, is_emergency=True)


# ---------------------------------------------------------------------------
# 2. Assessment status notification (BHW notifies resident)
# ---------------------------------------------------------------------------

def notify_assessment_status_update(user, assessment, status_message, bhw_name=None):
    """
    Notify a resident when a BHW reviews/updates their health assessment status.
    Called from consultation_routes when BHW assigns or updates a consultation.
    """
    name = _get_display_name(user)
    email = user.email
    if not email:
        return False

    risk = assessment.risk_level.value if assessment.risk_level else "UNKNOWN"
    risk_colors = {"HIGH": "#dc3545", "MODERATE": "#fd7e14", "LOW": "#198754"}
    risk_color = risk_colors.get(risk, "#6c757d")

    bhw_line = f"<p style='color:#495057;font-size:14px;'>Reviewed by: <strong>{bhw_name}</strong></p>" if bhw_name else ""

    subject = f"BAYANCARE: Health Assessment Update — Assessment #{assessment.id}"

    plain = (
        f"Hi {name},\n\n"
        f"Your health assessment (ID: {assessment.id}) has been reviewed by a Barangay Health Worker.\n\n"
        f"Risk Level: {risk}\n"
        f"Update: {status_message}\n\n"
        f"{'Reviewed by: ' + bhw_name + chr(10) if bhw_name else ''}"
        f"Please log in to BAYANCARE to view the full update and any recommendations.\n\n"
        f"Thank you,\nBAYANCARE Team"
    )

    html_content = f"""
    <p style="color:#495057;font-size:15px;">Hi <strong>{name}</strong>,</p>
    <p style="color:#495057;font-size:15px;">
      Your health assessment has been reviewed by a Barangay Health Worker.
    </p>
    <div style="background:#f8f9fa;border-radius:8px;padding:16px 20px;margin:16px 0;">
      <table width="100%" cellpadding="4" cellspacing="0" style="font-size:14px;color:#495057;">
        <tr>
          <td style="width:140px;"><strong>Assessment ID:</strong></td>
          <td>#{assessment.id}</td>
        </tr>
        <tr>
          <td><strong>Risk Level:</strong></td>
          <td><span style="background:{risk_color};color:#fff;padding:2px 10px;border-radius:999px;font-size:13px;">{risk}</span></td>
        </tr>
        <tr>
          <td><strong>Date:</strong></td>
          <td>{assessment.created_at.strftime('%B %d, %Y') if assessment.created_at else 'N/A'}</td>
        </tr>
      </table>
    </div>
    <div style="background:#e7f3ff;border-left:4px solid #0d6efd;padding:14px 18px;border-radius:0 8px 8px 0;margin:16px 0;">
      <strong style="color:#0d6efd;">BHW Update:</strong>
      <p style="margin:6px 0 0;color:#495057;">{status_message}</p>
    </div>
    {bhw_line}
    <div style="text-align:center;margin-top:24px;">
      <a href="http://localhost:5000/dashboard.html"
         style="background:#0d6efd;color:#fff;padding:12px 28px;border-radius:8px;
                text-decoration:none;font-weight:700;font-size:15px;">
        View My Assessment
      </a>
    </div>
    """

    html_body = _html_wrap("Health Assessment Update", html_content,
                           badge_color=risk_color, badge_text=f"Risk: {risk}")
    return send_email(email, subject, plain, html_body)


# ---------------------------------------------------------------------------
# 3. Recovery date achieved notification
# ---------------------------------------------------------------------------

def notify_recovery_date_reached(user, assessment):
    """
    Notify a resident when their recovery end date has been reached.
    Called by RecoveryNotificationService.send_recovery_notification().
    """
    name = _get_display_name(user)
    email = user.email
    if not email:
        return False

    risk = assessment.risk_level.value if assessment.risk_level else "UNKNOWN"
    recovery_date = (
        assessment.recovery_end_date.strftime("%B %d, %Y")
        if assessment.recovery_end_date else "Today"
    )
    symptoms_list = [s.symptom_name for s in assessment.symptoms]
    symptoms_text = ", ".join(symptoms_list) if symptoms_list else "your reported symptoms"

    subject = f"BAYANCARE: Your Recovery Date Has Been Reached — Assessment #{assessment.id}"

    plain = (
        f"Hi {name},\n\n"
        f"Your expected recovery date ({recovery_date}) has been reached for assessment #{assessment.id}.\n\n"
        f"Symptoms tracked: {symptoms_text}\n"
        f"Risk level: {risk}\n\n"
        f"Please log in to BAYANCARE to update your condition status:\n"
        f"  • Mark as RECOVERED if you are feeling better\n"
        f"  • Report if symptoms are the same or have worsened\n\n"
        f"If symptoms have worsened, please contact your Barangay Health Worker immediately.\n\n"
        f"Thank you,\nBAYANCARE Team"
    )

    html_content = f"""
    <p style="color:#495057;font-size:15px;">Hi <strong>{name}</strong>,</p>
    <p style="color:#495057;font-size:15px;">
      Your expected recovery date has arrived! Please update your health status.
    </p>
    <div style="background:#f8f9fa;border-radius:8px;padding:16px 20px;margin:16px 0;">
      <table width="100%" cellpadding="4" cellspacing="0" style="font-size:14px;color:#495057;">
        <tr>
          <td style="width:160px;"><strong>Assessment ID:</strong></td>
          <td>#{assessment.id}</td>
        </tr>
        <tr>
          <td><strong>Recovery Date:</strong></td>
          <td><strong style="color:#198754;">{recovery_date}</strong></td>
        </tr>
        <tr>
          <td><strong>Symptoms:</strong></td>
          <td>{symptoms_text}</td>
        </tr>
        <tr>
          <td><strong>Risk Level:</strong></td>
          <td>{risk}</td>
        </tr>
      </table>
    </div>
    <p style="color:#495057;font-size:15px;"><strong>Please log in and report your current condition:</strong></p>
    <ul style="color:#495057;font-size:14px;padding-left:20px;">
      <li>✅ <strong>Recovered</strong> — if you are feeling better</li>
      <li>🔄 <strong>Same</strong> — if symptoms are unchanged</li>
      <li>⚠️ <strong>Worsened</strong> — if symptoms have gotten worse (contact BHW immediately)</li>
    </ul>
    <div style="text-align:center;margin-top:24px;">
      <a href="http://localhost:5000/recovery.html"
         style="background:#198754;color:#fff;padding:12px 28px;border-radius:8px;
                text-decoration:none;font-weight:700;font-size:15px;">
        Update My Recovery Status
      </a>
    </div>
    """

    html_body = _html_wrap("Recovery Date Reached", html_content,
                           badge_color="#198754", badge_text="📅 Recovery Check-In")
    return send_email(email, subject, plain, html_body)


# ---------------------------------------------------------------------------
# 4. Referral slip generated notification
# ---------------------------------------------------------------------------

def notify_referral_generated(user, referral):
    """
    Notify a resident that a referral slip has been generated for them.
    Called from referral_routes.create_referral() and
    consultation_routes.generate_consultation_referral().
    """
    name = _get_display_name(user)
    email = user.email
    if not email:
        return False

    expires_text = ""
    if hasattr(referral, 'expires_at') and referral.expires_at:
        expires_text = referral.expires_at.strftime("%B %d, %Y")

    subject = f"BAYANCARE: Referral Slip Generated — {referral.referral_code}"

    plain = (
        f"Hi {name},\n\n"
        f"A referral slip has been generated for you by your Barangay Health Worker.\n\n"
        f"Referral Code: {referral.referral_code}\n"
        f"Referred To: {referral.referred_to_center}\n"
        f"{'Valid Until: ' + expires_text + chr(10) if expires_text else ''}"
        f"\nPlease present this referral code at the health facility.\n"
        f"You can also download the PDF referral slip by logging in to BAYANCARE.\n\n"
        f"Thank you,\nBAYANCARE Team"
    )

    expires_row = ""
    if expires_text:
        expires_row = f"""
        <tr>
          <td style="width:140px;"><strong>Valid Until:</strong></td>
          <td style="color:#dc3545;"><strong>{expires_text}</strong></td>
        </tr>"""

    html_content = f"""
    <p style="color:#495057;font-size:15px;">Hi <strong>{name}</strong>,</p>
    <p style="color:#495057;font-size:15px;">
      A referral slip has been generated for you by your Barangay Health Worker.
      Please bring this to the referred health facility.
    </p>
    <div style="background:#fff3cd;border:1px solid #ffc107;border-radius:8px;padding:20px 24px;margin:20px 0;text-align:center;">
      <p style="margin:0 0 6px;font-size:13px;color:#6c757d;text-transform:uppercase;letter-spacing:1px;">Referral Code</p>
      <p style="margin:0;font-size:28px;font-weight:700;color:#1a1a2e;letter-spacing:4px;">{referral.referral_code}</p>
    </div>
    <div style="background:#f8f9fa;border-radius:8px;padding:16px 20px;margin:16px 0;">
      <table width="100%" cellpadding="4" cellspacing="0" style="font-size:14px;color:#495057;">
        <tr>
          <td style="width:140px;"><strong>Referred To:</strong></td>
          <td>{referral.referred_to_center}</td>
        </tr>
        {expires_row}
        <tr>
          <td><strong>Status:</strong></td>
          <td><span style="background:#ffc107;color:#000;padding:2px 10px;border-radius:999px;font-size:13px;">PENDING</span></td>
        </tr>
      </table>
    </div>
    <p style="color:#495057;font-size:14px;">
      You can download your official PDF referral slip by logging in to BAYANCARE and visiting the <strong>Referrals</strong> section.
    </p>
    <div style="text-align:center;margin-top:24px;">
      <a href="http://localhost:5000/dashboard.html"
         style="background:#0d6efd;color:#fff;padding:12px 28px;border-radius:8px;
                text-decoration:none;font-weight:700;font-size:15px;">
        Download Referral PDF
      </a>
    </div>
    """

    html_body = _html_wrap("Referral Slip Generated", html_content,
                           badge_color="#ffc107", badge_text="📋 Referral Generated")
    return send_email(email, subject, plain, html_body)


# ---------------------------------------------------------------------------
# Legacy / utility helpers kept for backward compatibility
# ---------------------------------------------------------------------------

def notify_user_follow_up(user, assessment):
    """Notify a user about a follow-up due."""
    name = _get_display_name(user)
    email = user.email
    subject = "BAYANCARE: Follow-up Reminder"
    body = (
        f"Hi {name},\n\n"
        f"It's time to update your condition for assessment #{assessment.id}. "
        f"Please log in to BAYANCARE to record whether your symptoms have improved, "
        f"stayed the same, or worsened.\n\n"
        "Thank you,\nBAYANCARE Team"
    )
    if email:
        send_email(email, subject, body)


def notify_follow_up_check_in(user, assessment):
    """Send follow-up check-in notification after 2-3 days."""
    name = _get_display_name(user)
    email = user.email
    subject = "BAYANCARE: Health Check-in"
    body = (
        f"Hi {name},\n\n"
        f"How are you feeling after your recent assessment (ID: {assessment.id})?\n\n"
        f"Please log in to BAYANCARE and let us know:\n"
        f"- Have your symptoms improved?\n"
        f"- Are they the same?\n"
        f"- Have they worsened?\n\n"
        f"If you don't respond within 24 hours, we may follow up with additional assistance.\n\n"
        "Thank you,\nBAYANCARE Team"
    )
    if email:
        send_email(email, subject, body)


def generate_auto_referral_if_no_response(user, assessment):
    """Generate automatic referral if user doesn't respond to follow-up."""
    from app.models.referral import ReferralSlip
    from app.utils.pdf_generator import generate_referral_pdf
    import uuid

    existing_referral = ReferralSlip.query.filter_by(assessment_id=assessment.id).first()
    if existing_referral:
        return existing_referral

    referral_code = f"AUTO-{str(uuid.uuid4())[:8].upper()}"
    referral = ReferralSlip(
        assessment_id=assessment.id,
        referral_code=referral_code,
        referred_to_center="Barangay Health Center",
        barangay=user.health_profile.barangay if user.health_profile else "Unknown",
        generated_by=user.id,
        status="PENDING",
        notes="Auto-generated due to no response to follow-up notification"
    )
    db.session.add(referral)
    db.session.commit()

    notify_referral_generated(user, referral)
    return referral

# ---------------------------------------------------------------------------
# 5. Resident Follow-up Response Notification to BHW
# ---------------------------------------------------------------------------

def notify_bhw_patient_response(user, assessment, patient_response):
    """
    Notify the BHWs when a resident submits a follow-up response.
    """
    from app.models.user import User, Role
    from app.models.health_profile import HealthProfile
    
    barangay = "Unknown"
    hp = user.health_profile
    if hp and hp.barangay:
        barangay = hp.barangay

    # Find BHWs/Admins of the same barangay
    bhw_users = (
        db.session.query(User)
        .join(HealthProfile)
        .filter(User.role.in_([Role.BHW, Role.ADMIN]), HealthProfile.barangay == barangay)
        .all()
    )
    
    # If no BHWs matched by barangay, fallback to all admins
    if not bhw_users:
        bhw_users = User.query.filter(User.role == Role.ADMIN).all()

    resident_name = _get_display_name(user)
    
    if patient_response == 'OKAY':
        badge_color = "#198754"
        response_text = "Recovered"
    elif patient_response == 'SAME':
        badge_color = "#fd7e14"
        response_text = "Still Recovering"
    else: # WORSENED
        badge_color = "#dc3545"
        response_text = "Worsened / Needs Care"

    subject = f"BAYANCARE: Patient Response Update — {resident_name}"
    
    plain = (
        f"A resident has updated their health condition.\n\n"
        f"Resident: {resident_name}\n"
        f"Barangay: {barangay}\n"
        f"Condition: {patient_response} ({response_text})\n"
        f"Assessment ID: {assessment.id}\n\n"
        f"Please log in to the BAYANCARE dashboard for more details and to take necessary action."
    )
    
    html_content = f"""
    <p style="color:#495057;font-size:15px;">A resident has updated their health condition status.</p>
    <div style="background:#f8f9fa;border-radius:8px;padding:16px 20px;margin:16px 0;">
      <table width="100%" cellpadding="4" cellspacing="0" style="font-size:14px;color:#495057;">
        <tr>
          <td style="width:140px;"><strong>Resident:</strong></td>
          <td>{resident_name}</td>
        </tr>
        <tr>
          <td><strong>Barangay:</strong></td>
          <td>{barangay}</td>
        </tr>
        <tr>
          <td><strong>Assessment ID:</strong></td>
          <td>#{assessment.id}</td>
        </tr>
        <tr>
          <td><strong>Condition:</strong></td>
          <td><strong style="color:{badge_color};">{patient_response} ({response_text})</strong></td>
        </tr>
      </table>
    </div>
    <div style="text-align:center;margin-top:24px;">
      <a href="http://localhost:5000/dashboard.html"
         style="background:#0d6efd;color:#fff;padding:12px 28px;border-radius:8px;
                text-decoration:none;font-weight:700;font-size:15px;">
        View Dashboard
      </a>
    </div>
    """
    
    html_body = _html_wrap(f"Patient Follow-up Response", html_content,
                           badge_color=badge_color, badge_text=f"Response: {response_text}")

    success_count = 0
    for bhw in bhw_users:
        if bhw.email:
            if send_email(bhw.email, subject, plain, html_body):
                success_count += 1
                
    return success_count > 0
