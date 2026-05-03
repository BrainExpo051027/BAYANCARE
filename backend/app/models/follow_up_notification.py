from app.extensions import db
from datetime import datetime, timedelta
from enum import Enum

class FollowUpStatus(Enum):
    PENDING = "PENDING"
    IMPROVED = "IMPROVED"
    SAME = "SAME"
    WORSENED = "WORSENED"
    NO_RESPONSE = "NO_RESPONSE"

class FollowUpNotification(db.Model):
    __tablename__ = "follow_up_notifications"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    assessment_id = db.Column(db.Integer, db.ForeignKey("assessments.id"), nullable=False)
    notification_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.Enum(FollowUpStatus), default=FollowUpStatus.PENDING)
    user_response = db.Column(db.Text)  # User's feedback about their condition
    auto_referral_generated = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    responded_at = db.Column(db.DateTime)
    
    # Relationships
    user = db.relationship("User", backref="follow_up_notifications")
    assessment = db.relationship("Assessment", backref="follow_up_notifications")
