"""
AI SRE Agent — analyzes Prometheus alerts and produces RCA via Gemini AI.
"""

import os
import sys
import json
import time
import logging
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

log = logging.getLogger("ai-sre-agent")

# Config
PROMETHEUS_URL = os.getenv(
    "PROMETHEUS_URL",
    "http://monitoring-kube-prometheus-prometheus.default.svc.cluster.local:9090"
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL_SECONDS", "60"))

if not GEMINI_API_KEY:
    log.error("GEMINI_API_KEY env var not set")
    sys.exit(1)

GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
)


def get_alerts():
    """Fetch firing alerts from Prometheus."""
    url = f"{PROMETHEUS_URL}/api/v1/alerts"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        data = response.json()

        alerts = data.get("data", {}).get("alerts", [])

        firing_alerts = [
            a for a in alerts
            if a.get("state") == "firing"
        ]

        log.info(
            f"Fetched {len(firing_alerts)} firing alerts "
            f"(out of {len(alerts)} total)"
        )

        return firing_alerts

    except Exception as e:
        log.error(f"Failed to fetch Prometheus alerts: {e}")
        return []


def build_prompt(alerts):
    """Build structured alert prompt."""

    formatted_alerts = []

    for a in alerts:
        formatted_alerts.append({
            "alertname": a.get("labels", {}).get("alertname"),
            "severity": a.get("labels", {}).get("severity"),
            "namespace": a.get("labels", {}).get("namespace"),
            "pod": a.get("labels", {}).get("pod"),
            "instance": a.get("labels", {}).get("instance"),
            "summary": a.get("annotations", {}).get("summary"),
            "description": a.get("annotations", {}).get("description"),
        })

    alert_json = json.dumps(formatted_alerts, indent=2)

    prompt = f"""
You are a senior Site Reliability Engineer.

Analyze the following Prometheus alerts.

Provide:
1. Root cause
2. Impact
3. Immediate remediation
4. Exact kubectl troubleshooting commands
5. Long-term prevention

Keep the response concise and operationally useful.

Alerts:
{alert_json}
"""

    return prompt


def analyze_with_gemini(alerts):
    """Send alerts to Gemini."""

    if not alerts:
        return "No firing alerts. Cluster healthy."

    prompt = build_prompt(alerts)

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 700
        }
    }

    headers = {
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            GEMINI_URL,
            headers=headers,
            json=payload,
            timeout=60
        )

        # Print raw error response for debugging
        if response.status_code != 200:
            log.error(f"Gemini API Error: {response.status_code}")
            log.error(response.text)
            return f"Gemini API failed: {response.text}"

        data = response.json()

        candidates = data.get("candidates", [])

        if not candidates:
            return "No response candidates returned from Gemini."

        content = candidates[0].get("content", {})
        parts = content.get("parts", [])

        if not parts:
            return "Gemini returned empty content."

        text = parts[0].get("text", "")

        return text

    except Exception as e:
        log.error(f"Gemini request failed: {e}")
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
            log.info("\n" + analysis)

        else:
            log.info("No firing alerts.")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
