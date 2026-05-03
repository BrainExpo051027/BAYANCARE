from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models.announcement import Announcement, AnnouncementLike
from app.models.user import Role
from app.utils.decorators import role_required
from app.services.notification_service import notify_emergency_announcement, notify_announcement_to_residents
from datetime import datetime
import os
import uuid

announcement_bp = Blueprint("announcement_routes", __name__)

def _auto_archive_ended_events():
    """Auto-archive announcements whose event has ended"""
    active_announcements = Announcement.query.filter_by(status="ACTIVE").all()
    archived_count = 0
    for announcement in active_announcements:
        if announcement.is_event_ended():
            announcement.status = "ARCHIVED"
            archived_count += 1
    if archived_count > 0:
        db.session.commit()
    return archived_count

@announcement_bp.route("", methods=["GET"])
def list_announcements():
    # Auto-archive ended events first
    _auto_archive_ended_events()
    
    # Get barangay filter if provided
    barangay = request.args.get('barangay')
    
    query = Announcement.query.filter_by(status="ACTIVE")
    if barangay:
        query = query.filter_by(barangay=barangay)
    
    announcements = query.order_by(Announcement.created_at.desc()).all()
    
    # Check if user has liked each announcement
    user_likes = set()
    if current_user.is_authenticated:
        likes = AnnouncementLike.query.filter_by(user_id=current_user.id).all()
        user_likes = {like.announcement_id for like in likes}
    
    return jsonify([
        {
            "id": a.id,
            "title": a.title,
            "body": a.body,
            "category": a.category,
            "subcategory": a.subcategory,
            "barangay": a.barangay,
            "created_at": a.created_at.isoformat(),
            "event_start_date": a.event_start_date.isoformat() if a.event_start_date else None,
            "event_end_date": a.event_end_date.isoformat() if a.event_end_date else None,
            "is_emergency": a.is_emergency,
            "image_url": a.image_url,
            "view_count": a.view_count,
            "like_count": a.like_count,
            "user_has_liked": a.id in user_likes,
            "creator_name": a.creator.username if a.creator else "Unknown"
        }
        for a in announcements
    ])

@announcement_bp.route("/archived", methods=["GET"])
@login_required
@role_required(Role.BHW, Role.ADMIN)
def list_archived_announcements():
    """List all archived announcements (for admin/BHW)"""
    barangay = request.args.get('barangay')
    
    query = Announcement.query.filter_by(status="ARCHIVED")
    if barangay:
        query = query.filter_by(barangay=barangay)
    
    announcements = query.order_by(Announcement.created_at.desc()).all()
    
    return jsonify([
        {
            "id": a.id,
            "title": a.title,
            "body": a.body,
            "category": a.category,
            "subcategory": a.subcategory,
            "barangay": a.barangay,
            "created_at": a.created_at.isoformat(),
            "event_start_date": a.event_start_date.isoformat() if a.event_start_date else None,
            "event_end_date": a.event_end_date.isoformat() if a.event_end_date else None,
            "is_emergency": a.is_emergency,
            "image_url": a.image_url,
            "view_count": a.view_count,
            "like_count": a.like_count,
            "creator_name": a.creator.username if a.creator else "Unknown"
        }
        for a in announcements
    ])

@announcement_bp.route("/<int:id>/view", methods=["POST"])
def increment_view_count(id):
    """Increment view count for an announcement"""
    announcement = Announcement.query.get_or_404(id)
    announcement.view_count += 1
    db.session.commit()
    return {"view_count": announcement.view_count}

@announcement_bp.route("/<int:id>/like", methods=["POST"])
@login_required
def like_announcement(id):
    """Like an announcement"""
    announcement = Announcement.query.get_or_404(id)
    
    # Check if already liked
    existing_like = AnnouncementLike.query.filter_by(
        announcement_id=id, 
        user_id=current_user.id
    ).first()
    
    if existing_like:
        return {"error": "Already liked"}, 400
    
    # Create like
    like = AnnouncementLike(announcement_id=id, user_id=current_user.id)
    db.session.add(like)
    
    # Increment count
    announcement.like_count += 1
    db.session.commit()
    
    return {"like_count": announcement.like_count, "liked": True}

@announcement_bp.route("/<int:id>/unlike", methods=["POST"])
@login_required
def unlike_announcement(id):
    """Unlike an announcement"""
    announcement = Announcement.query.get_or_404(id)
    
    # Find and remove like
    like = AnnouncementLike.query.filter_by(
        announcement_id=id, 
        user_id=current_user.id
    ).first()
    
    if not like:
        return {"error": "Not liked yet"}, 400
    
    db.session.delete(like)
    
    # Decrement count
    announcement.like_count = max(0, announcement.like_count - 1)
    db.session.commit()
    
    return {"like_count": announcement.like_count, "liked": False}

