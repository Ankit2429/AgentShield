import pytest
from app.core.trust_engine import TrustEngine

@pytest.fixture
def trust_engine():
    return TrustEngine()

def test_trust_engine_new_agent(trust_engine):
    profile = trust_engine.get_profile("agent-1")
    assert profile.agent_id == "agent-1"
    assert profile.trust_score == 0.5  # Neutral prior
    assert profile.successful_requests == 0

def test_trust_engine_successful_events(trust_engine):
    trust_engine.record_event("agent-1", success=True)
    trust_engine.record_event("agent-1", success=True)
    profile = trust_engine.get_profile("agent-1")
    assert profile.successful_requests == 2
    assert profile.trust_score > 0.5  # Score should increase

def test_trust_engine_blocked_event(trust_engine):
    trust_engine.record_event("agent-1", success=True)
    initial_score = trust_engine.get_profile("agent-1").trust_score
    trust_engine.record_event("agent-1", blocked=True)
    new_score = trust_engine.get_profile("agent-1").trust_score
    assert new_score < initial_score
    assert trust_engine.get_profile("agent-1").blocked_requests == 1

def test_trust_engine_poisoning_cap(trust_engine):
    profile = trust_engine.get_profile("agent-1")
    initial_score = profile.trust_score
    trust_engine.record_event("agent-1", success=True)
    new_score = trust_engine.get_profile("agent-1").trust_score
    assert (new_score - initial_score) <= 0.05  # Delta cap

def test_trust_engine_trend(trust_engine):
    # Drive trust up to establish an improving trend
    for _ in range(10):
        trust_engine.record_event("agent-1", success=True)
    profile = trust_engine.get_profile("agent-1")
    assert profile.trend in ["improving", "stable"]
