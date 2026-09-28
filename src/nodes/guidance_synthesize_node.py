"""CMN-C2-683 — inner workflow step 3: guidance_synthesize (GuidanceSynthesize).

Composes a multi-part **Structured-Output Reliability Plan** (contract selection + validation placement
+ failure/repair handling + tool-call reliability + escalation) **conditioned on the retrieved
evidence** — not a static ``(strictness, model)`` lookup table — with per-topic source citations and a
consolidated verification checklist. On the 0-hit / rejected branch it emits the out-of-scope safe
answer (``citations=[]``). Advisory-only: the plan is a DRAFT recommendation for human adoption.
"""

from __future__ import annotations

import json
from typing import Any, ClassVar

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel

from src.utils.audit import emit_trace_event

_OUT_OF_SCOPE = (
    "No versioned guidance for this question was found in the structured-output / constrained-decoding "
    "reliability KB (JSON Schema, grammar-constrained decoding, function-calling reliability, validation "
    "placement, repair boundary, escalation). Please restate the technical decision (e.g. schema "
    "strictness, where to validate, tool-argument reliability) or consult your platform's structured-"
    "output reference."
)

# Which reliability-plan section each concern feeds.
_PLAN_SECTION = {
    "schema_selection": "contract",
    "constrained_decoding": "contract",
    "validation_placement": "validation_placement",
    "failure_handling": "failure_handling",
    "tool_call_reliability": "tool_call_reliability",
    "escalation": "escalation",
}
_PLAN_SECTIONS = ("contract", "validation_placement", "failure_handling", "tool_call_reliability", "escalation")


class GuidanceSynthesizeNode(FunctionNode):
    """Compose the Structured-Output Reliability Plan with citations (or safe answer on 0-hit)."""

    required_trust_level: ClassVar[TrustLevel] = TrustLevel.VERIFIED_EXTERNAL

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        evidence = json.loads(state.get("retrieved_evidence") or "[]")
        if state.get("error_code") or not evidence:
            emit_trace_event("guidance_synthesize.safe", {"reason": state.get("error_code") or "no_evidence"}, state)
            report: dict[str, Any] = {
                "status_kind": "out_of_scope",
                "message": _OUT_OF_SCOPE,
                "reliability_plan": {},
                "guidance": [],
                "verification_checklist": [],
                "citations": [],
            }
            return {"result": json.dumps(report, ensure_ascii=False), "status": AgentStatus.SUCCESS.value}

        plan: dict[str, list[dict[str, Any]]] = {s: [] for s in _PLAN_SECTIONS}
        guidance: list[dict[str, Any]] = []
        checklist: list[dict[str, Any]] = []
        citations: list[dict[str, str]] = []
        for e in evidence:
            citation = f"{e['source']} (v{e['version']})"
            section = _PLAN_SECTION.get(e["concern"], "contract")
            plan[section].append(
                {
                    "topic_id": e["topic_id"],
                    "title": e["title"],
                    "contract_type": e["contract_type"],
                    "recommendation": e["recommendation"],
                    "citation": citation,
                }
            )
            guidance.append(
                {
                    "topic_id": e["topic_id"],
                    "title": e["title"],
                    "concern": e["concern"],
                    "contract_type": e["contract_type"],
                    "recommendation": e["recommendation"],
                    "citation": citation,
                }
            )
            for chk in e["verification_checks"]:
                checklist.append({"topic_id": e["topic_id"], "check": chk})
            citations.append({"topic_id": e["topic_id"], "source": e["source"], "version": e["version"]})

        plan = {k: v for k, v in plan.items() if v}
        report = {
            "status_kind": "guidance",
            "reliability_plan": plan,
            "guidance": guidance,
            "verification_checklist": checklist,
            "citations": citations,
        }
        emit_trace_event(
            "guidance_synthesize.complete",
            {"topic_count": len(guidance), "citation_count": len(citations), "checklist_count": len(checklist)},
            state,
        )
        return {
            "result": json.dumps(report, ensure_ascii=False),
            "reliability_plan": json.dumps(plan, ensure_ascii=False),
            "status": AgentStatus.SUCCESS.value,
        }
