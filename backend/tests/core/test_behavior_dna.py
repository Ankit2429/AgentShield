import pytest
from app.core.behavior_dna import BehaviorDNAEngine, BehaviorObservation

@pytest.fixture
def behavior_engine():
    return BehaviorDNAEngine()

def test_behavior_cold_start(behavior_engine):
    observation = BehaviorObservation(
        agent_id="agent-2",
        tool_name="search",
        message_length=50,
        risk_score=0.0,
        threat_categories=[]
    )
    analysis = behavior_engine.analyze_behavior(observation)
    assert analysis.deviation_level.name == "NORMAL"
    assert "Insufficient history" in analysis.details[0]

def test_behavior_training(behavior_engine):
    # Train the baseline
    for _ in range(5):
        obs = BehaviorObservation(
            agent_id="agent-2",
            tool_name="search",
            message_length=50,
            risk_score=0.0,
            threat_categories=[]
        )
        behavior_engine.register_observation(obs)
    
    profile = behavior_engine.get_profile("agent-2")
    assert profile.total_observations == 5
    assert profile.avg_message_length == 50.0

def test_behavior_anomaly_detection(behavior_engine):
    # Train normal baseline
    for _ in range(10):
        behavior_engine.register_observation(BehaviorObservation(
            agent_id="agent-2",
            tool_name="search",
            message_length=50,
            risk_score=0.0,
            threat_categories=[]
        ))
    
    # Introduce anomalous observation (new tool, massive length)
    anomalous_obs = BehaviorObservation(
        agent_id="agent-2",
        tool_name="execute_sql",
        message_length=5000,
        risk_score=0.2,
        threat_categories=[]
    )
    analysis = behavior_engine.analyze_behavior(anomalous_obs)
    
    assert analysis.deviation_level.name in ["SIGNIFICANT", "CRITICAL"]
    assert any("tool" in detail.lower() for detail in analysis.details)
    assert any("length" in detail.lower() for detail in analysis.details)

def test_behavior_poisoning_rejection(behavior_engine):
    malicious_obs = BehaviorObservation(
        agent_id="agent-2",
        tool_name="search",
        message_length=50,
        risk_score=0.9,
        threat_categories=["command_injection"]
    )
    behavior_engine.register_observation(malicious_obs)
    
    profile = behavior_engine.get_profile("agent-2")
    assert profile.total_observations == 1
    # Ensure stats were not updated due to poisoning guard
    assert profile.avg_message_length == 0.0
