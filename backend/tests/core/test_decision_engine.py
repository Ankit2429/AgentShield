import pytest
from app.core.decision_engine import DecisionEngine
from app.core.models import DetectionResult, ThreatResult
from app.core.behavior_dna import BehaviorAnalysis, DeviationLevel
from app.core.trust_engine import AgentTrustProfile

@pytest.fixture
def decision_engine():
    return DecisionEngine()

def test_decision_allow_normal(decision_engine):
    detection = DetectionResult(is_malicious=False, risk_score=0.0, threats=[])
    behavior = BehaviorAnalysis(deviation_level=DeviationLevel.NORMAL, details=[], confidence=1.0)
    trust = AgentTrustProfile(agent_id="agent-1", trust_score=0.9, successful_requests=10)
    
    result = decision_engine.evaluate(detection, behavior, trust)
    
    assert result.decision.name == "ALLOW"
    assert "LOW_RISK" in [r.code for r in result.reasons]

def test_decision_block_critical_threat(decision_engine):
    threat = ThreatResult(
        rule_id="cmd_inj",
        category="command_injection",
        matched_text="rm -rf",
        start_pos=0,
        end_pos=5,
        severity="CRITICAL"
    )
    detection = DetectionResult(is_malicious=True, risk_score=1.0, threats=[threat])
    behavior = BehaviorAnalysis(deviation_level=DeviationLevel.NORMAL, details=[], confidence=1.0)
    trust = AgentTrustProfile(agent_id="agent-1", trust_score=0.9, successful_requests=10)
    
    result = decision_engine.evaluate(detection, behavior, trust)
    
    assert result.decision.name == "BLOCK"
    assert "CRITICAL_THREAT_DETECTED" in [r.code for r in result.reasons]

def test_decision_quarantine_untrusted_anomaly(decision_engine):
    detection = DetectionResult(is_malicious=False, risk_score=0.2, threats=[])
    behavior = BehaviorAnalysis(deviation_level=DeviationLevel.CRITICAL, details=["Massive deviation"], confidence=0.9)
    trust = AgentTrustProfile(agent_id="agent-1", trust_score=0.2, successful_requests=2)
    
    result = decision_engine.evaluate(detection, behavior, trust)
    
    assert result.decision.name == "QUARANTINE"
    assert "CRITICAL_ANOMALY" in [r.code for r in result.reasons]
    assert "LOW_TRUST" in [r.code for r in result.reasons]

def test_decision_interceptor_context(decision_engine):
    detection = DetectionResult(is_malicious=False, risk_score=0.0, threats=[])
    behavior = BehaviorAnalysis(deviation_level=DeviationLevel.NORMAL, details=[], confidence=1.0)
    trust = AgentTrustProfile(agent_id="agent-1", trust_score=0.9, successful_requests=10)
    
    context = {
        "auth_matrix_authorized": False
    }
    result = decision_engine.evaluate(detection, behavior, trust, context)
    
    assert result.decision.name == "BLOCK"
    assert "UNAUTHORIZED_TOOL" in [r.code for r in result.reasons]
