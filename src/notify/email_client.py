import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from src.core.config import config
from src.core.logger import logger

class EmailClient:
    def send_notification(self, job_title: str, company: str, job_url: str, resume_path: str):
        msg = MIMEMultipart()
        msg['From'] = config.SMTP_USER
        msg['To'] = config.NOTIFY_EMAIL
        msg['Subject'] = f"URGENT: APPLY NOW - {job_title} at {company}"

        body = f"""
        A new high-match job has been found!
        
        Job: {job_title}
        Company: {company}
        Link: {job_url}
        
        A tailored resume has been generated and attached to this email.
        """
        msg.attach(MIMEText(body, 'plain'))

        if resume_path and os.path.exists(resume_path):
            with open(resume_path, "rb") as f:
                part = MIMEApplication(f.read(), Name=os.path.basename(resume_path))
            part['Content-Disposition'] = f'attachment; filename="{os.path.basename(resume_path)}"'
            msg.attach(part)

        try:
            server = smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT)
            server.starttls()
            server.login(config.SMTP_USER, config.SMTP_PASSWORD)
            server.send_message(msg)
            server.quit()
            logger.info(f"Email notification sent for {job_title}")
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
