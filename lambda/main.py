import json
import os
import sys
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional, Sequence, Tuple

def _post_to_slack(webhook_url: str, payload: dict) -> None:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()  # force request execution
    except urllib.error.HTTPError as e:
        print(f"Slack webhook HTTPError: {e.code} {e.reason}", file=sys.stderr)
        raise
    except urllib.error.URLError as e:
        print(f"Slack webhook URLError: {e.reason}", file=sys.stderr)
        raise


def _get_severity_details(impact: Optional[float]) -> Dict[str, str]:
    if impact is None:
        return {"color": "#78909C", "emoji": ":information_source:", "label": "UNKNOWN"}
    
    if impact > 100:
        return {"color": "#C62828", "emoji": ":rotating_light:", "label": "HIGH"}
    elif impact > 50:
        # Amber/Yellow
        return {"color": "#FFC107", "emoji": ":warning:", "label": "MEDIUM"}
    else:
        # Blue (Low)
        return {"color": "#2196F3", "emoji": ":information_source:", "label": "LOW"}


def _safe_get(d: Dict[str, Any], path: Sequence[str], default: Any = None) -> Any:
    cur = d
    try:
        for k in path:
            if cur is None:
                return default
            cur = cur.get(k)
        return cur if cur is not None else default
    except Exception:
        return default


def _get_any(d: Dict[str, Any], paths: Sequence[Sequence[str]], default: Any = None) -> Any:
    """Return the first non-None value among multiple possible key-paths.

    Helps support both TitleCase (e.g., AnomalyId) and camelCase (e.g., anomalyId)
    variants from different AWS payloads (SNS direct vs EventBridge/detail).
    """
    for p in paths:
        val = _safe_get(d, p, None)
        if val is not None:
            return val
    return default


def _format_date(date_str: Optional[str]) -> Optional[str]:
    """Return just the YYYY-MM-DD part if an ISO string (e.g., 2025-11-04T00:00:00Z) is provided.
    Leaves value unchanged when not a string or already date-only.
    """
    if not isinstance(date_str, str):
        return date_str
    if "T" in date_str:
        return date_str.split("T", 1)[0]
    return date_str


def _get_account_info(anomaly: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    """Return (account_id, account_name) from the anomaly root cause."""
    root_causes = _get_any(anomaly, [["RootCauses"], ["rootCauses"]], []) or []
    if not root_causes or not isinstance(root_causes, list):
        return None, None
    
    rc = root_causes[0] or {}
    account_id = _get_any(rc, [["LinkedAccount"], ["linkedAccount"]])
    if not account_id:
        return None, None
    
    # Try to resolve account name from payload
    # Check for "LinkedAccountName" or "linkedAccountName" in the root cause
    acct_name = _get_any(rc, [["LinkedAccountName"], ["linkedAccountName"]])
    
    clean_acct = str(account_id).strip()
    return clean_acct, acct_name


def _build_blocks_for_anomaly(anomaly: Dict[str, Any]) -> List[Dict[str, Any]]:
    impact_total = _get_any(
        anomaly,
        [["Impact", "TotalImpact"], ["impact", "totalImpact"]],
    )
    
    # Determine severity
    sev_details = _get_severity_details(
        impact_total if isinstance(impact_total, (int, float)) else None
    )
    emoji = sev_details["emoji"]
    label = sev_details["label"]


    impact_text = f"${impact_total:,.2f}" if isinstance(impact_total, (int, float)) else "n/a"
    impact_pct = _get_any(
        anomaly,
        [["Impact", "TotalImpactPercentage"], ["impact", "totalImpactPercentage"]],
    )
    impact_pct_text = f"{impact_pct:,.2f}%" if isinstance(impact_pct, (int, float)) else "n/a"

    fields = []
    # Time window
    start = _get_any(anomaly, [["AnomalyStartDate"], ["anomalyStartDate"]])
    end = _get_any(anomaly, [["AnomalyEndDate"], ["anomalyEndDate"]])
    start_fmt = _format_date(start)
    end_fmt = _format_date(end)
    if start or end:
        fields.append({
            "type": "mrkdwn",
            "text": f"*Window*\n{start_fmt or '-'} → {end_fmt or '-'}",
        })

    # Impact
    fields.append({
        "type": "mrkdwn",
        "text": f"*Estimated impact*\n{impact_text} USD",
    })

    # Impact percentage
    fields.append({
        "type": "mrkdwn",
        "text": f"*Impact %*\n{impact_pct_text}",
    })

    # Root cause summary (top item)
    root_causes = _get_any(anomaly, [["RootCauses"], ["rootCauses"]], []) or []
    if root_causes and isinstance(root_causes, list):
        rc = root_causes[0] or {}
        rc_parts = []
        # Try both TitleCase and camelCase keys per field
        service = _get_any(rc, [["Service"], ["service"]])
        account = _get_any(rc, [["LinkedAccount"], ["linkedAccount"]])
        region = _get_any(rc, [["Region"], ["region"]])
        usage = _get_any(rc, [["UsageType"], ["usageType"]])
        if service:
            rc_parts.append(f"Service: {service}")

        if region:
            rc_parts.append(f"Region: {region}")
        if usage:
            rc_parts.append(f"Usage: {usage}")
        if rc_parts:
            fields.append({
                "type": "mrkdwn",
                "text": "*Root cause*\n" + " | ".join(rc_parts),
            })

    # Anomaly ID
    anomaly_id = _get_any(anomaly, [["AnomalyId"], ["anomalyId"]])
    if anomaly_id:
        fields.append({
            "type": "mrkdwn",
            "text": f"*Anomaly ID*\n{anomaly_id}",
        })

    # Title shown once in the bold header, now with Severity
    header_title = f"{emoji} AWS Cost Anomaly Detected: {label} {emoji}"

    acct_id, acct_name = _get_account_info(anomaly)
    if acct_name:
        detail_line = f"{acct_name} ({acct_id})"
    elif acct_id:
        detail_line = f"Account: {acct_id}"
    else:
        detail_line = None

    blocks: List[Dict[str, Any]] = [
        {"type": "header", "text": {"type": "plain_text", "text": header_title, "emoji": True}},
        {
            "type": "section",
            **({"text": {"type": "mrkdwn", "text": detail_line}} if detail_line else {}),
            "fields": fields,
        },
    ]

    # Link to AWS console; prefer anomalyDetailsLink when provided
    console_url = _get_any(
        anomaly,
        [["anomalyDetailsLink"], ["AnomalyDetailsLink"]],
        "https://console.aws.amazon.com/cost-management/home?#/anomaly-detection/anomalies",
    )
    blocks.append({
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Open in AWS Console"},
                "url": console_url,
                "style": "primary",
            }
        ],
    })

    # Context footer
    blocks.append({
        "type": "context",
        "elements": [
            {"type": "mrkdwn", "text": "Sent by Cost Anomaly Detection → SNS → Lambda → Slack"}
        ],
    })

    return blocks


