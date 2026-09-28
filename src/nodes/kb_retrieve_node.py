"""CMN-C2-683 — inner workflow step 2: kb_retrieve (VersionedKBRetrieve).

Deterministic retrieval over the **versioned** structured-output / constrained-decoding technical KB,
scored by the classified concerns + question keywords. Sets ``retrieval_hit_count``; **0 hits (rejected
input or no match) routes to the out-of-scope safe answer** — the agent never fabricates ungrounded
reliability guidance.
"""

from __future__ import annotations

import json
from typing import Any, ClassVar

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel

from src.services.service import ReliabilityKB
from src.utils.audit import emit_trace_event


class KbRetrieveNode(FunctionNode):
    """Retrieve grounded, versioned reliability guidance for the classified question."""

    required_trust_level: ClassVar[TrustLevel] = TrustLevel.VERIFIED_EXTERNAL

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        if state.get("error_code") or not state.get("intent"):
            emit_trace_event("kb_retrieve.skip", {"reason": state.get("error_code") or "no_intent"}, state)
            return {
                "retrieved_evidence": "[]",
                "retrieval_hit_count": 0,
                "error_code": state.get("error_code") or "NO_EVIDENCE",
                "status": AgentStatus.SUCCESS.value,
            }

        intent = json.loads(state.get("intent") or "{}")
        scope = json.loads(state.get("validated_input") or "{}")
        query = " ".join(
            str(x)
            for x in (scope.get("question", ""), scope.get("declared_constraints", ""), scope.get("current_setup", ""))
        )
        evidence = ReliabilityKB.retrieve(query, intent.get("concerns", []))
        emit_trace_event("kb_retrieve.complete", {"hit_count": len(evidence)}, state)
        out = {
            "retrieved_evidence": json.dumps(evidence, ensure_ascii=False),
            "retrieval_hit_count": len(evidence),
            "status": AgentStatus.SUCCESS.value,
        }
        if not evidence:
            out["error_code"] = "NO_EVIDENCE"
        return out
