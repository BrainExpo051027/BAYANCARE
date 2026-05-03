from app.extensions import db
from datetime import datetime
from enum import Enum

class RiskLevel(Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"

class Assessment(db.Model):
    __tablename__ = "assessments"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    risk_level = db.Column(db.Enum(RiskLevel), nullable=False)
    assessment_summary = db.Column(db.Text)
    recommendations = db.Column(db.Text)
    predicted_condition = db.Column(db.String(255))
    confidence_score = db.Column(db.Float)
    home_care_plan = db.Column(db.JSON)
    temperature = db.Column(db.Float)
    duration_days = db.Column(db.Integer)
    follow_up_required = db.Column(db.Boolean, default=False)
    follow_up_date = db.Column(db.DateTime)
    recovery_start_date = db.Column(db.DateTime)  # When recovery period starts
    recovery_end_date = db.Column(db.DateTime)    # Expected recovery date
    recovery_notified = db.Column(db.Boolean, default=False)  # Track if recovery notification sent
    status = db.Column(db.String(20), default="OPEN")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship("User", back_populates="assessments")
    symptoms = db.relationship(
        "AssessmentSymptom",
        back_populates="assessment",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    referral = db.relationship(
        "ReferralSlip",
        back_populates="assessment",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    consultation_request = db.relationship(
        "ConsultationRequest",
        back_populates="assessment",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

class AssessmentSymptom(db.Model):
    __tablename__ = "assessment_symptoms"

    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey("assessments.id"), nullable=False)
    symptom_name = db.Column(db.String(100), nullable=False)
    severity = db.Column(db.Integer)  # 1–10 or None

    assessment = db.relationship("Assessment", back_populates="symptoms")
