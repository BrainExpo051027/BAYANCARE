from app.extensions import db
from datetime import datetime
from enum import Enum

class ConsultationStatus(Enum):
    PENDING = "PENDING"
    ASSIGNED = "ASSIGNED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class ConsultationRequest(db.Model):
    __tablename__ = "consultation_requests"

    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey("assessments.id"), nullable=False)
    resident_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    assigned_bhw_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    symptoms = db.Column(db.Text)  # JSON array of symptoms
    risk_level = db.Column(db.String(20), nullable=False)
    status = db.Column(db.Enum(ConsultationStatus), default=ConsultationStatus.PENDING)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    assigned_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)

    # Relationships
    assessment = db.relationship("Assessment", back_populates="consultation_request")
    resident = db.relationship("User", foreign_keys=[resident_id], backref="consultation_requests")
    assigned_bhw = db.relationship("User", foreign_keys=[assigned_bhw_id], backref="assigned_consultations")

    def to_dict(self):
        def get_full_name(user):
            if user and user.health_profile:
                # Try full_name first
                if user.health_profile.full_name:
                    return user.health_profile.full_name
                # Construct from individual parts in "last, first, middle" format
                name_parts = []
                if user.health_profile.last_name and user.health_profile.last_name != 'N/A':
                    name_parts.append(user.health_profile.last_name)
                if user.health_profile.first_name and user.health_profile.first_name != 'N/A':
                    name_parts.append(user.health_profile.first_name)
                if user.health_profile.middle_name and user.health_profile.middle_name != 'N/A':
                    name_parts.append(user.health_profile.middle_name)
                return ', '.join(name_parts) if name_parts else user.username
            return user.username if user else None
        
        def get_bhw_full_name(user):
            if user and user.health_profile:
                # Try full_name first
                if user.health_profile.full_name:
                    return user.health_profile.full_name
                # Construct from individual parts in "last, first, middle" format
                name_parts = []
                if user.health_profile.last_name and user.health_profile.last_name != 'N/A':
                    name_parts.append(user.health_profile.last_name)
                if user.health_profile.first_name and user.health_profile.first_name != 'N/A':
                    name_parts.append(user.health_profile.first_name)
                if user.health_profile.middle_name and user.health_profile.middle_name != 'N/A':
                    name_parts.append(user.health_profile.middle_name)
                return ', '.join(name_parts) if name_parts else user.username
            return user.username if user else None
        
        return {
            "id": self.id,
            "assessment_id": self.assessment_id,
            "resident_id": self.resident_id,
            "assigned_bhw_id": self.assigned_bhw_id,
            "symptoms": self.symptoms,
            "risk_level": self.risk_level,
            "status": self.status.value,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "resident_name": get_full_name(self.resident),
            "resident_barangay": (self.resident.health_profile.barangay if self.resident and self.resident.health_profile else None),
            "resident_contact": (self.resident.health_profile.contact_number if self.resident and self.resident.health_profile else None),
            "assigned_bhw_name": get_bhw_full_name(self.assigned_bhw),
            "referral_id": (self.assessment.referral.id if self.assessment and self.assessment.referral else None),
            "referral_code": (self.assessment.referral.referral_code if self.assessment and self.assessment.referral else None)
        }