@announcement_bp.route("", methods=["POST"])
@login_required
@role_required(Role.BHW, Role.ADMIN)
def create_announcement():
    is_multipart = request.content_type and "multipart/form-data" in request.content_type
    if is_multipart:
        data = request.form
    else:
        data = request.get_json() or {}

    image_url = None
    if is_multipart and "image" in request.files:
        file = request.files.get("image")
        if file and file.filename:
            ext = os.path.splitext(file.filename)[1].lower()
            safe_ext = ext if ext in (".png", ".jpg", ".jpeg", ".webp") else ""
            filename = f"{uuid.uuid4().hex}{safe_ext}"
            upload_dir = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "..", "frontend", "assets", "uploads", "announcements")
            )
            os.makedirs(upload_dir, exist_ok=True)
            file_path = os.path.join(upload_dir, filename)
            file.save(file_path)
            image_url = f"/assets/uploads/announcements/{filename}"

    # Parse event dates
    event_start_date = None
    event_end_date = None
    if data.get("event_start_date"):
        try:
            event_start_date = datetime.fromisoformat(data.get("event_start_date").replace('Z', '+00:00').replace('+00:00', ''))
            # Validate that event start date is not in the past
            if event_start_date.date() < datetime.utcnow().date():
                return {"error": "Event start date cannot be in the past. Please select today or a future date."}, 400
        except:
            pass
    if data.get("event_end_date"):
        try:
            event_end_date = datetime.fromisoformat(data.get("event_end_date").replace('Z', '+00:00').replace('+00:00', ''))
        except:
            pass

    announcement = Announcement(
        title=data.get("title"),
        body=data.get("body"),
        category=data.get("category"),
        subcategory=data.get("subcategory"),
        barangay=data.get("barangay"),
        event_start_date=event_start_date,
        event_end_date=event_end_date,
        is_emergency=(str(data.get("is_emergency", "")).lower() in ("true", "1", "on", "yes")) if is_multipart else data.get("is_emergency", False),
        image_url=image_url,
        created_by=current_user.id
    )
    db.session.add(announcement)
    db.session.commit()
    
    # Notify all residents in the barangay
    notify_announcement_to_residents(
        barangay=announcement.barangay,
        title=announcement.title,
        body=announcement.body,
        is_emergency=announcement.is_emergency
    )
    
    return {"message": "Announcement created and notifications sent", "id": announcement.id}, 201

@announcement_bp.route("/<int:id>", methods=["PUT"])
@login_required
@role_required(Role.BHW, Role.ADMIN)
def update_announcement(id):
    announcement = Announcement.query.get_or_404(id)
    data = request.get_json()
    announcement.title = data.get("title", announcement.title)
    announcement.body = data.get("body", announcement.body)
    announcement.category = data.get("category", announcement.category)
    announcement.subcategory = data.get("subcategory", announcement.subcategory)
    announcement.barangay = data.get("barangay", announcement.barangay)
    announcement.is_emergency = data.get("is_emergency", announcement.is_emergency)
    
    # Update event dates
    if "event_start_date" in data:
        try:
            new_start_date = datetime.fromisoformat(data.get("event_start_date").replace('Z', '+00:00').replace('+00:00', ''))
            # Validate that event start date is not in the past
            if new_start_date.date() < datetime.utcnow().date():
                return {"error": "Event start date cannot be in the past. Please select today or a future date."}, 400
            announcement.event_start_date = new_start_date
        except:
            announcement.event_start_date = None
    if "event_end_date" in data:
        try:
            announcement.event_end_date = datetime.fromisoformat(data.get("event_end_date").replace('Z', '+00:00').replace('+00:00', ''))
        except:
            announcement.event_end_date = None
    
    db.session.commit()
    if announcement.is_emergency:
        notify_emergency_announcement(announcement.barangay, announcement.title, announcement.body)
    return {"message": "Announcement updated"}

@announcement_bp.route("/<int:id>", methods=["DELETE"])
@login_required
@role_required(Role.BHW, Role.ADMIN)
def delete_announcement(id):
    announcement = Announcement.query.get_or_404(id)
    announcement.status = "ARCHIVED"
    db.session.commit()
    return {"message": "Announcement archived"}

@announcement_bp.route("/<int:id>/restore", methods=["POST"])
@login_required
@role_required(Role.BHW, Role.ADMIN)
def restore_announcement(id):
    """Restore an archived announcement"""
    announcement = Announcement.query.get_or_404(id)
    announcement.status = "ACTIVE"
    announcement.created_at = datetime.utcnow()
    
    # Reset stats so it acts completely like a new announcement
    announcement.view_count = 0
    announcement.like_count = 0
    AnnouncementLike.query.filter_by(announcement_id=id).delete()
    
    # Clear event dates if they have already passed to prevent immediate auto-archiving
    if announcement.is_event_ended():
        announcement.event_start_date = None
        announcement.event_end_date = None

    db.session.commit()
    
    # Notify all residents in the barangay
    notify_announcement_to_residents(
        barangay=announcement.barangay,
        title=announcement.title,
        body=announcement.body,
        is_emergency=announcement.is_emergency
    )
    
    return {"message": "Announcement restored and notifications sent"}

@announcement_bp.route("/<int:id>/permanent", methods=["DELETE"])
@login_required
@role_required(Role.BHW, Role.ADMIN)
def permanent_delete_announcement(id):
    announcement = Announcement.query.get_or_404(id)
    # Delete associated likes
    AnnouncementLike.query.filter_by(announcement_id=id).delete()
    db.session.delete(announcement)
    db.session.commit()
    return {"message": "Announcement permanently deleted"}
