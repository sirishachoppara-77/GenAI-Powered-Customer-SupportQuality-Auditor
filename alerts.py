"""
alerts.py — Compliance Alerting Module for CallIQ (Milestone 4)

Sends real-time alerts when a call evaluation triggers critical thresholds.
Supports: Email (SMTP/SendGrid), Slack webhooks, Microsoft Teams webhooks.

Alert triggers (configurable):
  - Total score below threshold (default: 10/25)
  - Escalation risk = High
  - One or more compliance violations detected
  - Specific keywords detected (e.g. "lawsuit", "fraud")
  - Customer sentiment = Negative AND score below threshold
"""

import os
import json
import smtplib
import datetime
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

# ── Alert config (override via environment variables or AlertConfig) ──────────
DEFAULT_THRESHOLDS = {
    "score_below":          10,      # alert if total_score < this
    "escalation_high":      True,    # alert on High escalation risk
    "any_violation":        True,    # alert if any compliance violation
    "critical_keywords":    ["lawsuit", "legal action", "fraud", "data breach", "discrimination", "harassment"],
    "negative_low_score":   True,    # alert if Negative sentiment AND score < 15
}

ALERT_LOG_PATH = Path("calliq_alerts.json")


# ── Alert log ─────────────────────────────────────────────────────────────────
def load_alert_log() -> list:
    if ALERT_LOG_PATH.exists():
        try:
            return json.loads(ALERT_LOG_PATH.read_text())
        except Exception:
            return []
    return []


def save_alert_log(log: list):
    ALERT_LOG_PATH.write_text(json.dumps(log, indent=2))


