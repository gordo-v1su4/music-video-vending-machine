"""Run an API-format ComfyUI graph through SwarmUI (never straight to its backend).

SwarmUI's T2I API accepts a whole workflow as the `comfyworkflowraw` parameter
(ComfyUIAPIAbstractBackend.GetRawWorkflowFrom), so the job gets Swarm's queue, history and output folder.
Images the graph loads must already be in the managed ComfyUI's input folder.

  uv run --python 3.12 python -m mvvm_gen.swarm_raw GRAPH.json [--swarm http://127.0.0.1:7861]
"""

import argparse
import json
import urllib.request

SWARM = "http://127.0.0.1:7861"


def post(swarm, route, body, timeout=3600):
    req = urllib.request.Request(f"{swarm}/API/{route}", json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def run(graph, swarm=SWARM, prompt="raw workflow"):
    """Blocking: returns Swarm's result ({"images": [...]} with output paths, or {"error": ...})."""
    session = post(swarm, "GetNewSession", {})["session_id"]
    return post(swarm, "GenerateText2Image", {"session_id": session, "images": 1, "prompt": prompt,
                                              "comfyworkflowraw": json.dumps(graph)})


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("graph")
    ap.add_argument("--swarm", default=SWARM)
    a = ap.parse_args()
    with open(a.graph, encoding="utf-8") as fh:
        print(json.dumps(run(json.load(fh), a.swarm), indent=1))
