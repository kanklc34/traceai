import json
import uuid
import random
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession
from ...database import get_db
from ...models.orm import Trace, AIReport, SystemState, AgentStep
from ...models.schemas import TraceIngest

router = APIRouter()


@router.post("/ingest")
async def ingest_trace(data: TraceIngest, db: AsyncSession = Depends(get_db)):
    total_latency = sum(s.latency_ms for s in data.spans) if data.spans else 0
    status = "error" if any(s.status == "error" for s in data.spans) else "ok"

    new_trace = Trace(
        trace_id=data.trace_id,
        service=data.service,
        operation=data.spans[0].operation if data.spans else "unknown",
        duration_ms=int(total_latency),
        status=status,
        timestamp=data.timestamp,
    )
    db.add(new_trace)
    await db.commit()
    return {"status": "accepted", "trace_id": data.trace_id}


@router.get("/traces")
async def get_traces(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Trace).order_by(Trace.timestamp.desc()).limit(50))
    return result.scalars().all()


@router.get("/reports")
async def get_reports(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AIReport).order_by(AIReport.created_at.desc()).limit(10))
    reports = result.scalars().all()
    return [_serialize_report(r) for r in reports]


@router.get("/agent-steps")
async def get_agent_steps(
    incident_id: str | None = Query(None),
    service: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(AgentStep).order_by(AgentStep.step_order.asc())
    if incident_id:
        query = query.where(AgentStep.incident_id == incident_id)
    elif service:
        sub = (
            select(AgentStep.incident_id)
            .where(AgentStep.service == service)
            .order_by(AgentStep.created_at.desc())
            .limit(1)
        )
        latest = (await db.execute(sub)).scalar_one_or_none()
        if latest:
            query = query.where(AgentStep.incident_id == latest)
        else:
            return []
    else:
        query = query.order_by(AgentStep.created_at.desc()).limit(30)

    result = await db.execute(query)
    steps = result.scalars().all()
    return [_serialize_step(s) for s in steps]


@router.get("/incidents/latest")
async def get_latest_incident(db: AsyncSession = Depends(get_db)):
    state_result = await db.execute(select(SystemState))
    active_states = state_result.scalars().all()
    analyzing = len(active_states) > 0
    active_state = active_states[0] if active_states else None

    incident_id = None
    service = None
    if active_state:
        incident_id = active_state.incident_id
        service = active_state.service
    else:
        latest_step = await db.execute(
            select(AgentStep)
            .order_by(AgentStep.created_at.desc())
            .limit(1)
        )
        step = latest_step.scalar_one_or_none()
        if step:
            incident_id = step.incident_id
            service = step.service

    report = None
    if incident_id:
        report_result = await db.execute(
            select(AIReport)
            .where(AIReport.incident_id == incident_id)
            .order_by(AIReport.created_at.desc())
            .limit(1)
        )
        report = report_result.scalar_one_or_none()
    if not report:
        report_result = await db.execute(
            select(AIReport).order_by(AIReport.created_at.desc()).limit(1)
        )
        report = report_result.scalar_one_or_none()
        if report and not incident_id:
            incident_id = report.incident_id
            service = report.service

    steps = []
    if incident_id:
        steps_result = await db.execute(
            select(AgentStep)
            .where(AgentStep.incident_id == incident_id)
            .order_by(AgentStep.step_order.asc())
        )
        steps = [_serialize_step(s) for s in steps_result.scalars().all()]
    elif service:
        steps_result = await db.execute(
            select(AgentStep)
            .where(AgentStep.service == service)
            .order_by(AgentStep.created_at.desc())
            .limit(15)
        )
        steps = sorted(
            [_serialize_step(s) for s in steps_result.scalars().all()],
            key=lambda x: x["step_order"],
        )

    return {
        "incident": {
            "incident_id": incident_id,
            "service": service or (report.service if report else None),
            "created_at": report.created_at.isoformat() if report and report.created_at else None,
        }
        if incident_id or report
        else None,
        "report": _serialize_report(report) if report else None,
        "steps": steps,
        "analyzing": analyzing,
        "analysis_status": active_state.status if active_state else None,
    }


@router.get("/system-status")
async def get_system_status(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SystemState))
    states = result.scalars().all()

    trace_stats = await db.execute(
        select(
            func.count(Trace.id).label("total"),
            func.sum(case((Trace.status == "ok", 1), else_=0)).label("success"),
        )
    )
    stats = trace_stats.one()
    availability = (stats.success / stats.total * 100) if stats.total > 0 else 100.0

    conf_stats = await db.execute(select(func.avg(AIReport.confidence_score)))
    avg_conf = conf_stats.scalar()

    report_count = await db.execute(select(func.count(AIReport.id)))
    count = report_count.scalar() or 0

    return {
        "analysis_states": {s.service: s.status for s in states},
        "incident_ids": {s.service: s.incident_id for s in states if s.incident_id},
        "availability": f"{availability:.2f}%",
        "confidence": f"{(avg_conf or 0) * 100:.1f}%" if count > 0 else "---",
        "report_count": count,
        "gemma_model": "gemma-4-26b-a4b-it",
    }


