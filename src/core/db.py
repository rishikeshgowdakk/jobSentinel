import psycopg2
from src.core.config import config
from src.core.logger import logger

class Database:
    def __init__(self):
        self.conn = None
        self._connect()

    def _connect(self):
        try:
            self.conn = psycopg2.connect(
                dbname=config.DB_NAME,
                user=config.DB_USER,
                password=config.DB_PASSWORD,
                host=config.DB_HOST,
                port=config.DB_PORT
            )
            self._create_table()
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")

    def _create_table(self):
        with self.conn.cursor() as cur:
            cur.execute("""
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
            """)
            self.conn.commit()

    def job_exists(self, job_id: str) -> bool:
        with self.conn.cursor() as cur:
            cur.execute("SELECT 1 FROM processed_jobs WHERE job_id = %s", (job_id,))
            return cur.fetchone() is not None

    def add_job(self, job_data: dict):
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO processed_jobs (job_id, title, company, url, ats_score, status)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    job_data['job_id'],
                    job_data['title'],
                    job_data['company'],
                    job_data['url'],
                    job_data.get('ats_score'),
                    job_data.get('status', 'processed')
                ))
                self.conn.commit()
        except Exception as e:
            logger.error(f"Error adding job to DB: {e}")
            self.conn.rollback()

db = Database()
