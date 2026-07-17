import pytest
from app.core.trust_engine import TrustEngine, TrustTrend

@pytest.fixture
def trust_engine():
    return TrustEngine()

def test_trust_engine_new_agent(trust_engine):
    profile = trust_engine.register_agent("agent-1")
    assert profile.agent_id == "agent-1"
    assert profile.trust_score == 0.85  # Initial baseline trust score
    assert profile.successful_requests == 0

def test_trust_engine_successful_events(trust_engine):
    trust_engine.record_success("agent-1")
    trust_engine.record_success("agent-1")
    profile = trust_engine.get_profile("agent-1")
    assert profile.successful_requests == 2
    assert profile.trust_score > 0.85  # Score should increase

def test_trust_engine_blocked_event(trust_engine):
    trust_engine.record_success("agent-1")
    initial_score = trust_engine.get_profile("agent-1").trust_score
    trust_engine.record_block("agent-1")
    new_score = trust_engine.get_profile("agent-1").trust_score
    assert new_score < initial_score
    assert trust_engine.get_profile("agent-1").blocked_requests == 1

def test_trust_engine_poisoning_cap(trust_engine):
    profile = trust_engine.register_agent("agent-1")
    initial_score = profile.trust_score
    trust_engine.record_success("agent-1")
    new_score = trust_engine.get_profile("agent-1").trust_score
    assert round(new_score - initial_score, 4) <= 0.05  # Delta cap

def test_trust_engine_trend(trust_engine):
    # Drive trust up to establish an improving trend
    for _ in range(10):
        trust_engine.record_success("agent-1")
    profile = trust_engine.get_profile("agent-1")
    assert profile.trend in [TrustTrend.IMPROVING, TrustTrend.STABLE]
