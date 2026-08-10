"""Read the 'version' field from a witness-verify JSON line on stdin."""
import json
import sys

try:
    payload = json.load(sys.stdin)
    print(payload.get("version", "NONE"))
except Exception:
    print("UNPARSEABLE")
