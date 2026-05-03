-- BAYANCARE Database Schema (PostgreSQL)
-- Run this script to create all tables for the system.

-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(128) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'RESIDENT' CHECK (role IN ('RESIDENT', 'BHW', 'ADMIN')),
    is_approved BOOLEAN DEFAULT TRUE NOT NULL
);

-- Health profiles
CREATE TABLE health_profiles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    full_name VARCHAR(200),
    age INTEGER,
    sex VARCHAR(10),
    barangay VARCHAR(100),
    contact_number VARCHAR(50),
    allergies TEXT,
    chronic_conditions TEXT
);

-- Announcements
CREATE TABLE announcements (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    body TEXT NOT NULL,
    category VARCHAR(50) NOT NULL,
    barangay VARCHAR(100) NOT NULL,
    start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_date TIMESTAMP,
    created_by INTEGER NOT NULL REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_emergency BOOLEAN DEFAULT FALSE,
    status VARCHAR(20) DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'ARCHIVED'))
);

-- Assessments
CREATE TABLE assessments (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    risk_level VARCHAR(20) NOT NULL CHECK (risk_level IN ('LOW', 'MODERATE', 'HIGH')),
    assessment_summary TEXT,
    recommendations TEXT,
    temperature FLOAT,
    duration_days INTEGER,
    follow_up_required BOOLEAN DEFAULT FALSE,
    follow_up_date TIMESTAMP,
    status VARCHAR(20) DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'RESOLVED', 'REFERRED')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Assessment symptoms
CREATE TABLE assessment_symptoms (
    id SERIAL PRIMARY KEY,
    assessment_id INTEGER NOT NULL REFERENCES assessments(id) ON DELETE CASCADE,
    symptom_name VARCHAR(100) NOT NULL,
    severity INTEGER
);

-- Follow-ups
CREATE TABLE follow_ups (
    id SERIAL PRIMARY KEY,
    assessment_id INTEGER NOT NULL REFERENCES assessments(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL CHECK (status IN ('IMPROVED', 'SAME', 'WORSENED')),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Referral slips
CREATE TABLE referral_slips (
    id SERIAL PRIMARY KEY,
    assessment_id INTEGER UNIQUE NOT NULL REFERENCES assessments(id) ON DELETE CASCADE,
    referral_code VARCHAR(20) UNIQUE NOT NULL,
    referred_to_center VARCHAR(200) NOT NULL,
    barangay VARCHAR(100) NOT NULL,
    generated_by INTEGER REFERENCES users(id),
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'ATTENDED', 'CLOSED'))
);

-- Indexes for performance
CREATE INDEX idx_assessments_user_id ON assessments(user_id);
CREATE INDEX idx_assessments_created_at ON assessments(created_at);
CREATE INDEX idx_announcements_barangay ON announcements(barangay);
CREATE INDEX idx_announcements_status ON announcements(status);
CREATE INDEX idx_referral_slips_barangay ON referral_slips(barangay);
CREATE INDEX idx_referral_slips_status ON referral_slips(status);
CREATE INDEX idx_follow_ups_assessment_id ON follow_ups(assessment_id);
CREATE INDEX idx_assessment_symptoms_assessment_id ON assessment_symptoms(assessment_id);
