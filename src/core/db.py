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
        # We always want our new schemas, so we check or rebuild
        try:
            cur = self.conn.cursor()
            # Drop old tables to migrate to the new multi-table AI Job Agent schema
            if self.is_sqlite:
                cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='processed_jobs'")
                exists = cur.fetchone()
                if exists:
                    # Let's check if 'company_size' is present. If not, drop to update
                    cur.execute("PRAGMA table_info(processed_jobs)")
                    cols = [c[1] for c in cur.fetchall()]
                    if "company_size" not in cols:
                        logger.info("Dropping old table layout to migrate to AI Job Agent schema...")
                        cur.execute("DROP TABLE IF EXISTS processed_jobs")
                        cur.execute("DROP TABLE IF EXISTS job_matches")
            else:
                cur.execute("SELECT table_name FROM information_schema.tables WHERE table_name='processed_jobs'")
                exists = cur.fetchone()
                if exists:
                    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='processed_jobs' AND column_name='company_size'")
                    col_exists = cur.fetchone()
                    if not col_exists:
                        logger.info("Dropping old Postgres table layout to migrate to AI Job Agent schema...")
                        cur.execute("DROP TABLE IF EXISTS processed_jobs CASCADE")
                        cur.execute("DROP TABLE IF EXISTS job_matches CASCADE")
            self.conn.commit()
            cur.close()
        except Exception as e:
            logger.warning(f"Error checking/migrating schema: {e}")

        queries = [
            """
            CREATE TABLE IF NOT EXISTS settings (
                key VARCHAR(255) PRIMARY KEY,
                value TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS resume_profile (
                id SERIAL PRIMARY KEY,
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
                job_id VARCHAR(255) PRIMARY KEY,
                match_score INTEGER,
                confidence REAL,
                matched_skills TEXT,
                missing_skills TEXT,
                recommendation_reason TEXT,
                priority VARCHAR(50),
                apply_immediately BOOLEAN,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS applications (
                job_id VARCHAR(255) PRIMARY KEY,
                status VARCHAR(100) DEFAULT 'applied',
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

    def get_setting(self, key: str, default: str = None) -> str:
        query = "SELECT value FROM settings WHERE key = ?" if self.is_sqlite else "SELECT value FROM settings WHERE key = %s"
        try:
            cur = self.conn.cursor()
            cur.execute(query, (key,))
            row = cur.fetchone()
            cur.close()
            return row[0] if row else default
        except Exception as e:
            logger.error(f"Error fetching setting {key}: {e}")
            return default

    def set_setting(self, key: str, value: str):
        if self.is_sqlite:
            query = "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)"
        else:
            query = "INSERT INTO settings (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value"
            
        try:
            cur = self.conn.cursor()
            cur.execute(query, (key, value))
            self.conn.commit()
            cur.close()
        except Exception as e:
            logger.error(f"Error setting {key}: {e}")
            if self.conn:
                self.conn.rollback()

    def save_profile(self, raw_text: str, structured_data: dict, embedding: list = None):
        # Clean existing profiles since we only have one active user in local dashboard mode
        try:
            cur = self.conn.cursor()
            cur.execute("DELETE FROM resume_profile")
            
            embedding_str = json.dumps(embedding) if embedding else ""
            sd_str = json.dumps(structured_data)
            
            if self.is_sqlite:
                query = "INSERT INTO resume_profile (raw_text, structured_data, embedding) VALUES (?, ?, ?)"
            else:
                query = "INSERT INTO resume_profile (raw_text, structured_data, embedding) VALUES (%s, %s, %s)"
                
            cur.execute(query, (raw_text, sd_str, embedding_str))
            self.conn.commit()
            cur.close()
            logger.info("Resume profile saved successfully.")
        except Exception as e:
            logger.error(f"Error saving resume profile: {e}")
            if self.conn:
                self.conn.rollback()

    def get_profile(self) -> dict:
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT raw_text, structured_data, embedding FROM resume_profile ORDER BY id DESC LIMIT 1")
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
            logger.error(f"Error fetching resume profile: {e}")
            return None

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

    def save_match(self, match_data: dict):
        try:
            if self.is_sqlite:
                query = """
                    INSERT INTO job_matches (
                        job_id, match_score, confidence, matched_skills, 
                        missing_skills, recommendation_reason, priority, apply_immediately
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(job_id) DO UPDATE SET
                        match_score = excluded.match_score, confidence = excluded.confidence,
                        matched_skills = excluded.matched_skills, missing_skills = excluded.missing_skills,
                        recommendation_reason = excluded.recommendation_reason, priority = excluded.priority,
                        apply_immediately = excluded.apply_immediately, updated_at = CURRENT_TIMESTAMP
                """
            else:
                query = """
                    INSERT INTO job_matches (
                        job_id, match_score, confidence, matched_skills, 
                        missing_skills, recommendation_reason, priority, apply_immediately
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT(job_id) DO UPDATE SET
                        match_score = EXCLUDED.match_score, confidence = EXCLUDED.confidence,
                        matched_skills = EXCLUDED.matched_skills, missing_skills = EXCLUDED.missing_skills,
                        recommendation_reason = EXCLUDED.recommendation_reason, priority = EXCLUDED.priority,
                        apply_immediately = EXCLUDED.apply_immediately, updated_at = CURRENT_TIMESTAMP
                """
            params = (
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
            logger.error(f"Error saving match: {e}")
            if self.conn:
                self.conn.rollback()

    def get_recent_jobs(self, limit=50):
        # Joins processed_jobs, job_matches, and applications to get a complete view
        query = """
            SELECT 
                j.job_id, j.title, j.company, j.location, j.remote_status, j.salary, 
                j.experience, j.skills, j.description, j.url, j.source, j.company_size, 
                j.industry, j.posting_date, j.visa_sponsorship, j.recruiter_link, j.processed_at,
                m.match_score, m.confidence, m.matched_skills, m.missing_skills, m.recommendation_reason, m.priority, m.apply_immediately,
                a.status
            FROM processed_jobs j
            LEFT JOIN job_matches m ON j.job_id = m.job_id
            LEFT JOIN applications a ON j.job_id = a.job_id
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
            LEFT JOIN job_matches m ON j.job_id = m.job_id
            LEFT JOIN applications a ON j.job_id = a.job_id
            ORDER BY j.processed_at DESC
            LIMIT %s
        """
        try:
            cur = self.conn.cursor()
            cur.execute(query, (limit,))
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
            logger.error(f"Error fetching recent jobs: {e}")
            return []

    def set_job_status(self, job_id: str, status: str):
        try:
            cur = self.conn.cursor()
            if self.is_sqlite:
                query = "INSERT OR REPLACE INTO applications (job_id, status) VALUES (?, ?)"
            else:
                query = "INSERT INTO applications (job_id, status) VALUES (%s, %s) ON CONFLICT (job_id) DO UPDATE SET status = EXCLUDED.status"
            cur.execute(query, (job_id, status))
            self.conn.commit()
            cur.close()
            logger.info(f"Updated status for job {job_id} to {status}")
        except Exception as e:
            logger.error(f"Error setting job status: {e}")
            if self.conn:
                self.conn.rollback()

    def get_applications(self):
        query = """
            SELECT a.job_id, a.status, a.applied_at, j.title, j.company, j.source
            FROM applications a
            JOIN processed_jobs j ON a.job_id = j.job_id
            ORDER BY a.applied_at DESC
        """
        try:
            cur = self.conn.cursor()
            cur.execute(query)
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
            logger.error(f"Error fetching applications: {e}")
            return []

db = Database()
