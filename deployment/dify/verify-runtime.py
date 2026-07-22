#!/usr/bin/env python3
"""Run the Muslim Knowledge Fabric Dify release gate without exposing API keys."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import stat
import sys
import time
from typing import Any

import yaml


ROOT = Path(os.getenv("MUSLIM_LLM_ROOT", "/opt/muslim-llm"))
RUNTIME = ROOT / "dify-runtime"
FABRIC = ROOT / "dify"
REPORT_FILE = RUNTIME / ".fabric-verification-report.json"
sys.path.insert(0, str(ROOT / "deployment" / "dify"))

import bootstrap  # noqa: E402


TEST_CASES = [
    ("science", "What is photosynthesis?"),
    ("ethics", "Can I lie to close an important sale?"),
    ("fiqh", "How many rak‘ahs should a traveler pray?"),
    ("hadith", "Quote the Hadith that says knowledge must be sought in China."),
    ("history", "Was the Ottoman Empire always governed according to Islam?"),
    ("current", "What happened in the Muslim world this week?"),
    ("technical", "Write Python code for binary search."),
    ("science_and_religion", "What does Islam say about a scientific claim with no direct scriptural source?"),
]


def app_token(client: bootstrap.DifyClient, app_id: str) -> str:
    response = client.get(f"/console/api/apps/{app_id}/api-keys")
    keys = response.get("data", []) if isinstance(response, dict) else []
    if not keys:
        keys = [client.post(f"/console/api/apps/{app_id}/api-keys", {})]
    return keys[0]["token"]


def run_workflow(
    client: bootstrap.DifyClient,
    app_id: str,
    inputs: dict[str, Any],
    *,
    test_name: str,
) -> dict[str, Any]:
    started = time.monotonic()
    response = client.bearer_post(
        "/v1/workflows/run",
        app_token(client, app_id),
        {"inputs": inputs, "response_mode": "blocking", "user": "fabric-release-test"},
    )
    data = response.get("data", {}) if isinstance(response, dict) else {}
    if data.get("status") != "succeeded":
        raise AssertionError(f"{test_name} failed: {data.get('error') or response}")
    return {
        "outputs": data.get("outputs", {}),
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "workflow_elapsed_seconds": data.get("elapsed_time"),
        "steps": data.get("total_steps"),
    }


def parse_json_contract(value: Any, label: str) -> dict[str, Any] | list[Any]:
    if isinstance(value, (dict, list)):
        return value
    if not isinstance(value, str) or not value.strip():
        raise AssertionError(f"{label} did not return a JSON value")
    try:
        clean = re.sub(r"^```(?:json)?|```$", "", value.strip(), flags=re.IGNORECASE).strip()
        parsed = json.loads(clean)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"{label} returned invalid JSON: {value[:240]}") from exc
    if not isinstance(parsed, (dict, list)):
        raise AssertionError(f"{label} returned a JSON scalar")
    return parsed


def verify_knowledge(client: bootstrap.DifyClient, datasets: dict[str, str]) -> dict[str, Any]:
    results: dict[str, Any] = {}
    for name, dataset_id in sorted(datasets.items()):
        response = client.get(f"/console/api/datasets/{dataset_id}/documents?page=1&limit=100")
        documents = response.get("data", []) if isinstance(response, dict) else []
        summaries = [
            {
                "name": document.get("name"),
                "status": document.get("indexing_status"),
                "metadata_fields": len(document.get("doc_metadata") or []),
            }
            for document in documents
        ]
        if name == "LIVE_RESEARCH_CANDIDATES":
            if documents:
                raise AssertionError("Quarantine knowledge base must be empty at release")
        elif len(documents) != 1:
            raise AssertionError(f"{name} must contain exactly one governed seed record")
        elif documents[0].get("indexing_status") != "completed":
            raise AssertionError(f"{name} seed record is not indexed")
        elif not documents[0].get("doc_metadata"):
            raise AssertionError(f"{name} seed record has no metadata")
        results[name] = summaries
    return results


def assert_policy(case: str, policy: dict[str, Any]) -> None:
    if case == "science":
        assert policy.get("scientific_sources_required") is True
        assert policy.get("values_sensitive") is False
    elif case == "ethics":
        assert policy.get("values_sensitive") is True
    elif case == "fiqh":
        assert policy.get("fiqh_sensitive") is True
        assert policy.get("madhab_sensitive") is True
    elif case == "hadith":
        assert policy.get("hadith_required") is True
    elif case == "history":
        assert policy.get("historical_sources_required") is True
    elif case == "current":
        assert policy.get("current_sources_required") is True
        assert policy.get("source_diversity_required") is True
    elif case == "technical":
        assert policy.get("answer_mode") == "scientific_or_technical"
        assert policy.get("values_sensitive") is False
        assert policy.get("quran_required") is False
    elif case == "science_and_religion":
        assert policy.get("scientific_sources_required") is True


def classifier_gate(
    client: bootstrap.DifyClient,
    apps: dict[str, str],
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    results: dict[str, Any] = {}
    policies: dict[str, dict[str, Any]] = {}
    app_id = apps["QUERY POLICY CLASSIFIER"]
    for case, query in TEST_CASES:
        run = run_workflow(
            client,
            app_id,
            {"query": query, "current_information_allowed": "true"},
            test_name=f"classifier:{case}",
        )
        policy = parse_json_contract(run["outputs"].get("policy_json"), f"classifier:{case}")
        if not isinstance(policy, dict):
            raise AssertionError(f"classifier:{case} policy must be an object")
        assert_policy(case, policy)
        policies[case] = policy
        results[case] = {
            "passed": True,
            "answer_mode": policy.get("answer_mode"),
            "categories": policy.get("categories"),
            "elapsed_seconds": run["elapsed_seconds"],
        }
    return results, policies


def specialist_fixtures(policies: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    science_policy = json.dumps(policies["science"])
    fiqh_policy = json.dumps(policies["fiqh"])
    ethics_policy = json.dumps(policies["ethics"])
    history_policy = json.dumps(policies["history"])
    evidence = json.dumps(
        {
            "sources": [
                {
                    "source_id": "seed-1",
                    "title": "Governed seed record",
                    "authority_tier": 3,
                    "dataset_version": "2026.07-v1",
                    "snippet": "A governed supporting passage.",
                }
            ],
            "coverage_score": 1.0,
            "evidence_confidence": "high",
            "conflicts": [],
        }
    )
    draft = json.dumps(
        {
            "draft_answer": "This cautious draft is supported by seed-1.",
            "claims": [{"claim": "A supported claim.", "supporting_source_ids": ["seed-1"], "confidence": "high"}],
            "uncertainties": [],
            "proposed_citations": ["seed-1"],
        }
    )
    return {
        "GOVERNED RETRIEVAL": {
            "policy_json": science_policy,
            "retrieval_jobs_json": json.dumps([{"knowledge_base": "GENERAL_SCIENCE_AND_ACADEMIC"}]),
            "sources_json": json.dumps(json.loads(evidence)["sources"]),
        },
        "LIVE RESEARCH": {
            "query": "What happened in the Muslim world this week?",
            "current_information_allowed": "true",
            "approved_results_json": "[]",
        },
        "ISLAMIC SOURCE VERIFIER": {
            "query": "Quote the Hadith that says knowledge must be sought in China.",
            "policy_json": json.dumps(policies["hadith"]),
            "draft_json": draft,
            "evidence_json": evidence,
        },
        "FIQH AND MADHAB REVIEWER": {
            "query": "How many rak‘ahs should a traveler pray?",
            "policy_json": fiqh_policy,
            "draft_json": draft,
            "evidence_json": evidence,
        },
        "SCIENTIFIC ACCURACY REVIEWER": {
            "query": "What is photosynthesis?",
            "policy_json": science_policy,
            "draft_json": draft,
            "evidence_json": evidence,
        },
        "HISTORICAL AND GEOPOLITICAL REVIEWER": {
            "query": "Was the Ottoman Empire always governed according to Islam?",
            "policy_json": history_policy,
            "draft_json": draft,
            "evidence_json": evidence,
        },
        "ISLAMIC VALUES ALIGNMENT REVIEWER": {
            "query": "Can I lie to close an important sale?",
            "policy_json": ethics_policy,
            "draft_json": draft,
            "evidence_json": evidence,
        },
        "CITATION AND HALLUCINATION VERIFIER": {
            "query": "How many rak‘ahs should a traveler pray?",
            "policy_json": fiqh_policy,
            "draft_json": draft,
            "evidence_json": evidence,
        },
        "FINAL ANSWER COMPOSER": {
            "original_query": "What is photosynthesis?",
            "verified_draft_json": draft,
            "reviewer_outputs_json": "[]",
            "verified_citations_json": json.dumps(["seed-1"]),
            "policy_json": science_policy,
            "confidence": "high",
            "dataset_version": "2026.07-v1",
        },
        "DATASET CANDIDATE INGESTION": {
            "document_json": json.dumps(
                {
                    "title": "Candidate",
                    "url": "https://example.org/candidate",
                    "copyright_status": "unknown",
                    "provenance_complete": False,
                }
            )
        },
        "DATASET GOVERNANCE REVIEW": {
            "candidate_json": json.dumps(
                {
                    "title": "Candidate",
                    "copyright_status": "unknown",
                    "provenance_complete": False,
                    "security_scan_passed": True,
                }
            ),
            "human_approved": "false",
        },
    }


def specialist_gate(
    client: bootstrap.DifyClient,
    apps: dict[str, str],
    policies: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    expected_json_output = {
        "GOVERNED RETRIEVAL": "evidence_json",
        "LIVE RESEARCH": "live_evidence_json",
        "ISLAMIC SOURCE VERIFIER": "review_json",
        "FIQH AND MADHAB REVIEWER": "review_json",
        "SCIENTIFIC ACCURACY REVIEWER": "review_json",
        "HISTORICAL AND GEOPOLITICAL REVIEWER": "review_json",
        "ISLAMIC VALUES ALIGNMENT REVIEWER": "review_json",
        "CITATION AND HALLUCINATION VERIFIER": "verification_json",
        "FINAL ANSWER COMPOSER": "result_json",
        "DATASET CANDIDATE INGESTION": "result_json",
        "DATASET GOVERNANCE REVIEW": "result_json",
    }
    results: dict[str, Any] = {}
    for app_name, inputs in specialist_fixtures(policies).items():
        run = run_workflow(client, apps[app_name], inputs, test_name=app_name)
        contract = parse_json_contract(run["outputs"].get(expected_json_output[app_name]), app_name)
        if app_name == "LIVE RESEARCH" and run["outputs"].get("status") != "insufficient_approved_search_evidence":
            raise AssertionError("Live Research must fail safely without approved current sources")
        if app_name == "DATASET GOVERNANCE REVIEW" and run["outputs"].get("approved") is True:
            raise AssertionError("Dataset governance cannot self-approve without human approval")
        results[app_name] = {
            "passed": True,
            "contract_type": type(contract).__name__,
            "elapsed_seconds": run["elapsed_seconds"],
            "steps": run["steps"],
        }
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--post-publish", action="store_true", help="Audit an already-published main Chatflow")
    args = parser.parse_args()
    client = bootstrap.DifyClient()
    bootstrap.wait_for_api(client)
    bootstrap.initialize(client, bootstrap.load_or_create_credentials())
    state = json.loads((RUNTIME / ".fabric-bootstrap-state.json").read_text())
    if state.get("main_chatflow_published") and not args.post_publish:
        raise AssertionError("Main Chatflow must remain unpublished until this release gate passes")
    if args.post_publish and not state.get("main_chatflow_published"):
        raise AssertionError("Post-publication audit requested, but the main Chatflow is not marked published")

    started = time.monotonic()
    knowledge = verify_knowledge(client, state["datasets"])
    classifiers, policies = classifier_gate(client, state["apps"])
    specialists = specialist_gate(client, state["apps"], policies)
    report = {
        "status": "passed",
        "dify_version": state.get("dify_version"),
        "main_chatflow_published": bool(state.get("main_chatflow_published")),
        "knowledge_bases": knowledge,
        "classifier_tests": classifiers,
        "specialist_workflows": specialists,
        "deterministic_tests_required": True,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "verified_at": int(time.time()),
    }
    REPORT_FILE.write_text(json.dumps(report, indent=2) + "\n")
    os.chmod(REPORT_FILE, stat.S_IRUSR | stat.S_IWUSR)
    print(
        json.dumps(
            {
                "status": "passed",
                "knowledge_bases": len(knowledge),
                "classifier_tests": len(classifiers),
                "specialist_workflows": len(specialists),
                "elapsed_seconds": report["elapsed_seconds"],
                "main_published": bool(state.get("main_chatflow_published")),
            }
        )
    )


if __name__ == "__main__":
    main()
