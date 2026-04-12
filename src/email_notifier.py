"""
Email Notifier - Sends email alerts when manual action is needed.
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

logger = logging.getLogger(__name__)


class EmailNotifier:
    def __init__(self, smtp_host: str, smtp_port: int, smtp_email: str, smtp_password: str, notify_email: str):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_email = smtp_email
        self.smtp_password = smtp_password
        self.notify_email = notify_email

    def _send_email(self, subject: str, html_body: str) -> bool:
        """Send an email via SMTP."""
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.smtp_email
            msg["To"] = self.notify_email

            msg.attach(MIMEText(html_body, "html"))

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(self.smtp_email, self.smtp_password)
                server.sendmail(self.smtp_email, self.notify_email, msg.as_string())

            logger.info(f"Email sent: {subject}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    def notify_manual_action_needed(self, jobs: list):
        """Send email with jobs requiring manual action (login, extra details, etc.)."""
        if not jobs:
            return

        subject = f"🔔 Job Bot: {len(jobs)} job(s) need your attention"

        rows = ""
        for job in jobs:
            rows += f"""
            <tr>
                <td style="padding:8px;border:1px solid #ddd;">{job.get('title', 'N/A')}</td>
                <td style="padding:8px;border:1px solid #ddd;">{job.get('company', 'N/A')}</td>
                <td style="padding:8px;border:1px solid #ddd;">{job.get('platform', 'N/A')}</td>
                <td style="padding:8px;border:1px solid #ddd;">{job.get('message', 'Manual action required')}</td>
                <td style="padding:8px;border:1px solid #ddd;">
                    <a href="{job.get('url', '#')}" style="color:#1a73e8;">Apply Here</a>
                </td>
            </tr>
            """

        html = f"""
        <html>
        <body style="font-family:Arial,sans-serif;max-width:800px;margin:0 auto;">
            <div style="background:#1a73e8;color:white;padding:20px;border-radius:8px 8px 0 0;">
                <h2 style="margin:0;">⚡ Jobs Requiring Manual Action</h2>
                <p style="margin:5px 0 0;">Found {len(jobs)} job(s) that need your attention</p>
            </div>
            <div style="padding:15px;background:#f9f9f9;">
                <table style="width:100%;border-collapse:collapse;background:white;">
                    <thead>
                        <tr style="background:#f0f0f0;">
                            <th style="padding:10px;border:1px solid #ddd;text-align:left;">Title</th>
                            <th style="padding:10px;border:1px solid #ddd;text-align:left;">Company</th>
                            <th style="padding:10px;border:1px solid #ddd;text-align:left;">Platform</th>
                            <th style="padding:10px;border:1px solid #ddd;text-align:left;">Reason</th>
                            <th style="padding:10px;border:1px solid #ddd;text-align:left;">Link</th>
                        </tr>
                    </thead>
                    <tbody>{rows}</tbody>
                </table>
                <p style="color:#666;font-size:12px;margin-top:15px;">
                    Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} by Job Auto-Apply Bot
                </p>
            </div>
        </body>
        </html>
        """

        self._send_email(subject, html)

    def notify_successful_applications(self, jobs: list):
        """Send email with successfully applied jobs."""
        if not jobs:
            return

        subject = f"✅ Job Bot: Applied to {len(jobs)} job(s) automatically"

        rows = ""
        for job in jobs:
            rows += f"""
            <tr>
                <td style="padding:8px;border:1px solid #ddd;">{job.get('title', 'N/A')}</td>
                <td style="padding:8px;border:1px solid #ddd;">{job.get('company', 'N/A')}</td>
                <td style="padding:8px;border:1px solid #ddd;">{job.get('platform', 'N/A')}</td>
                <td style="padding:8px;border:1px solid #ddd;">{job.get('match_score', 0):.0f}%</td>
                <td style="padding:8px;border:1px solid #ddd;">
                    <a href="{job.get('url', '#')}" style="color:#1a73e8;">View</a>
                </td>
            </tr>
            """

        html = f"""
        <html>
        <body style="font-family:Arial,sans-serif;max-width:800px;margin:0 auto;">
            <div style="background:#34a853;color:white;padding:20px;border-radius:8px 8px 0 0;">
                <h2 style="margin:0;">✅ Auto-Applied Successfully</h2>
                <p style="margin:5px 0 0;">Applied to {len(jobs)} matching job(s)</p>
            </div>
            <div style="padding:15px;background:#f9f9f9;">
                <table style="width:100%;border-collapse:collapse;background:white;">
                    <thead>
                        <tr style="background:#f0f0f0;">
                            <th style="padding:10px;border:1px solid #ddd;text-align:left;">Title</th>
                            <th style="padding:10px;border:1px solid #ddd;text-align:left;">Company</th>
                            <th style="padding:10px;border:1px solid #ddd;text-align:left;">Platform</th>
                            <th style="padding:10px;border:1px solid #ddd;text-align:left;">Match Score</th>
                            <th style="padding:10px;border:1px solid #ddd;text-align:left;">Link</th>
                        </tr>
                    </thead>
                    <tbody>{rows}</tbody>
                </table>
                <p style="color:#666;font-size:12px;margin-top:15px;">
                    Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} by Job Auto-Apply Bot
                </p>
            </div>
        </body>
        </html>
        """

        self._send_email(subject, html)

    def send_daily_summary(self, stats: dict):
        """Send daily application summary."""
        subject = f"📊 Job Bot Daily Summary - {datetime.now().strftime('%b %d, %Y')}"

        total = sum(stats.values())
        applied = stats.get("applied", 0)
        manual = stats.get("manual_needed", 0)
        failed = stats.get("failed", 0)
        discovered = stats.get("discovered", 0)
        matched = stats.get("matched", 0)

        html = f"""
        <html>
        <body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
            <div style="background:#1a73e8;color:white;padding:20px;border-radius:8px 8px 0 0;">
                <h2 style="margin:0;">📊 Daily Summary</h2>
                <p style="margin:5px 0 0;">{datetime.now().strftime('%B %d, %Y')}</p>
            </div>
            <div style="padding:20px;background:#f9f9f9;">
                <div style="display:flex;flex-wrap:wrap;gap:10px;margin-bottom:20px;">
                    <div style="flex:1;min-width:120px;background:white;padding:15px;border-radius:8px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,0.1);">
                        <div style="font-size:28px;font-weight:bold;color:#1a73e8;">{total}</div>
                        <div style="color:#666;">Total Jobs Found</div>
                    </div>
                    <div style="flex:1;min-width:120px;background:white;padding:15px;border-radius:8px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,0.1);">
                        <div style="font-size:28px;font-weight:bold;color:#34a853;">{applied}</div>
                        <div style="color:#666;">Auto-Applied</div>
                    </div>
                    <div style="flex:1;min-width:120px;background:white;padding:15px;border-radius:8px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,0.1);">
                        <div style="font-size:28px;font-weight:bold;color:#fbbc04;">{manual}</div>
                        <div style="color:#666;">Need Attention</div>
                    </div>
                    <div style="flex:1;min-width:120px;background:white;padding:15px;border-radius:8px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,0.1);">
                        <div style="font-size:28px;font-weight:bold;color:#ea4335;">{failed}</div>
                        <div style="color:#666;">Failed</div>
                    </div>
                </div>
                <p style="color:#666;font-size:12px;">
                    Bot running every 30 minutes. Generated at {datetime.now().strftime('%H:%M:%S')}.
                </p>
            </div>
        </body>
        </html>
        """

        self._send_email(subject, html)

    def notify_login_required(self, platform: str, error_msg: str = ""):
        """Send email when platform login fails or session expires."""
        subject = f"🔐 Job Bot: {platform} login required"

        html = f"""
        <html>
        <body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
            <div style="background:#ea4335;color:white;padding:20px;border-radius:8px 8px 0 0;">
                <h2 style="margin:0;">🔐 Login Required</h2>
            </div>
            <div style="padding:20px;background:#f9f9f9;">
                <p>The bot could not log into <strong>{platform}</strong>.</p>
                <p>This may be due to:</p>
                <ul>
                    <li>Expired session or changed password</li>
                    <li>CAPTCHA or security verification required</li>
                    <li>OTP/2FA prompt</li>
                </ul>
                {f'<p style="color:#ea4335;"><strong>Error:</strong> {error_msg}</p>' if error_msg else ''}
                <p>Please log in manually and update your credentials in the <code>.env</code> file if needed.</p>
                <p style="color:#666;font-size:12px;">
                    {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                </p>
            </div>
        </body>
        </html>
        """

        self._send_email(subject, html)
