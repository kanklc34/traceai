import json
import os
import re
import uuid
import httpx
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession

from . import agent_tools

load_dotenv(override=True)

# Model IDs from AI Studio (run: python backend/core/model_tester.py)
# Your account: Gemma 4 26B → gemma-4-26b-a4b-it, Gemma 4 31B → gemma-4-31b-it
PRIMARY_MODEL = "gemma-4-26b-a4b-it"
# 31B may return 500 on some accounts; 26B MoE is reliable
FALLBACK_MODELS: list[str] = []


class GemmaAgent:
    def __init__(self):
        self.api_key = os.getenv("GEMMA_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.models = [PRIMARY_MODEL, *FALLBACK_MODELS]
        self.dev_mock = os.getenv("TRACEAI_DEV_MOCK", "0") == "1"

    async def run_investigation(
        self,
        session: AsyncSession,
        anomaly_event: dict,
        on_step=None,
        incident_id: str | None = None,
    ) -> dict:
        """Execute tool pipeline then Gemma 4 synthesis. Returns RCA + metadata."""
        incident_id = incident_id or f"inc-{uuid.uuid4().hex[:10]}"
        service = anomaly_event["service"]
        trigger = anomaly_event.get("trigger", "unknown")
        tools_used = []
        step_order = 0

        async def record_step(tool_name: str, tool_input: dict, tool_output: dict, status: str = "complete"):
            nonlocal step_order
            step_order += 1
            step = {
                "incident_id": incident_id,
                "service": service,
                "step_order": step_order,
                "tool_name": tool_name,
                "tool_input": tool_input,
                "tool_output": tool_output,
                "status": status,
            }
            if on_step:
                await on_step(step)
            return step

        # --- Tool 1: error breakdown ---
        error_stats = await agent_tools.get_error_breakdown(session, service)
        await record_step("get_error_breakdown", {"service": service}, error_stats)
        tools_used.append("get_error_breakdown")

        # --- Tool 2: recent traces ---
        traces = await agent_tools.get_recent_traces(session, service)
        await record_step("get_recent_traces", {"service": service, "limit": 15}, traces)
        tools_used.append("get_recent_traces")

        # --- Tool 3: deployment ---
        deployment = agent_tools.get_deployment(service)
        await record_step("get_deployment", {"service": service}, deployment)
        tools_used.append("get_deployment")

        # --- Tool 4: baseline comparison ---
        baseline = agent_tools.compare_to_baseline(service, error_stats)
        await record_step("compare_to_baseline", {"service": service}, baseline)
        tools_used.append("compare_to_baseline")

        # --- Tool 5: similar incidents ---
        similar = agent_tools.search_similar_incidents(service, trigger, error_stats)
        await record_step(
            "search_similar_incidents",
            {"service": service, "trigger": trigger},
            similar,
        )
        tools_used.append("search_similar_incidents")

        evidence_bundle = {
            "anomaly_event": anomaly_event,
            "error_breakdown": error_stats,
            "recent_traces": traces,
            "deployment": deployment,
            "baseline_comparison": baseline,
            "similar_incidents": similar,
        }

        await record_step(
            "gemma_synthesize",
            {"model": PRIMARY_MODEL},
            {"status": "calling_gemma_4"},
            status="running",
        )

        rca, model_used = await self._synthesize_rca(evidence_bundle, service, trigger)

        await record_step(
            "gemma_synthesize",
            {"model": model_used},
            {"status": "complete", "root_cause": rca.get("root_cause")},
        )

        rca["incident_id"] = incident_id
        rca["gemma_model"] = model_used
        rca["tools_used"] = tools_used
        rca["evidence"] = self._build_evidence_list(evidence_bundle, similar)
        return rca

    def _build_evidence_list(self, bundle: dict, similar: dict) -> list[str]:
        evidence = []
        eb = bundle["error_breakdown"]
        evidence.append(
            f"Error rate {eb['error_rate']*100:.1f}% over last {eb['window_minutes']}min "
            f"({eb['error_count']}/{eb['total_traces']} traces failed)"
        )
        if eb.get("top_failing_operations"):
            op = eb["top_failing_operations"][0]
            evidence.append(f"Top failing operation: {op['operation']} ({op['error_count']} errors)")

        dep = bundle["deployment"]
        if dep.get("found"):
            evidence.append(f"Recent deploy: {dep['version']} ({dep['deployed_at']})")

        bl = bundle["baseline_comparison"]
        if bl.get("found") and bl.get("latency_multiplier"):
            evidence.append(
                f"Latency {bl['latency_multiplier']}x above baseline "
                f"({bl['current_avg_latency_ms']:.0f}ms vs {bl['baseline_avg_latency_ms']}ms)"
            )

        if similar.get("best_match"):
            evidence.append(f"Matches playbook: {similar['best_match']['title']}")

        return evidence

    async def _synthesize_rca(self, evidence: dict, service: str, trigger: str) -> tuple[dict, str]:
        if not self.api_key or self.api_key in ("YOUR_GEMMA_API_KEY",):
            if self.dev_mock:
                return self._evidence_based_rca(evidence, service, degraded=True), "evidence-only-dev"
            raise RuntimeError(
                "GEMMA_API_KEY not configured. Set GEMMA_API_KEY from Google AI Studio."
            )

        prompt = self._build_synthesis_prompt(evidence, service, trigger)

        for model_name in self.models:
            try:
                result = await self._call_gemma(model_name, prompt)
                if result:
                    result.setdefault("confidence_score", 0.85)
                    return result, model_name
            except Exception as e:
                print(f"[GEMMA] {model_name} failed: {type(e).__name__}: {e}")

        if self.dev_mock:
            return self._evidence_based_rca(evidence, service, degraded=True), "evidence-only-dev"

        return self._evidence_based_rca(evidence, service, degraded=True), "evidence-only"

    async def _call_gemma(self, model_name: str, prompt: str) -> dict | None:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model_name}:generateContent?key={self.api_key}"
        )
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.1,
                        "maxOutputTokens": 1024,
                    },
                },
                timeout=60.0,
            )

        if response.status_code != 200:
            print(f"[GEMMA] HTTP {response.status_code}: {response.text[:300]}")
            return None

        data = response.json()
        candidates = data.get("candidates") or []
        if not candidates:
            print("[GEMMA] No candidates in response")
            return None

        parts = candidates[0].get("content", {}).get("parts") or []
        text = "".join(p.get("text", "") for p in parts).strip()
        if not text:
            print("[GEMMA] Empty text in response")
            return None

        parsed = self._extract_json_object(text)
        if parsed:
            return parsed
        print(f"[GEMMA] JSON parse failed, tail: {text[-300:]}")
        return None

    def _extract_json_object(self, text: str) -> dict | None:
        clean = text.replace("```json", "").replace("```", "").strip()
        for candidate in (clean,):
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass

        # Find last JSON object in response (Gemma may emit reasoning before JSON)
        for match in re.finditer(r"\{[^{}]*\"root_cause\"[^{}]*\}", text, re.DOTALL):
            pass
        matches = list(re.finditer(r'\{\s*"root_cause"\s*:', text))
        for m in reversed(matches):
            start = m.start()
            depth = 0
            for i in range(start, len(text)):
                if text[i] == "{":
                    depth += 1
                elif text[i] == "}":
                    depth -= 1
                    if depth == 0:
                        chunk = text[start : i + 1]
                        try:
                            return json.loads(chunk)
                        except json.JSONDecodeError:
                            break
        return None

    def _build_synthesis_prompt(self, evidence: dict, service: str, trigger: str) -> str:
        return f"""You are TraceAI SRE agent (Gemma 4). Output ONLY one JSON object. No markdown, no bullet lists, no reasoning text.

SERVICE: {service}
TRIGGER: {trigger}
EVIDENCE:
{json.dumps(evidence, default=str)}

JSON schema (use exactly these keys):
{{"root_cause":"string","impact_level":"High|Medium|Low","explanation":"string","recommended_action":"string","confidence_score":0.85}}

Cite error rates and deploy version from evidence. confidence_score is a number 0-1.
"""

    def _evidence_based_rca(self, evidence: dict, service: str, degraded: bool = False) -> dict:
        """Honest fallback synthesized from tool results — not canned per-service text."""
        eb = evidence["error_breakdown"]
        dep = evidence["deployment"]
        similar = evidence["similar_incidents"]
        bl = evidence["baseline_comparison"]

        root_cause = "Telemetry anomaly detected"
        if similar.get("best_match"):
            root_cause = similar["best_match"]["title"]
        elif dep.get("found") and eb["error_rate"] > 0.3:
            root_cause = f"Probable regression from deploy {dep['version']}"

        action = similar["best_match"]["suggested_remediation"] if similar.get("best_match") else (
            f"kubectl rollout undo deployment/{service} -n production"
        )

        explanation_parts = [
            f"{service} shows {eb['error_rate']*100:.1f}% error rate in the last {eb['window_minutes']} minutes.",
        ]
        if dep.get("found"):
            deployed = dep.get("deployed_at", "recently")
            explanation_parts.append(f"Deployment {dep.get('version', 'unknown')} landed {deployed}.")
        if bl.get("found") and bl.get("latency_multiplier"):
            explanation_parts.append(f"Latency is {bl['latency_multiplier']}x baseline.")

        prefix = "[Evidence-only mode — Gemma API unavailable] " if degraded else ""
        return {
            "root_cause": root_cause,
            "impact_level": "High" if eb["error_rate"] > 0.3 else "Medium",
            "explanation": prefix + " ".join(explanation_parts),
            "recommended_action": action,
            "confidence_score": 0.72 if degraded else 0.78,
        }
