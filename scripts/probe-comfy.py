# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Single-submission local ComfyUI feasibility probe; never retries a POST.

Start writes an exclusive intent before submission. Inspect reconciles the same
intent using provider history/queue, including a lost submission response. Keep
receipts in private runtime storage; this is not the production worker adapter.
"""
import argparse
import hashlib
import json
import os
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

ENDPOINT = "http://127.0.0.1:8198"


def request(route, payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(ENDPOINT + route, data=data,
                                 headers={"Content-Type": "application/json"})
    # A direct local connection only: no environment proxy or redirected POST.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    with opener.open(req, timeout=30) as response:
        return json.load(response)


def persist(path, record, exclusive=False):
    encoded = json.dumps(record, indent=2) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if exclusive:
        with path.open("x", encoding="utf-8") as out:
            out.write(encoded)
            out.flush()
            os.fsync(out.fileno())
    else:
        temp = path.with_suffix(path.suffix + ".tmp")
        with temp.open("w", encoding="utf-8") as out:
            out.write(encoded)
            out.flush()
            os.fsync(out.fileno())
        temp.replace(path)


def start(workflow_path, receipt):
    workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
    capabilities = request("/object_info")
    for node in workflow.values():
        kind = node["class_type"]
        if kind not in capabilities or capabilities[kind].get("api_node"):
            raise ValueError(f"Unavailable or paid API node: {kind}")
    queue = request("/queue")
    if queue["queue_running"] or queue["queue_pending"]:
        raise ValueError("Local GPU queue is busy; do not submit another heavy workload")
    record = {
        "probeId": str(uuid.uuid4()), "endpoint": ENDPOINT,
        "startedAt": datetime.now(timezone.utc).isoformat(),
        "state": "submission_intent", "providerId": None,
        "workflowSha256": hashlib.sha256(json.dumps(workflow, sort_keys=True).encode()).hexdigest(),
        "workflow": workflow, "runtime": request("/system_stats"),
    }
    persist(receipt, record, exclusive=True)
    try:
        response = request("/prompt", {"prompt": workflow, "client_id": record["probeId"],
                                      "extra_data": {"mvm_probe_id": record["probeId"]}})
        record["providerId"] = response["prompt_id"]
        record["state"] = "submitted"
        record["response"] = response
    except urllib.error.HTTPError as error:
        # Validation failure is known; any other status may conceal submission.
        record["state"] = "rejected" if error.code == 400 else "reconciliation_required"
        record["httpStatus"] = error.code
        record["error"] = error.read().decode("utf-8", errors="replace")[:20000]
    except (OSError, ValueError, KeyError) as error:
        record["state"] = "reconciliation_required"
        record["errorKind"] = type(error).__name__
    persist(receipt, record)
    return record


def inspect(receipt):
    record = json.loads(receipt.read_text(encoding="utf-8"))
    if record["endpoint"] != ENDPOINT:
        raise ValueError("Receipt endpoint differs from this isolated probe")
    provider_id = record.get("providerId")
    history = request("/history" + (f"/{provider_id}" if provider_id else ""))
    queue = request("/queue")
    entries = [entry["prompt"] for entry in history.values()]
    entries += queue["queue_running"] + queue["queue_pending"]
    matches = {entry[1] for entry in entries
               if len(entry) > 3 and entry[3].get("mvm_probe_id") == record["probeId"]}
    if provider_id:
        matches.add(provider_id)
    if len(matches) > 1:
        record["state"] = "ambiguous_provider_receipt"
    elif matches:
        provider_id = matches.pop()
        record["providerId"] = provider_id
        result = history.get(provider_id)
        if result is not None:
            record["history"] = result
            status = result.get("status", {})
            if status.get("status_str") == "error":
                record["state"] = "failed"
            elif status.get("completed") and result.get("outputs"):
                record["state"] = "generated_unverified"
            else:
                record["state"] = "reconciliation_required"
        elif any(entry[1] == provider_id for entry in queue["queue_running"]):
            record["state"] = "running"
        elif any(entry[1] == provider_id for entry in queue["queue_pending"]):
            record["state"] = "queued"
        else:
            record["state"] = "reconciliation_required"
    elif record["state"] != "rejected":
        record["state"] = "reconciliation_required"
    record["inspectedAt"] = datetime.now(timezone.utc).isoformat()
    persist(receipt, record)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["start", "inspect"])
    parser.add_argument("--workflow", type=Path)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    if args.action == "start" and not args.workflow:
        parser.error("start requires --workflow")
    record = start(args.workflow, args.receipt) if args.action == "start" else inspect(args.receipt)
    print(json.dumps({key: record.get(key) for key in
                      ("probeId", "providerId", "state", "workflowSha256", "httpStatus")}))
    if args.action == "inspect" and record["state"] in ("running", "queued"):
        raise SystemExit(2)
    expected = "submitted" if args.action == "start" else "generated_unverified"
    if record["state"] != expected:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
