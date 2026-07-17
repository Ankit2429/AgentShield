import pytest
import uuid
from datetime import datetime, timezone
from app.core.replay.replay_engine import ReplayEngine
from app.core.replay.replay_models import ReplayStage, SessionStatus, ReplayFrame

@pytest.fixture
def replay_engine():
    return ReplayEngine()

def test_replay_session_lifecycle(replay_engine):
    session = replay_engine.create_session("evt-1", "agent-1")
    session_id = session.session_id
    assert session_id is not None
    
    session = replay_engine.get_session(session_id)
    assert session.status == SessionStatus.IN_PROGRESS
    
    # Add a frame
    frame = ReplayFrame(
        frame_id=str(uuid.uuid4()),
        stage=ReplayStage.RECEIVED,
        timestamp=datetime.now(timezone.utc),
        title="Message Received",
        description="Received raw agent message",
        engine="API",
        risk_score=0.0,
        trust_score=0.8,
        decision=None,
        metadata={"length": 100}
    )
    replay_engine.add_frame(
        session_id=session_id,
        frame=frame
    )
    
    assert len(session.frames) == 1
    assert session.frames[0].stage == ReplayStage.RECEIVED
    
    # Complete session
    replay_engine.complete_session(
        session_id=session_id,
        overall_summary="Clean request."
    )
    
    assert session.status == SessionStatus.COMPLETE
    assert session.overall_summary == "Clean request."

def test_get_sessions(replay_engine):
    s1 = replay_engine.create_session("evt-1", "agent-1")
    s2 = replay_engine.create_session("evt-2", "agent-2")
    
    replay_engine.complete_session(s1.session_id, "Ok")
    
    sessions = replay_engine.list_sessions(limit=10)
    assert len(sessions) == 2
    
    filtered = replay_engine.list_sessions(agent_id="agent-1")
    assert len(filtered) == 1
    assert filtered[0].session_id == s1.session_id
