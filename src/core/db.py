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
        query = """
            CREATE TABLE IF NOT EXISTS processed_jobs (
                id SERIAL PRIMARY KEY,
                job_id VARCHAR(255) UNIQUE NOT NULL,
                title TEXT,
                company TEXT,
                url TEXT,
                ats_score INTEGER,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status VARCHAR(50)
            )
        """
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
                INSERT INTO processed_jobs (job_id, title, company, url, ats_score, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """ if self.is_sqlite else """
                INSERT INTO processed_jobs (job_id, title, company, url, ats_score, status)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            params = (
                job_data['job_id'],
                job_data['title'],
                job_data['company'],
                job_data['url'],
                job_data.get('ats_score'),
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

db = Database()
