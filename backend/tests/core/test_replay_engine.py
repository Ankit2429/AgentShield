import pytest
from app.core.replay.replay_engine import ReplayEngine
from app.core.replay.replay_models import ReplayStage, SessionStatus

@pytest.fixture
def replay_engine():
    return ReplayEngine()

def test_replay_session_lifecycle(replay_engine):
    session_id = replay_engine.create_session("agent-1")
    assert session_id is not None
    
    session = replay_engine.get_session(session_id)
    assert session.status == SessionStatus.IN_PROGRESS
    
    # Add a frame
    replay_engine.add_frame(
        session_id=session_id,
        stage=ReplayStage.RECEIVED,
        title="Message Received",
        engine="API",
        risk_score=0.0,
        trust_score=0.8,
        decision=None,
        metadata={"length": 100}
    )
    
    assert len(session.frames) == 1
    assert session.frames[0].stage == ReplayStage.RECEIVED
    
    # Complete session
    replay_engine.complete_session(
        session_id=session_id,
        final_decision="ALLOW",
        summary="Clean request."
    )
    
    assert session.status == SessionStatus.COMPLETE
    assert session.final_decision == "ALLOW"
    assert session.summary == "Clean request."

def test_get_sessions(replay_engine):
    sid1 = replay_engine.create_session("agent-1")
    sid2 = replay_engine.create_session("agent-2")
    
    replay_engine.complete_session(sid1, "ALLOW", "Ok")
    
    sessions = replay_engine.get_sessions(limit=10)
    assert len(sessions) == 2
    
    filtered = replay_engine.get_sessions(agent_id="agent-1")
    assert len(filtered) == 1
    assert filtered[0].session_id == sid1
