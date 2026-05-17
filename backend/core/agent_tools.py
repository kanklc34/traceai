import json
from datetime import datetime, timedelta
from pathlib import Path
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.orm import Trace

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _load_json(name: str) -> dict | list:
    path = DATA_DIR / name
    with open(path, encoding="utf-8") as f:
        return json.load(f)


async def get_error_breakdown(session: AsyncSession, service: str, window_minutes: int = 5) -> dict:
    since = datetime.utcnow() - timedelta(minutes=window_minutes)
    query = select(
        func.count(Trace.id).label("total"),
        func.sum(case((Trace.status == "error", 1), else_=0)).label("errors"),
        func.avg(Trace.duration_ms).label("avg_latency"),
        func.max(Trace.duration_ms).label("max_latency"),
    ).where(Trace.service == service, Trace.timestamp >= since)
    row = (await session.execute(query)).one()
    total = row.total or 0
    errors = row.errors or 0
    error_rate = errors / total if total > 0 else 0.0

    ops_query = (
        select(Trace.operation, func.count(Trace.id).label("cnt"))
        .where(Trace.service == service, Trace.timestamp >= since, Trace.status == "error")
        .group_by(Trace.operation)
        .order_by(func.count(Trace.id).desc())
        .limit(3)
    )
    top_ops = [
        {"operation": r.operation, "error_count": r.cnt}
        for r in (await session.execute(ops_query)).all()
    ]

    return {
        "service": service,
        "window_minutes": window_minutes,
        "total_traces": total,
        "error_count": int(errors),
        "error_rate": round(error_rate, 4),
        "avg_latency_ms": round(float(row.avg_latency or 0), 2),
        "max_latency_ms": int(row.max_latency or 0),
        "top_failing_operations": top_ops,
    }


async def get_recent_traces(session: AsyncSession, service: str, limit: int = 15) -> dict:
    query = (
        select(Trace)
        .where(Trace.service == service)
        .order_by(Trace.timestamp.desc())
        .limit(limit)
    )
    traces = (await session.execute(query)).scalars().all()
    return {
        "service": service,
        "count": len(traces),
        "traces": [
            {
                "trace_id": t.trace_id,
                "operation": t.operation,
                "duration_ms": t.duration_ms,
                "status": t.status,
                "timestamp": t.timestamp.isoformat() if t.timestamp else None,
            }
            for t in traces
        ],
    }


def get_deployment(service: str) -> dict:
    deployments = _load_json("deployments.json")
    info = deployments.get(service)
    if not info:
        return {"service": service, "found": False, "message": "No recent deployment on record"}
    return {"service": service, "found": True, **info}


def compare_to_baseline(service: str, current_stats: dict) -> dict:
    baselines = _load_json("baselines.json")
    baseline = baselines.get(service, {})
    if not baseline:
        return {"service": service, "found": False}

    current_error = current_stats.get("error_rate", 0)
    current_latency = current_stats.get("avg_latency_ms", 0)
    return {
        "service": service,
        "found": True,
        "baseline_error_rate": baseline.get("error_rate"),
        "current_error_rate": current_error,
        "error_rate_multiplier": round(current_error / baseline["error_rate"], 2)
        if baseline.get("error_rate")
        else None,
        "baseline_avg_latency_ms": baseline.get("avg_latency_ms"),
        "current_avg_latency_ms": current_latency,
        "latency_multiplier": round(current_latency / baseline["avg_latency_ms"], 2)
        if baseline.get("avg_latency_ms")
        else None,
        "primary_operation": baseline.get("primary_operation"),
        "anomaly_detected": current_error > baseline.get("error_rate", 1) * 3
        or current_latency > baseline.get("avg_latency_ms", 99999) * 2,
    }


def search_similar_incidents(service: str, trigger: str, error_breakdown: dict) -> dict:
    playbooks = _load_json("playbooks.json")
    symptoms = [service, trigger.replace("_", " ")]
    if error_breakdown.get("top_failing_operations"):
        symptoms.append(error_breakdown["top_failing_operations"][0]["operation"])

    scored = []
    for pb in playbooks:
        overlap = len(set(symptoms) & set(pb.get("symptoms", [])))
        if overlap > 0 or service in pb.get("symptoms", []):
            scored.append((overlap, pb))

    scored.sort(key=lambda x: x[0], reverse=True)
    if not scored:
        return {"matches": [], "best_match": None}

    best = scored[0][1]
    return {
        "matches": [s[1]["id"] for s in scored[:3]],
        "best_match": {
            "id": best["id"],
            "title": best["title"],
            "pattern": best["pattern"],
            "suggested_remediation": best["remediation"],
        },
    }


TOOL_DEFINITIONS = [
    {
        "name": "get_error_breakdown",
        "description": "Get error rate, latency, and top failing operations for a service in a time window.",
        "parameters": {
            "type": "object",
            "properties": {
                "service": {"type": "string"},
                "window_minutes": {"type": "integer"},
            },
            "required": ["service"],
        },
    },
    {
        "name": "get_recent_traces",
        "description": "Fetch recent distributed traces for a service.",
        "parameters": {
            "type": "object",
            "properties": {
                "service": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["service"],
        },
    },
    {
        "name": "get_deployment",
        "description": "Look up the most recent deployment for a service from the deployment registry.",
        "parameters": {
            "type": "object",
            "properties": {"service": {"type": "string"}},
            "required": ["service"],
        },
    },
    {
        "name": "compare_to_baseline",
        "description": "Compare current telemetry against historical baseline for the service.",
        "parameters": {
            "type": "object",
            "properties": {"service": {"type": "string"}},
            "required": ["service"],
        },
    },
    {
        "name": "search_similar_incidents",
        "description": "Search incident playbooks for similar past patterns.",
        "parameters": {
            "type": "object",
            "properties": {
                "service": {"type": "string"},
                "trigger": {"type": "string"},
            },
            "required": ["service", "trigger"],
        },
    },
]
