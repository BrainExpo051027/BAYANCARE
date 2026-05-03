from app.extensions import db
from datetime import datetime

class Announcement(db.Model):
    __tablename__ = "announcements"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)  # e.g., Vaccination, Checkup, Emergency
    subcategory = db.Column(db.String(120), nullable=True)
    barangay = db.Column(db.String(100), nullable=False)
    # NOTE: Keep DB column names as start_date/end_date for backward compatibility.
    # Expose event_start_date/event_end_date via synonyms for the frontend/API.
    start_date = db.Column(db.DateTime, nullable=True)  # When the program/event starts
    end_date = db.Column(db.DateTime, nullable=True)   # When the program/event ends
    event_start_date = db.synonym("start_date")
    event_end_date = db.synonym("end_date")
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_emergency = db.Column(db.Boolean, default=False)
    image_url = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default="ACTIVE")  # ACTIVE, ARCHIVED
    view_count = db.Column(db.Integer, default=0)
    like_count = db.Column(db.Integer, default=0)

    # Relationships
    creator = db.relationship("User", backref="announcements_created")
    likes = db.relationship("AnnouncementLike", backref="announcement", cascade="all, delete-orphan")

    def is_event_ended(self):
        """Check if the event has ended (for auto-archive)"""
        if self.end_date:
            return datetime.utcnow() > self.end_date
        return False


class AnnouncementLike(db.Model):
    __tablename__ = "announcement_likes"
    
    id = db.Column(db.Integer, primary_key=True)
    announcement_id = db.Column(db.Integer, db.ForeignKey("announcements.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Unique constraint - one like per user per announcement
    __table_args__ = (db.UniqueConstraint('announcement_id', 'user_id', name='unique_user_like'),)
    
    # Relationships
    user = db.relationship("User", backref="announcement_likes")
