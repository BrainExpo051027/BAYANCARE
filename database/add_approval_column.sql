-- Add is_approved column to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_approved BOOLEAN DEFAULT TRUE NOT NULL;