def log_alert(entry: dict):
    log = load_alert_log()
    entry["logged_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log.append(entry)
    save_alert_log(log)


# ── Trigger evaluation ─────────────────────────────────────────────────────────
def evaluate_triggers(result: dict, thresholds: dict = None) -> list[dict]:
    """
    Evaluate a result dict against alert thresholds.
    Returns list of triggered alerts, each with:
      {type, severity, title, detail, score, filename, timestamp}
    """
    t = thresholds or DEFAULT_THRESHOLDS
    alerts = []
    score     = result.get("total_score", 0)
    escalation= result.get("escalation_risk", "Low")
    sentiment = result.get("customer_sentiment", "Neutral")
    violations= result.get("compliance_violations", [])
    keywords  = result.get("compliance_keywords", [])
    filename  = result.get("filename", "unknown")
    timestamp = result.get("timestamp", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    # 1. Low score
    if score < t.get("score_below", 10):
        alerts.append({
            "type": "low_score",
            "severity": "critical" if score < 8 else "warning",
            "title": f"Low Quality Score — {score}/25",
            "detail": f"Call '{filename}' scored {score}/25, below the minimum threshold of {t['score_below']}/25.",
            "score": score, "filename": filename, "timestamp": timestamp,
        })

    # 2. High escalation
    if t.get("escalation_high") and escalation == "High":
        alerts.append({
            "type": "escalation",
            "severity": "critical",
            "title": "High Escalation Risk Detected",
            "detail": f"Call '{filename}' has been flagged with HIGH escalation risk. Immediate supervisor review recommended.",
            "score": score, "filename": filename, "timestamp": timestamp,
        })

    # 3. Compliance violations
    if t.get("any_violation") and violations:
        vlist = "; ".join(violations[:3]) + ("..." if len(violations) > 3 else "")
        alerts.append({
            "type": "compliance_violation",
            "severity": "critical",
            "title": f"{len(violations)} Compliance Violation(s) Detected",
            "detail": f"Call '{filename}' triggered compliance violations: {vlist}",
            "score": score, "filename": filename, "timestamp": timestamp,
            "violations": violations,
        })

    # 4. Critical keywords
    critical_kw = [k for k in keywords if k in t.get("critical_keywords", [])]
    if critical_kw:
        alerts.append({
            "type": "critical_keyword",
            "severity": "critical",
            "title": f"Critical Keyword(s) Detected: {', '.join(critical_kw)}",
            "detail": f"Call '{filename}' contains high-risk keywords that require immediate review: {', '.join(critical_kw)}",
            "score": score, "filename": filename, "timestamp": timestamp,
            "keywords": critical_kw,
        })

    # 5. Negative sentiment + low score
    if t.get("negative_low_score") and sentiment == "Negative" and score < 15:
        alerts.append({
            "type": "negative_sentiment",
            "severity": "warning",
            "title": "Negative Sentiment + Low Score",
            "detail": f"Call '{filename}' has Negative customer sentiment with a score of {score}/25. Customer may require follow-up.",
            "score": score, "filename": filename, "timestamp": timestamp,
        })

    return alerts


# ── Email (SMTP) ───────────────────────────────────────────────────────────────
def send_email_alert(
    alerts: list[dict],
    result: dict,
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    from_addr: str,
    to_addrs: list[str],
    use_tls: bool = True,
) -> tuple[bool, str]:
    """Send a formatted HTML email for triggered alerts."""
    if not alerts:
        return True, "No alerts to send."
    if not all([smtp_host, smtp_user, smtp_password, to_addrs]):
        return False, "Missing SMTP configuration."

    try:
        score     = result.get("total_score", 0)
        filename  = result.get("filename", "unknown")
        timestamp = result.get("timestamp", "")
        g_ltr     = "A" if score >= 22 else ("B" if score >= 19 else ("C" if score >= 15 else ("D" if score >= 12 else "F")))

        critical = [a for a in alerts if a["severity"] == "critical"]
        warnings = [a for a in alerts if a["severity"] == "warning"]
        subject  = f"[CallIQ ALERT] {'🔴 CRITICAL' if critical else '🟡 WARNING'} — {filename} scored {score}/25"

        # HTML body
        alert_rows = ""
        for a in alerts:
            color = "#f87171" if a["severity"] == "critical" else "#fbbf24"
            icon  = "🔴" if a["severity"] == "critical" else "🟡"
            alert_rows += f"""
            <tr>
              <td style="padding:10px 14px;border-bottom:1px solid #1a1a2e">
                <span style="color:{color};font-weight:700">{icon} {a['title']}</span><br>
                <span style="color:#a0a0c0;font-size:13px">{a['detail']}</span>
              </td>
            </tr>"""

        html = f"""
<html><body style="background:#050508;color:#e8e8f0;font-family:Arial,sans-serif;padding:0;margin:0">
<div style="max-width:620px;margin:32px auto;background:#0d0d14;border:1px solid rgba(255,77,109,0.2);border-radius:16px;overflow:hidden">
  <div style="background:linear-gradient(135deg,#1f0a10,#0e0e1c);padding:28px 32px;border-bottom:1px solid rgba(255,77,109,0.15)">
    <div style="font-size:11px;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:#ff4d6d;margin-bottom:8px">CallIQ Compliance Alert</div>
    <div style="font-size:22px;font-weight:800;color:#f0f0f8">{filename}</div>
    <div style="font-size:13px;color:#555570;margin-top:4px">{timestamp}</div>
  </div>
  <div style="padding:20px 32px;display:flex;gap:20px;border-bottom:1px solid rgba(255,255,255,0.06)">
    <div style="text-align:center;flex:1">
      <div style="font-size:32px;font-weight:800;color:#ff4d6d">{score}</div>
      <div style="font-size:11px;color:#555570;text-transform:uppercase;letter-spacing:0.08em">Score / 25</div>
    </div>
    <div style="text-align:center;flex:1">
      <div style="font-size:32px;font-weight:800;color:#ff4d6d">{g_ltr}</div>
      <div style="font-size:11px;color:#555570;text-transform:uppercase;letter-spacing:0.08em">Grade</div>
    </div>
    <div style="text-align:center;flex:1">
      <div style="font-size:32px;font-weight:800;color:#{'f87171' if critical else 'fbbf24'}">{len(critical)+len(warnings)}</div>
      <div style="font-size:11px;color:#555570;text-transform:uppercase;letter-spacing:0.08em">Alert(s)</div>
    </div>
  </div>
  <table style="width:100%;border-collapse:collapse;background:#08080f">{alert_rows}</table>
  <div style="padding:16px 32px;font-size:12px;color:#333350;border-top:1px solid rgba(255,255,255,0.04)">
    Sent by CallIQ Quality Auditor · Vidzai Digital · This is an automated alert.
  </div>
</div>
</body></html>"""

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = from_addr
        msg["To"]      = ", ".join(to_addrs)
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            if use_tls:
                server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(from_addr, to_addrs, msg.as_string())

        return True, f"Email sent to {', '.join(to_addrs)}"

    except Exception as e:
        return False, f"Email failed: {e}"


# ── Slack webhook ──────────────────────────────────────────────────────────────
def send_slack_alert(
    alerts: list[dict],
    result: dict,
    webhook_url: str,
) -> tuple[bool, str]:
    """Send a formatted Slack Block Kit message."""
    if not alerts or not webhook_url:
        return False, "No alerts or no webhook URL."

    try:
        score    = result.get("total_score", 0)
        filename = result.get("filename", "unknown")
        ts       = result.get("timestamp", "")
        critical = any(a["severity"] == "critical" for a in alerts)
        icon     = ":red_circle:" if critical else ":warning:"

        blocks = [
            {"type": "header", "text": {"type": "plain_text", "text": f"{':rotating_light:' if critical else ':warning:'} CallIQ Compliance Alert"}},
            {"type": "section", "fields": [
                {"type": "mrkdwn", "text": f"*File:*\n{filename}"},
                {"type": "mrkdwn", "text": f"*Score:*\n{score}/25"},
                {"type": "mrkdwn", "text": f"*Alerts:*\n{len(alerts)} triggered"},
                {"type": "mrkdwn", "text": f"*Time:*\n{ts}"},
            ]},
            {"type": "divider"},
        ]

        for a in alerts:
            em = ":red_circle:" if a["severity"] == "critical" else ":warning:"
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"{em} *{a['title']}*\n{a['detail']}"}
            })

        blocks.append({"type": "context", "elements": [
            {"type": "mrkdwn", "text": "Sent by *CallIQ Quality Auditor* · Vidzai Digital"}
        ]})

        resp = requests.post(webhook_url, json={"blocks": blocks}, timeout=10)
        resp.raise_for_status()
        return True, "Slack alert sent."

    except Exception as e:
        return False, f"Slack failed: {e}"


