#!/usr/bin/env python3
"""Render a reviewable deployment plan without calling a WAF platform."""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ACTION_MAP = {
    "aws": {
        "monitor": "Count",
        "block": "Block",
        "allow": "Allow",
    },
    "akamai": {
        "monitor": "Alert",
        "block": "Deny",
        "allow": "Allow/Exception",
    },
}


def load_policy(path):
    with path.open(encoding="utf-8") as policy_file:
        return json.load(policy_file)


def policy_digest(policy):
    canonical = json.dumps(policy, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def render_rule(policy, platform, environment):
    generic_action = policy["rollout"][f"{environment}_action"]
    return {
        "rule_id": policy["rule_id"],
        "jira_issue": policy["jira_issue"],
        "description": policy["description"],
        "priority": policy["priority"],
        "match": policy["match"],
        "generic_action": generic_action,
        "platform_action": ACTION_MAP[platform][generic_action],
        "policy_sha256": policy_digest(policy),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", choices=("aws", "akamai", "both"), required=True)
    parser.add_argument("--environment", choices=("staging", "production"), required=True)
    parser.add_argument("--policy-dir", default="waf/policies")
    parser.add_argument("--output", default="build/waf-deployment-plan.json")
    args = parser.parse_args()

    platforms = ("aws", "akamai") if args.platform == "both" else (args.platform,)
    policy_paths = sorted(Path(args.policy_dir).glob("*.json"))
    policies = [load_policy(path) for path in policy_paths]

    deployments = []
    skipped = []
    for policy in policies:
        if not policy["enabled"]:
            skipped.append({"rule_id": policy["rule_id"], "reason": "policy is disabled"})
            continue
        for platform in platforms:
            if platform in policy["targets"]:
                deployments.append({
                    "platform": platform,
                    "environment": args.environment,
                    "operation": "PLAN_ONLY",
                    "rule": render_rule(policy, platform, args.environment),
                })

    plan = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dry_run": True,
        "requested_platform": args.platform,
        "requested_environment": args.environment,
        "deployments": deployments,
        "skipped": skipped,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as output_file:
        json.dump(plan, output_file, ensure_ascii=False, indent=2)
        output_file.write("\n")

    print(f"Wrote dry-run plan to {output_path}")
    print(f"Planned deployments: {len(deployments)}; skipped policies: {len(skipped)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
