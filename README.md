# BAYANCARE: Barangay-Assisted Analysis and Navigation for Community Health System

## Quick Start

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Create a PostgreSQL database named `bayancare_db`.

3. Set your database URL (optional, defaults to `postgresql://user:password@localhost/bayancare_db`):
   ```bash
   export DATABASE_URL="postgresql://youruser:yourpass@localhost/bayancare_db"
   ```

4. Run the backend:
   ```bash
   python backend/run.py
   ```

5. Verify health check:
   ```bash
   curl http://127.0.0.1:5000/api/health
   ```

## Project Structure

- `backend/` — Flask application (Python)
  - `run.py` — entry point
  - `app/` — application package
    - `config/` — configuration
    - `extensions/` — Flask extensions (db, bcrypt, login_manager)
    - `models/` — database models (User, Assessment, etc.)
    - `routes/` — API blueprints
    - `services/` — business logic (risk_engine, etc.)
    - `utils/` — helpers (security, validators, pdf)
- `frontend/` — HTML/CSS/JS (to be added)
- `database/` — SQL scripts, migrations (to be added)
- `docs/` — project documentation (to be added)
- `tests/` — unit tests (to be added)

## API Endpoints (Implemented)

- `GET /api/health` — health check
- `POST /api/auth/register` — register a user
- `POST /api/auth/login` — login a user
- `POST /api/assessments` — submit a symptom assessment (risk analysis)

## Next Steps

- Fill in remaining blueprints (announcements, follow-ups, referrals, profile).
- Add frontend pages that call these APIs.
- Create database schema/migration scripts.
- Add authentication sessions and role-based access control.
