import asyncio
import json
import uuid
from datetime import datetime, timedelta
from sqlalchemy import select, func, case, delete
from ..database import async_session
from ..models.orm import Trace, AIReport, SystemState, AgentStep
from .gemma_agent import GemmaAgent


class AnomalyManager:
    def __init__(self):
        self.agent = GemmaAgent()
        self.threshold_error_rate = 0.3
        self.window_minutes = 5
        self.alert_suppression = {}

    async def _update_status(self, service: str, status: str, incident_id: str | None = None):
        async with async_session() as session:
            await session.execute(delete(SystemState).where(SystemState.service == service))
            session.add(
                SystemState(service=service, status=status, incident_id=incident_id)
            )
            await session.commit()

    async def _persist_step(self, step: dict):
        async with async_session() as session:
            session.add(
                AgentStep(
                    incident_id=step["incident_id"],
                    service=step["service"],
                    step_order=step["step_order"],
                    tool_name=step["tool_name"],
                    tool_input=json.dumps(step.get("tool_input", {})),
                    tool_output=json.dumps(step.get("tool_output", {})),
                    status=step.get("status", "complete"),
                )
            )
            await session.commit()

    async def start_worker(self, queue: asyncio.Queue):
        print("[SYSTEM] Monitoring database for telemetry anomalies...")
        while True:
            try:
                async with async_session() as session:
                    five_mins_ago = datetime.utcnow() - timedelta(minutes=self.window_minutes)
                    query = (
                        select(
                            Trace.service,
                            func.count(Trace.id).label("total"),
                            func.sum(case((Trace.status == "error", 1), else_=0)).label("errors"),
                            func.avg(Trace.duration_ms).label("avg_latency"),
                        )
                        .where(Trace.timestamp >= five_mins_ago)
                        .group_by(Trace.service)
                    )

                    for row in (await session.execute(query)).all():
                        last_alert = self.alert_suppression.get(row.service)
                        if last_alert and datetime.utcnow() - last_alert < timedelta(minutes=2):
                            continue

                        error_rate = row.errors / row.total if row.total > 0 else 0
                        if error_rate > self.threshold_error_rate or (row.avg_latency or 0) > 800:
                            event = {
                                "service": row.service,
                                "trigger": "error_rate"
                                if error_rate > self.threshold_error_rate
                                else "latency_spike",
                                "value": f"{error_rate:.2%}"
                                if error_rate > self.threshold_error_rate
                                else f"{row.avg_latency:.2f}ms",
                                "timestamp": datetime.utcnow().isoformat(),
                            }
                            queue.put_nowait(event)
                            self.alert_suppression[row.service] = datetime.utcnow()
                            print(f"[INCIDENT] Anomaly on {row.service} -> queued")
            except Exception as e:
                print(f"[ERROR] Detector failed: {e}")

            await asyncio.sleep(5)

    async def start_ai_worker(self, queue: asyncio.Queue):
        print("[SYSTEM] Gemma 4 investigation agent operational.")
        while True:
            event = await queue.get()
            service = event["service"]
            incident_id = f"inc-{uuid.uuid4().hex[:10]}"

            try:
                await self._update_status(
                    service,
                    "Investigating: running agent tools...",
                    incident_id,
                )

                async def on_step(step: dict):
                    await self._persist_step(step)
                    tool = step["tool_name"]
                    await self._update_status(
                        service,
                        f"Agent: {tool}",
                        incident_id,
                    )

                async with async_session() as session:
                    report_data = await self.agent.run_investigation(
                        session,
                        event,
                        on_step=on_step,
                        incident_id=incident_id,
                    )

                    context_query = (
                        select(Trace)
                        .where(Trace.service == service)
                        .order_by(Trace.timestamp.desc())
                        .limit(1)
                    )
                    latest = (await session.execute(context_query)).scalar_one_or_none()
                    trace_id = latest.trace_id if latest else "N/A"

                    new_report = AIReport(
                        incident_id=incident_id,
                        trace_id=trace_id,
                        service=service,
                        root_cause=report_data.get("root_cause", "Anomaly Detected"),
                        impact_level=report_data.get("impact_level", "Medium"),
                        explanation=report_data.get("explanation", ""),
                        recommended_action=report_data.get("recommended_action", ""),
                        confidence_score=report_data.get("confidence_score", 0.8),
                        evidence_json=json.dumps(report_data.get("evidence", [])),
                        gemma_model=report_data.get("gemma_model", "gemma-4-26b-it"),
                        tools_used_json=json.dumps(report_data.get("tools_used", [])),
                        tools_output=json.dumps(
                            {"tools_executed": report_data.get("tools_used", [])}
                        ),
                    )
                    session.add(new_report)
                    await session.execute(
                        delete(SystemState).where(SystemState.service == service)
                    )
                    await session.commit()

                    print(
                        f"[SUCCESS] RCA complete for {service} "
                        f"(incident={incident_id}, model={report_data.get('gemma_model')})"
                    )
            except Exception as e:
                print(f"[ERROR] AI Worker failed: {e}")
                await self._update_status(service, f"Analysis failed: {str(e)[:80]}")
            finally:
                queue.task_done()


anomaly_manager = AnomalyManager()
