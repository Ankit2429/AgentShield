import pytest
from app.core.decision_engine import DecisionEngine, Decision, ReasonCode
from app.core.models import DetectionResult, ThreatResult, ThreatRule
from app.core.severity import Severity
from app.core.trust_engine import AgentTrustProfile, TrustStatus

@pytest.fixture
def decision_engine():
    return DecisionEngine()

def test_decision_allow_normal(decision_engine):
    detection = DetectionResult(is_malicious=False, risk_score=0.0, threat_count=0, threats=[])
    trust = AgentTrustProfile(agent_id="agent-1", trust_score=0.9, status=TrustStatus.TRUSTED, successful_requests=10)
    
    result = decision_engine.decide(detection_result=detection, trust_profile=trust)
    
    assert result.decision == Decision.ALLOW
    assert ReasonCode.CLEAN in result.reasoning

def test_decision_block_critical_threat(decision_engine):
    threat = ThreatResult(
        rule=ThreatRule(
            pattern="rm -rf",
            name="Destructive Remove Command",
            description="...",
            category="command_injection",
            severity=Severity.CRITICAL
        ),
        matched_text="rm -rf",
        position=0
    )
    detection = DetectionResult(is_malicious=True, risk_score=1.0, threat_count=1, threats=[threat])
    trust = AgentTrustProfile(agent_id="agent-1", trust_score=0.9, status=TrustStatus.TRUSTED, successful_requests=10)
    
    result = decision_engine.decide(detection_result=detection, trust_profile=trust)
    
    assert result.decision == Decision.BLOCK
    assert ReasonCode.COMMAND_INJECTION in result.reasoning

def test_decision_quarantine_untrusted_anomaly(decision_engine):
    detection = DetectionResult(is_malicious=False, risk_score=0.2, threat_count=0, threats=[])
    trust = AgentTrustProfile(agent_id="agent-1", trust_score=0.05, status=TrustStatus.QUARANTINED, successful_requests=2)
    
    result = decision_engine.decide(detection_result=detection, trust_profile=trust)
    
    assert result.decision == Decision.QUARANTINE
    assert ReasonCode.QUARANTINED_AGENT in result.reasoning
    assert ReasonCode.CRITICAL_TRUST in result.reasoning

def test_decision_interceptor_context(decision_engine):
    detection = DetectionResult(is_malicious=False, risk_score=0.0, threat_count=0, threats=[])
    trust = AgentTrustProfile(agent_id="agent-1", trust_score=0.9, status=TrustStatus.TRUSTED, successful_requests=10)
    
    context = {
        "auth_matrix_authorized": False
    }
    result = decision_engine.decide(detection_result=detection, trust_profile=trust, context=context)
    
    assert result.decision == Decision.BLOCK
    assert ReasonCode.UNAUTHORIZED_TOOL in result.reasoning
