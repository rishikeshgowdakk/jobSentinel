import psycopg2
import sqlite3
import os
import json
from src.core.config import config
from src.core.logger import logger

class Database:
    def __init__(self):
        self.conn = None
        self.is_sqlite = False
        self._connect()

    def _connect(self):
        try:
            # Try PostgreSQL first
            self.conn = psycopg2.connect(
                dbname=config.DB_NAME,
                user=config.DB_USER,
                password=config.DB_PASSWORD,
                host=config.DB_HOST,
                port=config.DB_PORT,
                connect_timeout=3
            )
            logger.info("Connected to PostgreSQL")
            self._create_table()
        except Exception as e:
            logger.warning(f"PostgreSQL connection failed, falling back to SQLite: {e}")
            self._connect_sqlite()

    def _connect_sqlite(self):
        try:
            db_path = os.path.join(os.getcwd(), "jobsentinel.db")
            self.conn = sqlite3.connect(db_path, check_same_thread=False)
            self.is_sqlite = True
            logger.info(f"Connected to SQLite: {db_path}")
            self._create_table()
        except Exception as e:
            logger.error(f"Failed to connect to SQLite: {e}")

    def _create_table(self):
        # We always want our new schemas, so we check or rebuild to support multi-user isolation
        try:
            cur = self.conn.cursor()
            if self.is_sqlite:
                cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='resume_profile'")
                exists = cur.fetchone()
                if exists:
                    # Let's check if 'user_id' is present. If not, drop to update
                    cur.execute("PRAGMA table_info(resume_profile)")
                    cols = [c[1] for c in cur.fetchall()]
                    if "user_id" not in cols:
                        logger.info("Dropping old SQLite tables to migrate to multi-user isolated schema...")
                        cur.execute("DROP TABLE IF EXISTS settings")
                        cur.execute("DROP TABLE IF EXISTS resume_profile")
                        cur.execute("DROP TABLE IF EXISTS processed_jobs")
                        cur.execute("DROP TABLE IF EXISTS job_matches")
                        cur.execute("DROP TABLE IF EXISTS applications")
            else:
                cur.execute("SELECT table_name FROM information_schema.tables WHERE table_name='resume_profile'")
                exists = cur.fetchone()
                if exists:
                    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='resume_profile' AND column_name='user_id'")
                    col_exists = cur.fetchone()
                    if not col_exists:
                        logger.info("Dropping old Postgres tables to migrate to multi-user isolated schema...")
                        cur.execute("DROP TABLE IF EXISTS settings CASCADE")
                        cur.execute("DROP TABLE IF EXISTS resume_profile CASCADE")
                        cur.execute("DROP TABLE IF EXISTS processed_jobs CASCADE")
                        cur.execute("DROP TABLE IF EXISTS job_matches CASCADE")
                        cur.execute("DROP TABLE IF EXISTS applications CASCADE")
            self.conn.commit()
            cur.close()
        except Exception as e:
            logger.warning(f"Error checking/migrating schema: {e}")

        queries = [
            """
            CREATE TABLE IF NOT EXISTS settings (
                user_id VARCHAR(255),
                key VARCHAR(255),
                value TEXT,
                PRIMARY KEY (user_id, key)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS resume_profile (
                user_id VARCHAR(255) PRIMARY KEY,
                raw_text TEXT,
                structured_data TEXT,
                embedding TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS processed_jobs (
                job_id VARCHAR(255) PRIMARY KEY,
                title TEXT,
                company TEXT,
                location TEXT,
                remote_status TEXT,
                salary TEXT,
                experience TEXT,
                skills TEXT,
                description TEXT,
                url TEXT,
                source TEXT,
                company_size TEXT,
                industry TEXT,
                posting_date TEXT,
                visa_sponsorship TEXT,
                recruiter_link TEXT,
                embedding TEXT,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS job_matches (
                user_id VARCHAR(255),
                job_id VARCHAR(255),
                match_score INTEGER,
                confidence REAL,
                matched_skills TEXT,
                missing_skills TEXT,
                recommendation_reason TEXT,
                priority VARCHAR(50),
                apply_immediately BOOLEAN,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, job_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS applications (
                user_id VARCHAR(255),
                job_id VARCHAR(255),
                status VARCHAR(100) DEFAULT 'applied',
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, job_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS payments (
                utr VARCHAR(255) PRIMARY KEY,
                user_id VARCHAR(255),
                amount REAL,
                status VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        ]
        
        for query in queries:
            if self.is_sqlite:
                query = query.replace("SERIAL PRIMARY KEY", "INTEGER PRIMARY KEY AUTOINCREMENT")
                query = query.replace("DEFAULT CURRENT_TIMESTAMP", "DEFAULT (datetime('now','localtime'))")
                
            try:
                cur = self.conn.cursor()
                cur.execute(query)
                self.conn.commit()
                cur.close()
            except Exception as e:
                logger.error(f"Error creating table: {e}")

    def get_setting(self, user_id: str, key: str, default: str = None) -> str:
        query = "SELECT value FROM settings WHERE user_id = ? AND key = ?" if self.is_sqlite else "SELECT value FROM settings WHERE user_id = %s AND key = %s"
        try:
            cur = self.conn.cursor()
            cur.execute(query, (user_id, key))
            row = cur.fetchone()
            cur.close()
            return row[0] if row else default
        except Exception as e:
            logger.error(f"Error fetching setting {key} for user {user_id}: {e}")
            return default

    def set_setting(self, user_id: str, key: str, value: str):
        if self.is_sqlite:
            query = "INSERT OR REPLACE INTO settings (user_id, key, value) VALUES (?, ?, ?)"
        else:
            query = "INSERT INTO settings (user_id, key, value) VALUES (%s, %s, %s) ON CONFLICT (user_id, key) DO UPDATE SET value = EXCLUDED.value"
            
        try:
            cur = self.conn.cursor()
            cur.execute(query, (user_id, key, value))
            self.conn.commit()
            cur.close()
        except Exception as e:
            logger.error(f"Error setting {key} for user {user_id}: {e}")
            if self.conn:
                self.conn.rollback()

    def save_profile(self, user_id: str, raw_text: str, structured_data: dict, embedding: list = None):
        try:
            cur = self.conn.cursor()
            embedding_str = json.dumps(embedding) if embedding else ""
            sd_str = json.dumps(structured_data)
            
            if self.is_sqlite:
                query = "INSERT OR REPLACE INTO resume_profile (user_id, raw_text, structured_data, embedding) VALUES (?, ?, ?, ?)"
            else:
                query = """
                    INSERT INTO resume_profile (user_id, raw_text, structured_data, embedding) 
                    VALUES (%s, %s, %s, %s) 
                    ON CONFLICT (user_id) 
                    DO UPDATE SET raw_text = EXCLUDED.raw_text, structured_data = EXCLUDED.structured_data, embedding = EXCLUDED.embedding
                """
                
            cur.execute(query, (user_id, raw_text, sd_str, embedding_str))
            self.conn.commit()
            cur.close()
            logger.info(f"Resume profile saved successfully for user {user_id}.")
        except Exception as e:
            logger.error(f"Error saving resume profile for user {user_id}: {e}")
            if self.conn:
                self.conn.rollback()

    def get_profile(self, user_id: str) -> dict:
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT raw_text, structured_data, embedding FROM resume_profile WHERE user_id = ?", (user_id,))
            row = cur.fetchone()
            cur.close()
            if row:
                return {
                    "raw_text": row[0],
                    "structured_data": json.loads(row[1]) if row[1] else {},
                    "embedding": json.loads(row[2]) if row[2] else []
                }
            return None
        except Exception as e:
            logger.error(f"Error fetching resume profile for user {user_id}: {e}")
            return None

    def get_all_users_profiles(self) -> list:
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT user_id, raw_text, structured_data, embedding FROM resume_profile")
            rows = cur.fetchall()
            cur.close()
            profiles = []
            for row in rows:
                profiles.append({
                    "user_id": row[0],
                    "raw_text": row[1],
                    "structured_data": json.loads(row[2]) if row[2] else {},
                    "embedding": json.loads(row[3]) if row[3] else []
                })
            return profiles
        except Exception as e:
            logger.error(f"Error fetching all user profiles: {e}")
            return []

    def get_user_preferences(self, user_id: str) -> dict:
        return {
            "keywords": self.get_setting(user_id, "keywords", config.JOB_KEYWORDS),
            "locations": self.get_setting(user_id, "locations", config.JOB_LOCATIONS),
            "job_type": self.get_setting(user_id, "job_type", "All"),
            "experience_level": self.get_setting(user_id, "experience_level", "All")
        }

    def job_exists(self, job_id: str) -> bool:
        query = "SELECT 1 FROM processed_jobs WHERE job_id = ?" if self.is_sqlite else "SELECT 1 FROM processed_jobs WHERE job_id = %s"
        try:
            cur = self.conn.cursor()
            cur.execute(query, (job_id,))
            exists = cur.fetchone() is not None
            cur.close()
            return exists
        except Exception as e:
            logger.error(f"Error checking job existence: {e}")
            return False

    def add_job(self, job_data: dict, embedding: list = None):
        try:
            if self.is_sqlite:
                query = """
                    INSERT INTO processed_jobs (
                        job_id, title, company, location, remote_status, salary, 
                        experience, skills, description, url, source, company_size, 
                        industry, posting_date, visa_sponsorship, recruiter_link, embedding
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(job_id) DO UPDATE SET
                        title = excluded.title, company = excluded.company, location = excluded.location,
                        remote_status = excluded.remote_status, salary = excluded.salary, 
                        experience = excluded.experience, skills = excluded.skills, 
                        description = excluded.description, url = excluded.url, source = excluded.source
                """
            else:
                query = """
                    INSERT INTO processed_jobs (
                        job_id, title, company, location, remote_status, salary, 
                        experience, skills, description, url, source, company_size, 
                        industry, posting_date, visa_sponsorship, recruiter_link, embedding
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT(job_id) DO UPDATE SET
                        title = EXCLUDED.title, company = EXCLUDED.company, location = EXCLUDED.location,
                        remote_status = EXCLUDED.remote_status, salary = EXCLUDED.salary, 
                        experience = EXCLUDED.experience, skills = EXCLUDED.skills, 
                        description = EXCLUDED.description, url = EXCLUDED.url, source = EXCLUDED.source
                """
            embedding_str = json.dumps(embedding) if embedding else ""
            params = (
                job_data['job_id'],
                job_data['title'],
                job_data['company'],
                job_data.get('location', ''),
                job_data.get('remote_status', ''),
                job_data.get('salary', ''),
                job_data.get('experience', ''),
                job_data.get('skills', ''),
                job_data.get('description', ''),
                job_data['url'],
                job_data.get('source', ''),
                job_data.get('company_size', ''),
                job_data.get('industry', ''),
                job_data.get('posting_date', ''),
                job_data.get('visa_sponsorship', ''),
                job_data.get('recruiter_link', ''),
                embedding_str
            )
            cur = self.conn.cursor()
            cur.execute(query, params)
            self.conn.commit()
            cur.close()
        except Exception as e:
            logger.error(f"Error adding job: {e}")
            if self.conn:
                self.conn.rollback()

    def save_match(self, user_id: str, match_data: dict):
        try:
            if self.is_sqlite:
                query = """
                    INSERT INTO job_matches (
                        user_id, job_id, match_score, confidence, matched_skills, 
                        missing_skills, recommendation_reason, priority, apply_immediately
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(user_id, job_id) DO UPDATE SET
                        match_score = excluded.match_score, confidence = excluded.confidence,
                        matched_skills = excluded.matched_skills, missing_skills = excluded.missing_skills,
                        recommendation_reason = excluded.recommendation_reason, priority = excluded.priority,
                        apply_immediately = excluded.apply_immediately, updated_at = CURRENT_TIMESTAMP
                """
            else:
                query = """
                    INSERT INTO job_matches (
                        user_id, job_id, match_score, confidence, matched_skills, 
                        missing_skills, recommendation_reason, priority, apply_immediately
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT(user_id, job_id) DO UPDATE SET
                        match_score = EXCLUDED.match_score, confidence = EXCLUDED.confidence,
                        matched_skills = EXCLUDED.matched_skills, missing_skills = EXCLUDED.missing_skills,
                        recommendation_reason = EXCLUDED.recommendation_reason, priority = EXCLUDED.priority,
                        apply_immediately = EXCLUDED.apply_immediately, updated_at = CURRENT_TIMESTAMP
                """
            params = (
                user_id,
                match_data['job_id'],
                match_data.get('matchScore', 0),
                match_data.get('confidence', 1.0),
                ", ".join(match_data.get('matchedSkills', [])) if isinstance(match_data.get('matchedSkills'), list) else match_data.get('matchedSkills', ''),
                ", ".join(match_data.get('missingSkills', [])) if isinstance(match_data.get('missingSkills'), list) else match_data.get('missingSkills', ''),
                match_data.get('recommendationReason', ''),
                match_data.get('priority', 'Medium'),
                1 if match_data.get('applyImmediately', False) else 0
            )
            cur = self.conn.cursor()
            cur.execute(query, params)
            self.conn.commit()
            cur.close()
        except Exception as e:
            logger.error(f"Error saving match for user {user_id}: {e}")
            if self.conn:
                self.conn.rollback()

    def get_recent_jobs(self, user_id: str, limit=50):
        # Joins processed_jobs, job_matches, and applications to get a complete user-specific view
        query = """
            SELECT 
                j.job_id, j.title, j.company, j.location, j.remote_status, j.salary, 
                j.experience, j.skills, j.description, j.url, j.source, j.company_size, 
                j.industry, j.posting_date, j.visa_sponsorship, j.recruiter_link, j.processed_at,
                m.match_score, m.confidence, m.matched_skills, m.missing_skills, m.recommendation_reason, m.priority, m.apply_immediately,
                a.status
            FROM processed_jobs j
            LEFT JOIN job_matches m ON j.job_id = m.job_id AND m.user_id = ?
            LEFT JOIN applications a ON j.job_id = a.job_id AND a.user_id = ?
            ORDER BY j.processed_at DESC
            LIMIT ?
        """ if self.is_sqlite else """
            SELECT 
                j.job_id, j.title, j.company, j.location, j.remote_status, j.salary, 
                j.experience, j.skills, j.description, j.url, j.source, j.company_size, 
                j.industry, j.posting_date, j.visa_sponsorship, j.recruiter_link, j.processed_at,
                m.match_score, m.confidence, m.matched_skills, m.missing_skills, m.recommendation_reason, m.priority, m.apply_immediately,
                a.status
            FROM processed_jobs j
            LEFT JOIN job_matches m ON j.job_id = m.job_id AND m.user_id = %s
            LEFT JOIN applications a ON j.job_id = a.job_id AND a.user_id = %s
            ORDER BY j.processed_at DESC
            LIMIT %s
        """
        try:
            cur = self.conn.cursor()
            cur.execute(query, (user_id, user_id, limit))
            rows = cur.fetchall()
            cur.close()
            
            jobs = []
            for row in rows:
                jobs.append({
                    "job_id": row[0],
                    "title": row[1],
                    "company": row[2],
                    "location": row[3],
                    "remote_status": row[4],
                    "salary": row[5],
                    "experience": row[6],
                    "skills": row[7],
                    "description": row[8],
                    "url": row[9],
                    "source": row[10],
                    "company_size": row[11],
                    "industry": row[12],
                    "posting_date": row[13],
                    "visa_sponsorship": row[14],
                    "recruiter_link": row[15],
                    "processed_at": str(row[16]),
                    "matchScore": row[17] if row[17] is not None else 0,
                    "confidence": row[18] if row[18] is not None else 1.0,
                    "matchedSkills": [s.strip() for s in row[19].split(",")] if row[19] else [],
                    "missingSkills": [s.strip() for s in row[20].split(",")] if row[20] else [],
                    "recommendationReason": row[21] if row[21] else "",
                    "priority": row[22] if row[22] else "Medium",
                    "applyImmediately": bool(row[23]),
                    "status": row[24] if row[24] else "pending"
                })
            return jobs
        except Exception as e:
            logger.error(f"Error fetching recent jobs for user {user_id}: {e}")
            return []

    def set_job_status(self, user_id: str, job_id: str, status: str):
        try:
            cur = self.conn.cursor()
            if self.is_sqlite:
                query = "INSERT OR REPLACE INTO applications (user_id, job_id, status) VALUES (?, ?, ?)"
            else:
                query = "INSERT INTO applications (user_id, job_id, status) VALUES (%s, %s, %s) ON CONFLICT (user_id, job_id) DO UPDATE SET status = EXCLUDED.status"
            cur.execute(query, (user_id, job_id, status))
            self.conn.commit()
            cur.close()
            logger.info(f"Updated status for job {job_id} to {status} for user {user_id}")
        except Exception as e:
            logger.error(f"Error setting job status for user {user_id}: {e}")
            if self.conn:
                self.conn.rollback()

    def get_applications(self, user_id: str):
        query = """
            SELECT a.job_id, a.status, a.applied_at, j.title, j.company, j.source
            FROM applications a
            JOIN processed_jobs j ON a.job_id = j.job_id
            WHERE a.user_id = ?
            ORDER BY a.applied_at DESC
        """
        try:
            cur = self.conn.cursor()
            cur.execute(query, (user_id,))
            rows = cur.fetchall()
            cur.close()
            
            apps = []
            for row in rows:
                apps.append({
                    "job_id": row[0],
                    "status": row[1],
                    "applied_at": str(row[2]),
                    "title": row[3],
                    "company": row[4],
                    "source": row[5]
                })
            return apps
        except Exception as e:
            logger.error(f"Error fetching applications for user {user_id}: {e}")
            return []

    def delete_profile(self, user_id: str):
        try:
            cur = self.conn.cursor()
            cur.execute("DELETE FROM resume_profile WHERE user_id = ?", (user_id,))
            cur.execute("DELETE FROM settings WHERE user_id = ?", (user_id,))
            cur.execute("DELETE FROM job_matches WHERE user_id = ?", (user_id,))
            cur.execute("DELETE FROM applications WHERE user_id = ?", (user_id,))
            self.conn.commit()
            cur.close()
            logger.info(f"Resume profile and related data deleted successfully for user {user_id}.")
        except Exception as e:
            logger.error(f"Error deleting resume profile for user {user_id}: {e}")
            if self.conn:
                self.conn.rollback()

    def save_payment(self, utr: str, user_id: str, amount: float, status: str = "completed") -> bool:
        query = "INSERT INTO payments (utr, user_id, amount, status) VALUES (?, ?, ?, ?)"
        try:
            cur = self.conn.cursor()
            cur.execute(query, (utr, user_id, amount, status))
            self.conn.commit()
            cur.close()
            logger.info(f"Payment UTR {utr} saved successfully for user {user_id}.")
            return True
        except Exception as e:
            logger.error(f"Error saving payment UTR {utr}: {e}")
            if self.conn:
                self.conn.rollback()
            return False

    def is_utr_used(self, utr: str) -> bool:
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT 1 FROM payments WHERE utr = ?", (utr,))
            row = cur.fetchone()
            cur.close()
            return row is not None
        except Exception as e:
            logger.error(f"Error checking UTR {utr}: {e}")
            return False

db = Database()