@router.post("/demo/trigger-spike")
async def trigger_demo_spike():
    """Inject scripted payment-service incident for demos."""
    traces = []
    svc = "payment-service"

    phases = [
        ("ok", random.uniform(850, 1200)),
        ("ok", random.uniform(850, 1200)),
        ("ok", random.uniform(900, 1100)),
        ("error", random.uniform(1500, 2500)),
        ("ok", random.uniform(1600, 2200)),
        ("error", random.uniform(1800, 2400)),
        ("error", 3000.0),
        ("error", 3000.0),
        ("error", 3000.0),
        ("error", 3000.0),
        ("error", 3000.0),
    ]

    from ...database import async_session

    ingested = []
    async with async_session() as db:
        for status, latency in phases:
            trace_id = f"demo-{uuid.uuid4().hex[:6]}"
            t = Trace(
                trace_id=trace_id,
                service=svc,
                operation="checkout_flow",
                duration_ms=int(latency),
                status=status,
                timestamp=datetime.now(timezone.utc),
            )
            db.add(t)
            ingested.append(trace_id)
        await db.commit()

    return {
        "status": "injected",
        "service": svc,
        "trace_count": len(ingested),
        "message": "Incident traces injected. Anomaly detector will pick up within 5s.",
    }


def _serialize_report(r: AIReport) -> dict:
    evidence = []
    tools_used = []
    try:
        evidence = json.loads(r.evidence_json) if r.evidence_json else []
    except json.JSONDecodeError:
        pass
    try:
        tools_used = json.loads(r.tools_used_json) if r.tools_used_json else []
    except json.JSONDecodeError:
        pass

    return {
        "id": r.id,
        "incident_id": r.incident_id,
        "trace_id": r.trace_id,
        "service": r.service,
        "root_cause": r.root_cause,
        "impact_level": r.impact_level,
        "explanation": r.explanation,
        "recommended_action": r.recommended_action,
        "confidence_score": r.confidence_score,
        "evidence": evidence,
        "gemma_model": r.gemma_model,
        "tools_used": tools_used,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


def _serialize_step(s: AgentStep) -> dict:
    tool_input = {}
    tool_output = {}
    try:
        tool_input = json.loads(s.tool_input) if s.tool_input else {}
    except json.JSONDecodeError:
        pass
    try:
        tool_output = json.loads(s.tool_output) if s.tool_output else {}
    except json.JSONDecodeError:
        pass

    return {
        "id": s.id,
        "incident_id": s.incident_id,
        "service": s.service,
        "step_order": s.step_order,
        "tool_name": s.tool_name,
        "tool_input": tool_input,
        "tool_output": tool_output,
        "status": s.status,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }
