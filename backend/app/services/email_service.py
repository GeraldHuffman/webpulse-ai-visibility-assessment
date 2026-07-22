"""Resend email integration — transactional emails."""

import httpx
from loguru import logger

from app.core.config import Settings
from app.models.orm import Assessment, Report

RESEND_API = "https://api.resend.com/emails"


def _report_email_html(assessment: Assessment, report: Report, settings: Settings) -> str:
    """Generate the HTML email body for the report-ready email."""
    score = report.visibility_score
    score_color = "#00d4a1" if score >= 70 else "#7209B7" if score >= 40 else "#F72585"

    actions_html = ""
    for action in report.get("actions", [])[:3]:
        a = action if isinstance(action, dict) else {}
        actions_html += f"""
        <tr>
          <td style="padding: 12px; background: #1a1a2e; border-radius: 8px; margin-bottom: 8px;">
            <strong style="color: #00d4a1;">{a.get('title', '')}</strong><br>
            <span style="color: #ccc; font-size: 14px;">{a.get('description', '')}</span>
          </td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0; padding:0; background:#0d0d1a; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;">
  <div style="max-width:600px; margin:0 auto; padding:32px; background:#0d0d1a;">
    <div style="text-align:center; margin-bottom:32px;">
      <h1 style="color:#fff; font-size:28px; margin:0;">Your AI Visibility Assessment is Ready</h1>
      <p style="color:#888; font-size:16px;">{assessment.company_name}</p>
    </div>

    <div style="text-align:center; padding:32px; background:#15001f; border-radius:16px; margin-bottom:32px;">
      <div style="font-size:64px; font-weight:bold; color:{score_color};">{score}</div>
      <div style="color:#888; font-size:18px;">AI Visibility Score (out of 100)</div>
    </div>

    <div style="padding:24px; background:#1a1a2e; border-radius:12px; margin-bottom:32px;">
      <p style="color:#ddd; font-size:16px; line-height:1.6;">{report.summary}</p>
    </div>

    <h2 style="color:#00d4a1; font-size:20px; margin-bottom:16px;">Top Actions to Improve</h2>
    <table style="width:100%; border-collapse:separate; border-spacing:0 8px;">
      {actions_html}
    </table>

    <div style="text-align:center; padding:32px; margin-top:32px;">
      <a href="{settings.app_url}/report/{assessment.id}"
         style="display:inline-block; padding:16px 48px; background:linear-gradient(135deg, #F72585, #7209B7); color:#fff; text-decoration:none; font-size:18px; font-weight:bold; border-radius:8px;">
        View Full Report
      </a>
    </div>

    <div style="text-align:center; padding:24px; background:#15001f; border-radius:12px; margin-top:32px;">
      <p style="color:#ddd; font-size:16px;">Want to talk through your results?</p>
      <a href="{settings.app_url}/report/{assessment.id}?action=schedule"
         style="display:inline-block; padding:12px 32px; background:#00d4a1; color:#0d0d1a; text-decoration:none; font-size:16px; font-weight:bold; border-radius:8px; margin-top:12px;">
        Book a Strategy Session
      </a>
    </div>

    <p style="color:#555; font-size:12px; text-align:center; margin-top:32px;">
      WebPulse — AI Visibility Assessment<br>
      <a href="{settings.app_url}/report/{assessment.id}" style="color:#7209B7;">View your report</a>
    </p>
  </div>
</body>
</html>"""


async def send_report_ready_email(assessment: Assessment, report: Report, settings: Settings) -> None:
    """Send the report-ready notification email via Resend."""
    if not settings.resend_api_key:
        logger.info("Email send skipped: Resend not configured")
        return

    html = _report_email_html(assessment, report, settings)

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            RESEND_API,
            headers={
                "Authorization": f"Bearer {settings.resend_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": settings.email_from,
                "to": [assessment.email],
                "subject": f"Your AI Visibility Assessment is Ready — Score: {report.visibility_score}/100",
                "html": html,
                "tags": ["assessment", "report-ready"],
            },
        )
        if resp.status_code in (200, 202):
            logger.info(f"Report email sent to {assessment.email}")
        else:
            logger.error(f"Email send failed: {resp.status_code} {resp.text[:200]}")
