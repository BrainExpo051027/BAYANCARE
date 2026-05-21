"""Barangay-scoped authorization helpers for BHW users."""

from flask_login import current_user
from app.extensions import db
from app.models.user import Role, User
from app.models.health_profile import HealthProfile
from app.models.consultation_request import ConsultationRequest
from app.models.assessment import Assessment


def normalize_barangay(value):
    """Normalize barangay for consistent comparison."""
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.upper() == "N/A":
        return None
    return text.lower()


def get_user_barangay(user):
    if not user or not user.health_profile:
        return None
    return normalize_barangay(user.health_profile.barangay)


def get_current_bhw_barangay():
    if not current_user.is_authenticated or current_user.role != Role.BHW:
        return None
    return get_user_barangay(current_user)


def is_admin_user():
    return current_user.is_authenticated and current_user.role == Role.ADMIN


def resident_in_bhw_barangay(target_user):
    bhw_barangay = get_current_bhw_barangay()
    if not bhw_barangay:
        return False
    return get_user_barangay(target_user) == bhw_barangay


def can_bhw_access_user(target_user):
    if is_admin_user():
        return True
    if current_user.role != Role.BHW:
        return False
    return resident_in_bhw_barangay(target_user)


def deny_bhw_out_of_scope():
    return {"error": "Access denied: resident outside your assigned barangay"}, 403


def can_bhw_access_assessment(assessment):
    if is_admin_user():
        return True
    if current_user.role != Role.BHW or not assessment:
        return False
    return resident_in_bhw_barangay(assessment.user)


def can_bhw_access_consultation(consultation):
    if is_admin_user():
        return True
    if current_user.role != Role.BHW or not consultation:
        return False
    if consultation.assigned_bhw_id == current_user.id:
        return True
    return resident_in_bhw_barangay(consultation.resident)


def filter_users_query_by_bhw_scope(query):
    """Restrict a User query to residents in the current BHW's barangay."""
    if is_admin_user():
        return query
    if current_user.role != Role.BHW:
        return query
    bhw_barangay = get_current_bhw_barangay()
    if not bhw_barangay:
        return query.filter(db.false())
    return query.filter(db.func.lower(HealthProfile.barangay) == bhw_barangay)


def filter_consultations_query_by_bhw_scope(query):
    """Restrict consultations to assigned BHW or resident in same barangay."""
    if is_admin_user():
        return query
    if current_user.role != Role.BHW:
        return query
    bhw_barangay = get_current_bhw_barangay()
    if not bhw_barangay:
        return query.filter(db.false())
    return (
        query.join(User, ConsultationRequest.resident_id == User.id)
        .outerjoin(HealthProfile, HealthProfile.user_id == User.id)
        .filter(
            db.or_(
                ConsultationRequest.assigned_bhw_id == current_user.id,
                db.func.lower(HealthProfile.barangay) == bhw_barangay,
            )
        )
    )


def filter_assessments_query_by_bhw_scope(query):
    """Restrict assessments to residents in the current BHW's barangay."""
    if is_admin_user():
        return query
    if current_user.role != Role.BHW:
        return query
    bhw_barangay = get_current_bhw_barangay()
    if not bhw_barangay:
        return query.filter(db.false())
    return (
        query.join(User, Assessment.user_id == User.id)
        .outerjoin(HealthProfile, HealthProfile.user_id == User.id)
        .filter(db.func.lower(HealthProfile.barangay) == bhw_barangay)
    )
