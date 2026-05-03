from app.extensions import db
from enum import Enum

class Role(Enum):
    RESIDENT = "RESIDENT"
    BHW = "BHW"
    ADMIN = "ADMIN"

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.Enum(Role), nullable=False, default=Role.RESIDENT)
    is_approved = db.Column(db.Boolean, default=True, nullable=False)

    # Relationships
    health_profile = db.relationship("HealthProfile", back_populates="user", uselist=False)
    assessments = db.relationship("Assessment", back_populates="user")

    def set_password(self, password):
        from app.extensions import bcrypt
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password):
        from app.extensions import bcrypt
        return bcrypt.check_password_hash(self.password_hash, password)

    # Flask-Login required properties
    @property
    def is_active(self):
        return True

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

    def __repr__(self):
        return f"<User {self.username} ({self.role.value})>"
