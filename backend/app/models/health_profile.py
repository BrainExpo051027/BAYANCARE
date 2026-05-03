from app.extensions import db

class HealthProfile(db.Model):
    __tablename__ = "health_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    
    # I. PERSONAL IDENTIFICATION
    full_name = db.Column(db.String(200))
    last_name = db.Column(db.String(100))
    first_name = db.Column(db.String(100))
    middle_name = db.Column(db.String(100))
    date_of_birth = db.Column(db.Date)
    age = db.Column(db.Integer)
    sex = db.Column(db.String(10))
    civil_status = db.Column(db.String(50))
    address = db.Column(db.Text)
    barangay = db.Column(db.String(100))
    contact_number = db.Column(db.String(50))
    philhealth_id = db.Column(db.String(100))
    
    # II. MEDICAL HISTORY & SOCIAL DETERMINANTS
    blood_type = db.Column(db.String(10))
    pwd_id = db.Column(db.String(100))
    allergies = db.Column(db.Text)
    chronic_conditions = db.Column(db.Text)
    current_medications = db.Column(db.Text)
    lifestyle = db.Column(db.String(200))  # Smoker/Alcohol
    household_details = db.Column(db.Text)  # Water Source/Toilet Facility
    
    # III. PUBLIC HEALTH PROGRAM STATUS
    covid_vaccination = db.Column(db.Text)  # 1st, 2nd, Booster/s
    other_immunizations = db.Column(db.Text)  # Flu, Pneumococcal
    maternal_child_health = db.Column(db.Text)  # Immunization/Nutritional Status
    
    # IV. EMERGENCY CONTACT INFO & CERTIFICATION
    emergency_contact_person = db.Column(db.String(200))
    emergency_contact_relationship = db.Column(db.String(100))
    emergency_contact_number = db.Column(db.String(50))
    processed_by_bhw = db.Column(db.String(200))
    processed_date = db.Column(db.Date)
    
    # Relationships
    user = db.relationship("User", back_populates="health_profile")
