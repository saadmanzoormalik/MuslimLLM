import json
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
DIFY = ROOT / "dify"
APPS = DIFY / "apps"
sys.path.insert(0, str(ROOT))


EXPECTED_APPS = {
    "MUSLIM KNOWLEDGE FABRIC",
    "QUERY POLICY CLASSIFIER",
    "GOVERNED RETRIEVAL",
    "LIVE RESEARCH",
    "ISLAMIC SOURCE VERIFIER",
    "FIQH AND MADHAB REVIEWER",
    "SCIENTIFIC ACCURACY REVIEWER",
    "HISTORICAL AND GEOPOLITICAL REVIEWER",
    "ISLAMIC VALUES ALIGNMENT REVIEWER",
    "CITATION AND HALLUCINATION VERIFIER",
    "FINAL ANSWER COMPOSER",
    "DATASET CANDIDATE INGESTION",
    "DATASET GOVERNANCE REVIEW",
}

EXPECTED_KBS = {
    "QURAN_VERIFIED", "HADITH_VERIFIED", "TAFSIR_AND_CLASSICAL_SCHOLARSHIP", "FIQH_AND_USUL",
    "ISLAMIC_HISTORY_AND_CIVILIZATION", "MODERN_MUSLIM_WORLD", "GENERAL_SCIENCE_AND_ACADEMIC",
    "LIVE_RESEARCH_CANDIDATES",
}


def assert_true(value, message):
    if not value:
        raise AssertionError(message)


def main():
    manifest = json.loads((DIFY / "app-manifest.json").read_text(encoding="utf-8"))
    assert_true(manifest["dify_target"] == "1.16.0", "Unexpected Dify target")
    assert_true(len(manifest["applications"]) == 13, "Expected 13 Dify applications")

    loaded = {}
    for path in sorted(APPS.glob("*.yml")):
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        name = document["app"]["name"]
        loaded[name] = document
        assert_true(document["version"] == "0.7.0", f"{name} has wrong DSL version")
        graph = document["workflow"]["graph"]
        node_ids = {node["id"] for node in graph["nodes"]}
        assert_true("start" in node_ids, f"{name} missing Start")
        for graph_edge in graph["edges"]:
            assert_true(graph_edge["source"] in node_ids, f"{name} edge has missing source")
            assert_true(graph_edge["target"] in node_ids, f"{name} edge has missing target")
        if any(node["data"]["type"] == "llm" for node in graph["nodes"]):
            assert_true(document["dependencies"], f"{name} uses an LLM without model dependency")

    assert_true(set(loaded) == EXPECTED_APPS, f"Unexpected app set: {set(loaded) ^ EXPECTED_APPS}")
    main_flow = loaded["MUSLIM KNOWLEDGE FABRIC"]
    titles = [node["data"]["title"] for node in main_flow["workflow"]["graph"]["nodes"]]
    required_order = [
        "Start", "Input Validation", "Query Policy Classifier", "Retrieval Plan",
        "Evidence Merge and Sufficiency", "Answer Drafting Agent", "Citation and Release Gate",
        "Final Answer Composer", "Answer",
    ]
    assert_true(titles == required_order, f"Main node order differs: {titles}")

    classifier_types = {node["data"]["type"] for node in loaded["QUERY POLICY CLASSIFIER"]["workflow"]["graph"]["nodes"]}
    assert_true({"question-classifier", "parameter-extractor", "code"} <= classifier_types, "Classifier is missing required node types")

    citation_types = [node["data"]["type"] for node in loaded["CITATION AND HALLUCINATION VERIFIER"]["workflow"]["graph"]["nodes"]]
    assert_true(citation_types.count("code") == 2 and "llm" in citation_types, "Citation verifier lacks deterministic and semantic checks")

    kb_manifest = yaml.safe_load((DIFY / "knowledge-bases.yaml").read_text(encoding="utf-8"))
    kb_names = {item["name"] for item in kb_manifest["knowledge_bases"]}
    assert_true(kb_names == EXPECTED_KBS, "Knowledge base set differs")
    candidate = next(item for item in kb_manifest["knowledge_bases"] if item["name"] == "LIVE_RESEARCH_CANDIDATES")
    assert_true(candidate["quarantine"] and not candidate["production_retrieval_allowed"], "Candidate KB is not quarantined")

    publications = yaml.safe_load((DIFY / "tool-publication.yaml").read_text(encoding="utf-8"))["workflows"]
    assert_true(len(publications) == 12, "Expected 12 workflow-as-tool publication names")
    print("Dify Muslim Knowledge Fabric DSL tests passed")


if __name__ == "__main__":
    main()
