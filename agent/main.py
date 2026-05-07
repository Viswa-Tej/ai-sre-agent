"""
AI SRE Agent — analyzes Prometheus alerts and produces RCA via LLM.

Designed to be model-agnostic: swap LLM_BACKEND env var to use
Gemini, OpenAI, Groq, or Ollama. Currently configured for Gemini (free tier).
"""

import os
import sys
import json
import time
import logging
import requests

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
log = logging.getLogger("ai-sre-agent")

# Twelve-factor config
PROMETHEUS_URL = os.getenv(
    "PROMETHEUS_URL",
    "http://monitoring-kube-prometheus-prometheus.default.svc.cluster.local:9090"
)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL_SECONDS", "60"))

if not GEMINI_API_KEY:
    log.error("GEMINI_API_KEY env var not set. Exiting.")
    sys.exit(1)

GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
)


def get_alerts():
    """Query Prometheus alerts API. Returns firing alerts only."""
    url = f"{PROMETHEUS_URL}/api/v1/alerts"
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        data = res.json()
        alerts = data.get("data", {}).get("alerts", [])
        firing = [a for a in alerts if a.get("state") == "firing"]
        log.info(f"Fetched {len(firing)} firing alerts (out of {len(alerts)} total)")
        return firing
    except requests.exceptions.RequestException as e:
        log.error(f"Failed to fetch alerts: {e}")
        return []


def analyze_with_gemini(alerts):
    """Send alerts to Gemini and get RCA + remediation."""
    if not alerts:
        return "No firing alerts. Cluster healthy."

    alert_summary = json.dumps(
        [
            {
                "name": a.get("labels", {}).get("alertname"),
                "severity": a.get("labels", {}).get("severity"),
                "namespace": a.get("labels", {}).get("namespace"),
                "pod": a.get("labels", {}).get("pod"),
                "summary": a.get("annotations", {}).get("summary"),
                "description": a.get("annotations", {}).get("description"),
            }
            for a in alerts
        ],
        indent=2,
    )

    system_prompt = (
        "You are a senior Site Reliability Engineer. "
        "Given Prometheus alerts in JSON, produce: "
        "(1) likely root cause, "
        "(2) impact assessment, "
        "(3) immediate remediation steps with exact kubectl commands, "
        "(4) long-term fix. "
        "Be concise. Use plain text — no markdown."
    )

    payload = {
        "contents": [{
            "parts": [{
                "text": f"{system_prompt}\n\nAlerts:\n{alert_summary}"
            }]
        }],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 600,
        }
    }

    try:
        res = requests.post(GEMINI_URL, json=payload, timeout=30)
        res.raise_for_status()
        data = res.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        log.error(f"Gemini call failed: {e}")
        return f"LLM analysis failed: {e}"


def main():
    log.info("AI SRE Agent starting...")
    log.info(f"Prometheus URL: {PROMETHEUS_URL}")
    log.info(f"LLM Model: {GEMINI_MODEL}")
    log.info(f"Poll interval: {POLL_INTERVAL}s")

    while True:
        log.info("=" * 60)
        alerts = get_alerts()
        if alerts:
            analysis = analyze_with_gemini(alerts)
            log.info("AI ANALYSIS:")
            log.info(analysis)
        else:
            log.info("No firing alerts.")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
