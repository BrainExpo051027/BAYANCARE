from app.extensions import db
from datetime import datetime, timedelta

class ReferralSlip(db.Model):
    __tablename__ = "referral_slips"

    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey("assessments.id"), nullable=False)
    referral_code = db.Column(db.String(20), unique=True, nullable=False)
    referred_to_center = db.Column(db.String(200), nullable=False)
    barangay = db.Column(db.String(100), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))  # Unified creator field
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default="PENDING")  # PENDING, ATTENDED, CLOSED, EXPIRED
    is_auto_generated = db.Column(db.Boolean, default=False)  # Flag for auto-generated referrals
    
    # Additional fields
    symptoms = db.Column(db.Text)  # JSON string of symptoms
    expires_at = db.Column(db.DateTime)  # Referral expiration date

    # Relationships
    assessment = db.relationship("Assessment", back_populates="referral")
    creator = db.relationship("User", foreign_keys=[created_by], backref="referrals_created")

    def is_expired(self):
        """Check if the referral has expired."""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    def auto_expire(self):
        """Auto-expire the referral if past expiration date."""
        if self.is_expired() and self.status == "PENDING":
            self.status = "EXPIRED"
            return True
        return False
