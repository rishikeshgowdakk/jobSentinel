import psycopg2
import sqlite3
import os
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
        # Upgrade schema if needed
        try:
            cur = self.conn.cursor()
            if self.is_sqlite:
                cur.execute("PRAGMA table_info(processed_jobs)")
                cols = [c[1] for c in cur.fetchall()]
                if cols and "source" not in cols:
                    cur.execute("DROP TABLE processed_jobs")
            else:
                cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='processed_jobs'")
                cols = [c[0] for c in cur.fetchall()]
                if cols and "source" not in cols:
                    cur.execute("DROP TABLE processed_jobs CASCADE")
            self.conn.commit()
            cur.close()
        except Exception as e:
            logger.warning(f"Error checking/migrating schema: {e}")

        queries = [
            """
            CREATE TABLE IF NOT EXISTS processed_jobs (
                id SERIAL PRIMARY KEY,
                job_id VARCHAR(255) UNIQUE NOT NULL,
                title TEXT,
                company TEXT,
                url TEXT,
                source VARCHAR(100),
                location TEXT,
                description TEXT,
                skills TEXT,
                summary TEXT,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status VARCHAR(50)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS settings (
                key VARCHAR(255) PRIMARY KEY,
                value TEXT
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

    def add_job(self, job_data: dict):
        try:
            query = """
                INSERT INTO processed_jobs (job_id, title, company, url, source, location, description, skills, summary, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """ if self.is_sqlite else """
                INSERT INTO processed_jobs (job_id, title, company, url, source, location, description, skills, summary, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            params = (
                job_data['job_id'],
                job_data['title'],
                job_data['company'],
                job_data['url'],
                job_data.get('source', 'Unknown'),
                job_data.get('location', ''),
                job_data.get('description', ''),
                job_data.get('skills', ''),
                job_data.get('summary', ''),
                job_data.get('status', 'processed')
            )
            cur = self.conn.cursor()
            cur.execute(query, params)
            self.conn.commit()
            cur.close()
        except Exception as e:
            logger.error(f"Error adding job to DB: {e}")
            if self.conn:
                self.conn.rollback()

    def get_recent_jobs(self, limit=50):
        query = f"SELECT job_id, title, company, url, source, location, description, skills, summary, processed_at, status FROM processed_jobs ORDER BY processed_at DESC LIMIT {limit}"
        try:
            cur = self.conn.cursor()
            cur.execute(query)
            rows = cur.fetchall()
            cur.close()
            
            jobs = []
            for row in rows:
                jobs.append({
                    "job_id": row[0],
                    "title": row[1],
                    "company": row[2],
                    "url": row[3],
                    "source": row[4],
                    "location": row[5],
                    "description": row[6],
                    "skills": row[7],
                    "summary": row[8],
                    "processed_at": row[9].strftime('%Y-%m-%d %H:%M:%S') if hasattr(row[9], 'strftime') else str(row[9]),
                    "status": row[10]
                })
            return jobs
        except Exception as e:
            logger.error(f"Error fetching recent jobs: {e}")
            return []

db = Database()
