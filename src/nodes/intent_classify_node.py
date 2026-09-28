"""CMN-C2-683 — inner workflow step 1: intent_classify.

Deterministic classification of the developer's design-time question into one/more reliability
concerns (schema selection / constrained decoding / validation placement / repair boundary /
tool-call argument reliability / escalation). No LLM required; the production model is reserved for
prose phrasing only.

Skips (no-op) on rejected input — the error_code set by pre_process propagates so kb_retrieve emits
``retrieval_hit_count=0`` and guidance_synthesize returns the out-of-scope safe answer.
"""

from __future__ import annotations

import json
from typing import Any, ClassVar

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel

from src.services.service import ReliabilityKB
from src.utils.audit import emit_trace_event


class IntentClassifyNode(FunctionNode):
    """Classify the reliability question into concerns."""

    required_trust_level: ClassVar[TrustLevel] = TrustLevel.VERIFIED_EXTERNAL

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        scope = json.loads(state.get("validated_input") or state.get("user_input") or "{}")
        question = scope.get("question", "")
        if state.get("error_code") or not question.strip():
            emit_trace_event("intent_classify.skip", {"reason": state.get("error_code") or "empty_question"}, state)
            return {}

        intent = ReliabilityKB.classify(question, scope.get("declared_constraints"))
        intent["constraints"] = {
            "declared_constraints": scope.get("declared_constraints", ""),
            "current_setup": scope.get("current_setup", ""),
        }
        emit_trace_event(
            "intent_classify.complete",
            {"primary_intent": intent["primary_intent"], "concern_count": len(intent["concerns"])},
            state,
        )
        return {"intent": json.dumps(intent, ensure_ascii=False), "status": AgentStatus.SUCCESS.value}
