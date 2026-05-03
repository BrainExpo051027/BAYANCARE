"""
Unified Database Migration Script for BAYANCARE

This script consolidates all database migrations into one file.
Run this to set up or update the entire database schema.

Usage:
    python migrate_all.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = create_app()


def table_exists(table_name):
    """Check if a table exists in the database"""
    try:
        result = db.session.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = :table_name
            )
        """), {'table_name': table_name})
        return result.scalar()
    except Exception as e:
        logger.error(f"Error checking table {table_name}: {e}")
        return False


def column_exists(table_name, column_name):
    """Check if a column exists in a table"""
    try:
        result = db.session.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name = :table_name AND column_name = :column_name
            )
        """), {'table_name': table_name, 'column_name': column_name})
        return result.scalar()
    except Exception as e:
        logger.error(f"Error checking column {column_name} in {table_name}: {e}")
        return False


def create_tables():
    """Create all required tables if they don't exist"""
    
    # 1. Create follow_up_notifications table
    if not table_exists('follow_up_notifications'):
        db.session.execute(text("""
            CREATE TABLE follow_up_notifications (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                assessment_id INTEGER NOT NULL REFERENCES assessments(id),
                notification_date TIMESTAMP NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
                user_response TEXT,
                auto_referral_generated BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                responded_at TIMESTAMP
            )
        """))
        logger.info("✓ Created follow_up_notifications table")
    else:
        logger.info("- follow_up_notifications table already exists")
    
    # 2. Create consultation_requests table
    if not table_exists('consultation_requests'):
        db.session.execute(text("""
            CREATE TABLE consultation_requests (
                id SERIAL PRIMARY KEY,
                assessment_id INTEGER NOT NULL REFERENCES assessments(id),
                resident_id INTEGER NOT NULL REFERENCES users(id),
                assigned_bhw_id INTEGER REFERENCES users(id),
                symptoms TEXT,
                risk_level VARCHAR(20) NOT NULL,
                status VARCHAR(20) DEFAULT 'PENDING',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                assigned_at TIMESTAMP,
                completed_at TIMESTAMP
            )
        """))
        logger.info("✓ Created consultation_requests table")
    else:
        logger.info("- consultation_requests table already exists")
    
    # 3. Create announcement_likes table
    if not table_exists('announcement_likes'):
        db.session.execute(text("""
            CREATE TABLE announcement_likes (
                id SERIAL PRIMARY KEY,
                announcement_id INTEGER NOT NULL REFERENCES announcements(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at TIMESTAMP DEFAULT NOW(),
                CONSTRAINT unique_user_like UNIQUE (announcement_id, user_id)
            )
        """))
        logger.info("✓ Created announcement_likes table")
    else:
        logger.info("- announcement_likes table already exists")


def migrate_assessments_table():
    """Add columns to assessments table"""
    columns = [
        ('predicted_condition', 'VARCHAR(255)'),
        ('confidence_score', 'FLOAT'),
        ('home_care_plan', 'JSON'),
        ('recovery_start_date', 'TIMESTAMP'),
        ('recovery_end_date', 'TIMESTAMP'),
        ('recovery_notified', 'BOOLEAN DEFAULT FALSE'),
        ('recovery_notification_sent_at', 'TIMESTAMP'),
    ]
    
    for col_name, col_type in columns:
        if not column_exists('assessments', col_name):
            db.session.execute(text(f"""
                ALTER TABLE assessments 
                ADD COLUMN {col_name} {col_type}
            """))
            logger.info(f"✓ Added {col_name} to assessments")
        else:
            logger.info(f"- {col_name} already exists in assessments")


def migrate_users_table():
    """Add columns to users table"""
    if not column_exists('users', 'is_approved'):
        db.session.execute(text("""
            ALTER TABLE users 
            ADD COLUMN is_approved BOOLEAN DEFAULT TRUE NOT NULL
        """))
        logger.info("✓ Added is_approved to users")
    else:
        logger.info("- is_approved already exists in users")


