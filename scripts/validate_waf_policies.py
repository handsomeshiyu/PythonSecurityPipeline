#!/usr/bin/env python3
"""Validate vendor-neutral WAF policies using only the Python standard library."""

import argparse
import json
import os
import re
import sys
from pathlib import Path


JIRA_PATTERN = re.compile(r"^[A-Z][A-Z0-9]+-[0-9]+$")
RULE_PATTERN = re.compile(r"^[A-Z][A-Z0-9]+-[0-9]+-[a-z0-9][a-z0-9-]*$")
ALLOWED_TARGETS = {"aws", "akamai"}
ALLOWED_STAGING_ACTIONS = {"monitor"}
ALLOWED_PRODUCTION_ACTIONS = {"block", "allow"}
ALLOWED_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}


def require(condition, message, errors):
    if not condition:
        errors.append(message)


def validate_policy(path):
    errors = []
    try:
        with path.open(encoding="utf-8") as policy_file:
            policy = json.load(policy_file)
    except (OSError, json.JSONDecodeError) as exc:
        return None, [f"{path}: cannot read valid JSON: {exc}"]

    prefix = str(path)
    require(policy.get("schema_version") == 1, f"{prefix}: schema_version must be 1", errors)

    jira_issue = policy.get("jira_issue", "")
    require(bool(JIRA_PATTERN.fullmatch(jira_issue)), f"{prefix}: invalid jira_issue", errors)

    rule_id = policy.get("rule_id", "")
    require(bool(RULE_PATTERN.fullmatch(rule_id)), f"{prefix}: invalid rule_id", errors)
    require(rule_id.startswith(f"{jira_issue}-"), f"{prefix}: rule_id must start with jira_issue", errors)
    require(path.stem.startswith(rule_id), f"{prefix}: filename must start with rule_id", errors)

    require(isinstance(policy.get("description"), str) and bool(policy["description"].strip()),
            f"{prefix}: description is required", errors)
    require(isinstance(policy.get("enabled"), bool), f"{prefix}: enabled must be boolean", errors)

    targets = policy.get("targets")
    require(isinstance(targets, list) and bool(targets), f"{prefix}: targets must be a non-empty list", errors)
    if isinstance(targets, list):
        require(set(targets).issubset(ALLOWED_TARGETS), f"{prefix}: targets may only contain aws/akamai", errors)
        require(len(targets) == len(set(targets)), f"{prefix}: targets must not contain duplicates", errors)

    priority = policy.get("priority")
    require(isinstance(priority, int) and 0 <= priority <= 999999,
            f"{prefix}: priority must be an integer from 0 to 999999", errors)

    match = policy.get("match")
    require(isinstance(match, dict), f"{prefix}: match must be an object", errors)
    if isinstance(match, dict):
        path_prefix = match.get("path_prefix")
        require(isinstance(path_prefix, str) and path_prefix.startswith("/"),
                f"{prefix}: match.path_prefix must start with /", errors)

    rollout = policy.get("rollout")
    require(isinstance(rollout, dict), f"{prefix}: rollout must be an object", errors)
    if isinstance(rollout, dict):
        require(rollout.get("staging_action") in ALLOWED_STAGING_ACTIONS,
                f"{prefix}: staging_action must be monitor", errors)
        require(rollout.get("production_action") in ALLOWED_PRODUCTION_ACTIONS,
                f"{prefix}: production_action must be block or allow", errors)

    tests = policy.get("tests")
    require(isinstance(tests, list) and len(tests) >= 2, f"{prefix}: at least two tests are required", errors)
    expected_results = set()
    if isinstance(tests, list):
        test_names = set()
        for index, test in enumerate(tests):
            test_prefix = f"{prefix}: tests[{index}]"
            require(isinstance(test, dict), f"{test_prefix} must be an object", errors)
            if not isinstance(test, dict):
                continue
            name = test.get("name")
            require(isinstance(name, str) and bool(name.strip()), f"{test_prefix}.name is required", errors)
            if isinstance(name, str):
                require(name not in test_names, f"{test_prefix}.name must be unique", errors)
                test_names.add(name)
            request = test.get("request")
            require(isinstance(request, dict), f"{test_prefix}.request must be an object", errors)
            if isinstance(request, dict):
                require(request.get("method") in ALLOWED_METHODS,
                        f"{test_prefix}.request.method is invalid", errors)
                request_path = request.get("path")
                require(isinstance(request_path, str) and request_path.startswith("/"),
                        f"{test_prefix}.request.path must start with /", errors)
            expected_match = test.get("expected_match")
            require(isinstance(expected_match, bool), f"{test_prefix}.expected_match must be boolean", errors)
            if isinstance(expected_match, bool):
                expected_results.add(expected_match)
        require(expected_results == {False, True},
                f"{prefix}: tests must include both matching and non-matching requests", errors)

    return policy, errors


def validate_branch(branch_name, jira_issues):
    if branch_name in {"main", "master"}:
        return []
    if not branch_name:
        return ["branch name is unavailable; set BRANCH_NAME or GIT_BRANCH"]
    issues_in_branch = set(re.findall(r"[A-Z][A-Z0-9]+-[0-9]+", branch_name.upper()))
    if not issues_in_branch:
        return [f"branch '{branch_name}' must contain a Jira key, for example waf/SEC-1024-description"]
    missing = jira_issues - issues_in_branch
    if missing:
        return [f"branch '{branch_name}' does not reference policy Jira issue(s): {', '.join(sorted(missing))}"]
    return []


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy-dir", default="waf/policies")
    parser.add_argument("--enforce-branch", action="store_true")
    args = parser.parse_args()

    policy_dir = Path(args.policy_dir)
    paths = sorted(policy_dir.glob("*.json"))
    if not paths:
        print(f"ERROR: no policy files found in {policy_dir}", file=sys.stderr)
        return 1

    all_errors = []
    policies = []
    for path in paths:
        policy, errors = validate_policy(path)
        all_errors.extend(errors)
        if policy is not None:
            policies.append((path, policy))

    rule_ids = {}
    priorities = {}
    for path, policy in policies:
        rule_id = policy.get("rule_id")
        priority = policy.get("priority")
        if rule_id in rule_ids:
            all_errors.append(f"{path}: duplicate rule_id also used by {rule_ids[rule_id]}")
        else:
            rule_ids[rule_id] = path
        if priority in priorities:
            all_errors.append(f"{path}: duplicate priority also used by {priorities[priority]}")
        else:
            priorities[priority] = path

    if args.enforce_branch:
        branch_name = os.environ.get("BRANCH_NAME") or os.environ.get("GIT_BRANCH", "")
        jira_issues = {policy.get("jira_issue") for _, policy in policies if policy.get("jira_issue")}
        all_errors.extend(validate_branch(branch_name, jira_issues))

    if all_errors:
        for error in all_errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"Validated {len(policies)} WAF policy file(s).")
    for path, policy in policies:
        state = "enabled" if policy["enabled"] else "disabled"
        print(f"- {policy['rule_id']} ({state}) -> {', '.join(policy['targets'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
