"""Local ops helper: run a shell script on the prod instance via SSM, print output.

Usage: python scripts/_ssm_run.py <script_file>
Reads the script from a file (so no shell-quoting issues), sends it as a single
AWS-RunShellScript command, polls to completion, prints stdout/stderr.
Not committed-critical; a throwaway ops tool. Reads only — never echoes secrets
unless the script itself does.
"""
import sys
import time

import boto3

INSTANCE = "i-06d145c63c87cd096"
REGION = "eu-central-1"

script = open(sys.argv[1]).read()
ssm = boto3.client("ssm", region_name=REGION)
cmd = ssm.send_command(
    InstanceIds=[INSTANCE],
    DocumentName="AWS-RunShellScript",
    Parameters={"commands": [script]},
)["Command"]["CommandId"]

for _ in range(40):
    time.sleep(3)
    inv = ssm.get_command_invocation(CommandId=cmd, InstanceId=INSTANCE)
    if inv["Status"] in ("Success", "Failed", "Cancelled", "TimedOut"):
        break

sys.stderr.write(f"[status={inv['Status']}]\n")
sys.stdout.write(inv.get("StandardOutputContent", ""))
err = inv.get("StandardErrorContent", "")
if err.strip():
    sys.stderr.write("--- stderr ---\n" + err)