def migrate_referral_slips_table():
    """Add columns to referral_slips table"""
    columns = [
        ('generated_by_bhw_id', 'INTEGER REFERENCES users(id)'),
        ('symptoms', 'TEXT'),
        ('expires_at', 'TIMESTAMP'),
        ('created_by', 'INTEGER REFERENCES users(id)'),
        ('created_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
        ('is_auto_generated', 'BOOLEAN DEFAULT FALSE'),
    ]
    
    for col_name, col_type in columns:
        if not column_exists('referral_slips', col_name):
            db.session.execute(text(f"""
                ALTER TABLE referral_slips 
                ADD COLUMN {col_name} {col_type}
            """))
            logger.info(f"✓ Added {col_name} to referral_slips")
        else:
            logger.info(f"- {col_name} already exists in referral_slips")


def migrate_health_profiles_table():
    """Add columns to health_profiles table"""
    columns = [
        # I. Personal Identification
        ('last_name', 'VARCHAR(100)'),
        ('first_name', 'VARCHAR(100)'),
        ('middle_name', 'VARCHAR(100)'),
        ('date_of_birth', 'DATE'),
        ('civil_status', 'VARCHAR(50)'),
        ('address', 'TEXT'),
        ('philhealth_id', 'VARCHAR(100)'),
        # II. Medical History & Social Determinants
        ('blood_type', 'VARCHAR(10)'),
        ('pwd_id', 'VARCHAR(100)'),
        ('current_medications', 'TEXT'),
        ('lifestyle', 'VARCHAR(200)'),
        ('household_details', 'TEXT'),
        # III. Public Health Program Status
        ('covid_vaccination', 'TEXT'),
        ('other_immunizations', 'TEXT'),
        ('maternal_child_health', 'TEXT'),
        # IV. Emergency Contact Info
        ('emergency_contact_person', 'VARCHAR(200)'),
        ('emergency_contact_relationship', 'VARCHAR(100)'),
        ('emergency_contact_number', 'VARCHAR(50)'),
        ('processed_by_bhw', 'VARCHAR(200)'),
        ('processed_date', 'DATE'),
    ]
    
    for col_name, col_type in columns:
        if not column_exists('health_profiles', col_name):
            db.session.execute(text(f"""
                ALTER TABLE health_profiles 
                ADD COLUMN {col_name} {col_type}
            """))
            logger.info(f"✓ Added {col_name} to health_profiles")
        else:
            logger.info(f"- {col_name} already exists in health_profiles")


def migrate_announcements_table():
    """Add columns to announcements table"""
    columns = [
        ('subcategory', 'VARCHAR(120)'),
        ('image_url', 'TEXT'),
        ('start_date', 'TIMESTAMP'),
        ('end_date', 'TIMESTAMP'),
        ('view_count', 'INTEGER DEFAULT 0'),
        ('like_count', 'INTEGER DEFAULT 0'),
    ]
    
    for col_name, col_type in columns:
        if not column_exists('announcements', col_name):
            db.session.execute(text(f"""
                ALTER TABLE announcements 
                ADD COLUMN {col_name} {col_type}
            """))
            logger.info(f"✓ Added {col_name} to announcements")
        else:
            logger.info(f"- {col_name} already exists in announcements")


def main():
    """Run all migrations"""
    with app.app_context():
        logger.info("=" * 60)
        logger.info("Starting BAYANCARE Database Migration")
        logger.info("=" * 60)
        
        try:
            create_tables()
            migrate_assessments_table()
            migrate_users_table()
            migrate_referral_slips_table()
            migrate_health_profiles_table()
            migrate_announcements_table()
            
            db.session.commit()
            logger.info("=" * 60)
            logger.info("✅ Database migration completed successfully!")
            logger.info("=" * 60)
            logger.info("\nYou can now restart your backend.")
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"❌ Migration failed: {e}")
            raise


if __name__ == "__main__":
    main()
