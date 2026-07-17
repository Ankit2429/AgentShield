import pytest
from app.core.behavior_dna import BehaviorDNAEngine, BehaviorObservation, DeviationLevel

@pytest.fixture
def behavior_engine():
    return BehaviorDNAEngine()

def test_behavior_cold_start(behavior_engine):
    observation = BehaviorObservation(
        requested_tool="search",
        message_length=50,
        risk_score=0.0,
        threat_categories=[]
    )
    analysis = behavior_engine.analyze_behavior("agent-2", observation)
    assert analysis.deviation_level == DeviationLevel.NORMAL
    assert "Baseline not yet established" in analysis.summary

def test_behavior_training(behavior_engine):
    # Train the baseline
    for _ in range(5):
        obs = BehaviorObservation(
            requested_tool="search",
            message_length=50,
            risk_score=0.0,
            threat_categories=[]
        )
        behavior_engine.register_observation("agent-2", obs)
    
    profile = behavior_engine.get_profile("agent-2")
    assert profile.observations == 5
    assert profile.average_message_length == 50.0

def test_behavior_anomaly_detection(behavior_engine):
    # Train normal baseline
    for _ in range(10):
        behavior_engine.register_observation("agent-2", BehaviorObservation(
            requested_tool="search",
            message_length=50,
            risk_score=0.0,
            threat_categories=[]
        ))
    
    # Introduce anomalous observation (new tool, massive length)
    anomalous_obs = BehaviorObservation(
        requested_tool="execute_sql",
        message_length=5000,
        risk_score=0.2,
        threat_categories=[]
    )
    analysis = behavior_engine.analyze_behavior("agent-2", anomalous_obs)
    
    assert analysis.deviation_level in [DeviationLevel.HIGH, DeviationLevel.CRITICAL]
    assert any("tool" in reason.lower() for reason in analysis.reasons)
    assert any("length" in reason.lower() for reason in analysis.reasons)

def test_behavior_poisoning_rejection(behavior_engine):
    malicious_obs = BehaviorObservation(
        requested_tool="search",
        message_length=50,
        risk_score=0.9,
        threat_categories=["command_injection"]
    )
    behavior_engine.register_observation("agent-2", malicious_obs)
    
    profile = behavior_engine.get_profile("agent-2")
    assert profile.observations == 1
    # Ensure stats were not updated due to poisoning guard
    assert profile.average_message_length == 0.0
