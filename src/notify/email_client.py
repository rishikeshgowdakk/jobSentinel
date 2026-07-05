import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from src.core.config import config
from src.core.logger import logger

class EmailClient:
    def send_notification(self, job: dict, match: dict):
        if not config.SMTP_USER or not config.NOTIFY_EMAIL:
            logger.warning("SMTP credentials or recipient email not configured. Skipping email notification.")
            return

        msg = MIMEMultipart('alternative')
        msg['From'] = config.SMTP_USER
        msg['To'] = config.NOTIFY_EMAIL
        
        score = match.get('matchScore', 0)
        msg['Subject'] = f"🚀 High Match Opportunity ({score}%): {job['title']} at {job['company']}"

        # Parse skills
        matched_skills = match.get('matchedSkills', [])
        if isinstance(matched_skills, str):
            matched_skills = [s.strip() for s in matched_skills.split(",") if s.strip()]
        missing_skills = match.get('missingSkills', [])
        if isinstance(missing_skills, str):
            missing_skills = [s.strip() for s in missing_skills.split(",") if s.strip()]

        matched_pills = "".join([f'<span style="background-color:#dcfce7;color:#15803d;padding:4px 8px;border-radius:4px;font-size:11px;margin-right:6px;display:inline-block;margin-bottom:6px;">{s}</span>' for s in matched_skills])
        missing_pills = "".join([f'<span style="background-color:#fee2e2;color:#b91c1c;padding:4px 8px;border-radius:4px;font-size:11px;margin-right:6px;display:inline-block;margin-bottom:6px;">{s}</span>' for s in missing_skills])

        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background-color: #f4f4f5; color: #1f2937; margin: 0; padding: 20px;">
            <table align="center" border="0" cellpadding="0" cellspacing="0" width="600" style="background-color: #ffffff; border-radius: 8px; border: 1px solid #e4e4e7; box-shadow: 0 4px 6px rgba(0,0,0,0.05); overflow: hidden;">
                <!-- Header -->
                <tr>
                    <td style="background-color: #2563eb; color: #ffffff; padding: 30px; text-align: center;">
                        <h1 style="margin: 0; font-size: 24px; font-weight: bold; letter-spacing: -0.5px;">JobSentinel Agent</h1>
                        <p style="margin: 5px 0 0 0; font-size: 14px; opacity: 0.9;">High-Compatibility Job Discovered</p>
                    </td>
                </tr>
                <!-- Content -->
                <tr>
                    <td style="padding: 30px;">
                        <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 25px;">
                            <div>
                                <h2 style="margin: 0; font-size: 20px; font-weight: 800; color: #111827;">{job['title']}</h2>
                                <p style="margin: 4px 0; font-size: 14px; font-weight: bold; color: #4b5563;">{job['company']} &bull; <span style="font-weight:normal;">{job.get('location', 'Remote')}</span></p>
                            </div>
                            <div style="background-color: #eff6ff; border: 1px solid #bfdbfe; color: #1d4ed8; padding: 8px 16px; border-radius: 20px; font-weight: 900; font-size: 18px; text-align: center;">
                                {score}% Match
                            </div>
                        </div>

                        <hr style="border: 0; border-top: 1px solid #e4e4e7; margin: 20px 0;" />

                        <h3 style="font-size: 14px; text-transform: uppercase; color: #6b7280; margin-bottom: 8px; letter-spacing: 0.5px;">Recommendation Insights</h3>
                        <p style="font-size: 14px; line-height: 1.6; color: #374151; margin-top: 0; background-color: #fafafa; border-left: 3px solid #3b82f6; padding: 12px;">
                            {match.get('recommendationReason', 'The job role aligns strongly with your current experience level and primary tech stack.')}
                        </p>

                        <!-- Salary & Info -->
                        <div style="margin: 15px 0; font-size: 13px; color: #4b5563;">
                            {f"<b>Salary:</b> {job['salary']}<br/>" if job.get('salary') else ""}
                            {f"<b>Remote Status:</b> {job['remote_status']}<br/>" if job.get('remote_status') else ""}
                            <b>Priority:</b> {match.get('priority', 'Medium')} &bull; <b>Source:</b> {job.get('source', 'Web')}
                        </div>

                        <table border="0" cellpadding="0" cellspacing="0" width="100%" style="margin-top: 25px;">
                            <!-- Matched Skills -->
                            <tr>
                                <td style="padding-bottom: 15px;">
                                    <h4 style="margin: 0 0 8px 0; font-size: 13px; text-transform: uppercase; color: #166534;">Matched Skills</h4>
                                    <div>{matched_pills if matched_pills else '<span style="font-size:12px;color:#9ca3af;">None</span>'}</div>
                                </td>
                            </tr>
                            <!-- Missing Skills -->
                            {f'''
                            <tr>
                                <td style="padding-bottom: 15px;">
                                    <h4 style="margin: 0 0 8px 0; font-size: 13px; text-transform: uppercase; color: #991b1b;">Missing Skills Gap</h4>
                                    <div>{missing_pills}</div>
                                </td>
                            </tr>
                            ''' if missing_pills else ""}
                        </table>

                        <!-- CTA Button -->
                        <div style="text-align: center; margin-top: 35px;">
                            <a href="{job['url']}" target="_blank" style="background-color: #2563eb; color: #ffffff; text-decoration: none; padding: 14px 30px; border-radius: 8px; font-weight: bold; font-size: 14px; display: inline-block; box-shadow: 0 4px 6px rgba(37,99,235,0.2);">
                                Apply Immediately &rarr;
                            </a>
                        </div>
                    </td>
                </tr>
                <!-- Footer -->
                <tr>
                    <td style="background-color: #f4f4f5; border-top: 1px solid #e4e4e7; padding: 20px; text-align: center; font-size: 11px; color: #71717a;">
                        Sent by JobSentinel autonomous agent. All details calculated semantically.<br/>
                        &copy; 2026 JobSentinel Inc.
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(html_body, 'html'))

        try:
            server = smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT)
            server.starttls()
            server.login(config.SMTP_USER, config.SMTP_PASSWORD)
            server.send_message(msg)
            server.quit()
            logger.info(f"HTML email notification successfully sent to {config.NOTIFY_EMAIL} for {job['title']}")
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
