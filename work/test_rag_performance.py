import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.chat_stream.routing import route_request
from app.chat_reliability import classify_chat_run
from app.rag import is_islamic_query


def test_rag_is_conditional():
    neutral = route_request("Write a Python function for binary search.", requested_mode="auto", islamic=False, fiqh=False, values_sensitive=False)
    fiqh = route_request("How should a traveler pray?", requested_mode="auto", islamic=True, fiqh=True, values_sensitive=False)
    exact = route_request("Quote the Quran reference about justice.", requested_mode="auto", islamic=True, fiqh=False, values_sensitive=False)
    assert neutral.retrieval_required is False
    assert fiqh.name == "retrieval_required"
    assert exact.name == "retrieval_required"


def test_traveler_prayer_is_fiqh_and_source_sensitive():
    message = "How should a traveler pray?"
    run = classify_chat_run(message, is_islamic_query(message), False)
    route = route_request(message, requested_mode="auto", islamic=run.query_is_islamic, fiqh=run.madhab_sensitive, values_sensitive=False)
    assert run.madhab_sensitive is True
    assert route.name == "retrieval_required"
