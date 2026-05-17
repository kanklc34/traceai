from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime


class Base(DeclarativeBase):
    pass


class Trace(Base):
    __tablename__ = "traces"
    id = Column(Integer, primary_key=True)
    trace_id = Column(String(50), unique=True, index=True)
    service = Column(String(50), index=True)
    operation = Column(String(100))
    duration_ms = Column(Integer)
    status = Column(String(20))
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    metadata_json = Column(Text)


class AIReport(Base):
    __tablename__ = "ai_reports"
    id = Column(Integer, primary_key=True)
    incident_id = Column(String(50), index=True)
    trace_id = Column(String(50), index=True)
    service = Column(String(50), index=True)
    root_cause = Column(String(255))
    impact_level = Column(String(20))
    explanation = Column(Text)
    recommended_action = Column(Text)
    confidence_score = Column(Float)
    evidence_json = Column(Text)
    gemma_model = Column(String(50))
    tools_used_json = Column(Text)
    tools_output = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class AgentStep(Base):
    __tablename__ = "agent_steps"
    id = Column(Integer, primary_key=True)
    incident_id = Column(String(50), index=True)
    service = Column(String(50), index=True)
    step_order = Column(Integer)
    tool_name = Column(String(100))
    tool_input = Column(Text)
    tool_output = Column(Text)
    status = Column(String(20), default="complete")
    created_at = Column(DateTime, default=datetime.utcnow)


class SystemState(Base):
    __tablename__ = "system_state"
    id = Column(Integer, primary_key=True)
    service = Column(String(50))
    incident_id = Column(String(50), nullable=True)
    status = Column(String(100))
    updated_at = Column(DateTime, default=datetime.utcnow)