# ── Microsoft Teams webhook ────────────────────────────────────────────────────
def send_teams_alert(
    alerts: list[dict],
    result: dict,
    webhook_url: str,
) -> tuple[bool, str]:
    """Send a Teams Adaptive Card via incoming webhook."""
    if not alerts or not webhook_url:
        return False, "No alerts or no webhook URL."

    try:
        score    = result.get("total_score", 0)
        filename = result.get("filename", "unknown")
        critical = any(a["severity"] == "critical" for a in alerts)
        color    = "FF0000" if critical else "FFA500"

        facts = [{"name": a["title"], "value": a["detail"]} for a in alerts]

        payload = {
            "@type": "MessageCard",
            "@context": "https://schema.org/extensions",
            "themeColor": color,
            "summary": f"CallIQ Alert — {filename}",
            "sections": [{
                "activityTitle": f"{'🔴 CRITICAL' if critical else '🟡 WARNING'}: {filename}",
                "activitySubtitle": f"Score: {score}/25 · {len(alerts)} alert(s) triggered",
                "facts": facts,
            }],
        }

        resp = requests.post(webhook_url, json=payload, timeout=10)
        resp.raise_for_status()
        return True, "Teams alert sent."

    except Exception as e:
        return False, f"Teams failed: {e}"


# ── Master dispatch ────────────────────────────────────────────────────────────
def dispatch_alerts(
    result: dict,
    config: dict,
    thresholds: dict = None,
) -> dict:
    """
    Main entry point. Evaluates triggers and dispatches to all configured channels.

    config keys (all optional):
      email_enabled, smtp_host, smtp_port, smtp_user, smtp_password,
      from_addr, to_addrs (list), use_tls
      slack_enabled, slack_webhook_url
      teams_enabled, teams_webhook_url

    Returns summary dict with triggered alerts and channel results.
    """
    alerts = evaluate_triggers(result, thresholds or DEFAULT_THRESHOLDS)

    if not alerts:
        return {"alerts": [], "channels": {}, "message": "No thresholds triggered."}

    channel_results = {}

    # Email
    if config.get("email_enabled") and config.get("smtp_host"):
        ok, msg = send_email_alert(
            alerts, result,
            smtp_host     = config.get("smtp_host", ""),
            smtp_port     = int(config.get("smtp_port", 587)),
            smtp_user     = config.get("smtp_user", ""),
            smtp_password = config.get("smtp_password", ""),
            from_addr     = config.get("from_addr", config.get("smtp_user", "")),
            to_addrs      = config.get("to_addrs", []),
            use_tls       = config.get("use_tls", True),
        )
        channel_results["email"] = {"success": ok, "message": msg}

    # Slack
    if config.get("slack_enabled") and config.get("slack_webhook_url"):
        ok, msg = send_slack_alert(alerts, result, config["slack_webhook_url"])
        channel_results["slack"] = {"success": ok, "message": msg}

    # Teams
    if config.get("teams_enabled") and config.get("teams_webhook_url"):
        ok, msg = send_teams_alert(alerts, result, config["teams_webhook_url"])
        channel_results["teams"] = {"success": ok, "message": msg}

    # Log
    for alert in alerts:
        log_alert({**alert, "channels_notified": list(channel_results.keys())})

    return {"alerts": alerts, "channels": channel_results, "message": f"{len(alerts)} alert(s) triggered."}