def _build_payload(anomaly: Optional[Dict[str, Any]], raw_text: str) -> Dict[str, Any]:
    if anomaly and _get_any(anomaly, [["AnomalyId"], ["anomalyId"]]):
        impact = _get_any(anomaly, [["Impact", "TotalImpact"], ["impact", "totalImpact"]])  # may be None
        sev_details = _get_severity_details(impact if isinstance(impact, (int, float)) else None)
        return {
            # Use an attachment for the color bar; detailed content comes from Block Kit
            "attachments": [
                {
                    "color": sev_details["color"],
                    "blocks": _build_blocks_for_anomaly(anomaly),
                }
            ],
        }
    # Fallback payload when the message can't be parsed as an anomaly
    return {
        "blocks": [
            {"type": "header", "text": {"type": "plain_text", "text": ":rotating_light: AWS Cost Anomaly Notification :rotating_light:", "emoji": True}},
            {"type": "section", "text": {"type": "mrkdwn", "text": f"```{raw_text}```"}},
        ],
    }

def handler(event, context):
    print("Event object:", json.dumps(event))

    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        print("Missing SLACK_WEBHOOK_URL environment variable", file=sys.stderr)
        # Fail fast so SNS can retry
        raise RuntimeError("SLACK_WEBHOOK_URL not set")

    # SNS -> Lambda event structure
    records = event.get("Records") or []
    for record in records:
        sns = record.get("Sns") or {}
        msg_str = sns.get("Message", "")

        # Try to parse the message payload as JSON from AWS CAD
        anomaly_payload: Optional[Dict[str, Any]] = None
        try:
            parsed = json.loads(msg_str)
            # If AWS wraps the anomaly in another object, try to extract
            if isinstance(parsed, dict) and (
                parsed.get("AnomalyId") or parsed.get("anomalyId")
            ):
                anomaly_payload = parsed
            elif isinstance(parsed, dict):
                detail = parsed.get("detail", {}) if isinstance(parsed.get("detail"), dict) else {}
                if detail.get("AnomalyId") or detail.get("anomalyId"):
                    anomaly_payload = detail
        except Exception:
            anomaly_payload = None

        payload = _build_payload(anomaly_payload, msg_str)
        _post_to_slack(webhook_url, payload)

    return {"status": "ok", "delivered": len(records)}
