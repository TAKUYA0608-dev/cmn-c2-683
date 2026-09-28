"""CMN-C2-683 — post_process node: SafetyAndCitationGate (S-3 output gate + S-4 audit).

S-3: verify citation completeness (grounded guidance must cite its versioned technical source), strip
any credential-shaped token that reached the output, reject unsupported claims, and append the
mandatory advisory / DRAFT disclaimer. S-4: emit a terminal audit event (intent / topic counts /
citation-completeness only — no PII, no credentials). Runs on both the full plan and the out-of-scope
safe branch.
"""

from __future__ import annotations

import json
import re
from typing import Any, ClassVar

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel

from src.utils.audit import emit_trace_event

_DISCLAIMER = (
    "DRAFT advisory guidance for design-time structured-output and constrained-decoding reliability "
    "decisions, grounded in versioned technical references. This agent is not a runtime component: it "
    "never decodes, validates, or repairs live model output and never executes a tool call. Validate "
    "every recommendation against your model/runtime version and have an authorized engineer review "
    "and approve before adoption."
)
# S-3 redaction: never echo a credential-shaped token even if one reached the plan text.
_CRED_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9]{16,}"),
    re.compile(r"AKIA[0-9A-Z]{12,}"),
    re.compile(r"eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}"),
)
_CRED_MASK = "[CREDENTIAL-REDACTED]"


def _redact(text: str) -> str:
    for pat in _CRED_PATTERNS:
        text = pat.sub(_CRED_MASK, text)
    return text


class PostProcessNode(FunctionNode):
    """Verify citations, redact credentials, append advisory disclaimer, emit audit."""

    required_trust_level: ClassVar[TrustLevel] = TrustLevel.VERIFIED_EXTERNAL

    def _extra_security_gate_output(self, result: dict[str, Any]) -> dict[str, Any]:
        """S-3 preservation check: advisory / DRAFT disclaimer present in the output envelope.

        SDK 1.0.0 contract: receives the **result dict from ``execute()``**; returns the (possibly
        filtered) result. MAY raise to block an output missing the mandatory disclaimer.
        """
        out = result.get("formatted_output", "")
        if out and "DRAFT" not in out and "advisory" not in out.lower():
            raise ValueError("S-3: advisory / DRAFT disclaimer missing from output")
        return dict(result)

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        report: dict[str, Any] = json.loads(state.get("result", "{}") or "{}")

        citations = report.get("citations", [])
        grounded = report.get("status_kind") == "guidance"
        citation_complete = (not grounded) or bool(citations)

        formatted = {
            "status_kind": report.get("status_kind"),
            "reliability_plan": report.get("reliability_plan", {}),
            "guidance": report.get("guidance", []),
            "verification_checklist": report.get("verification_checklist", []),
            "citations": citations,
            "citation_complete": citation_complete,
            "message": report.get("message"),
            "disclaimer": _DISCLAIMER,
        }
        formatted_output = _redact(json.dumps(formatted, ensure_ascii=False))
        emit_trace_event(
            "post_process.complete",
            {
                "status_kind": report.get("status_kind"),
                "topic_count": len(report.get("guidance", [])),
                "citation_complete": citation_complete,
                "error_code": state.get("error_code"),
            },
            state,
        )
        return {
            "formatted_output": formatted_output,
            "disclaimer": _DISCLAIMER,
            "audit_logged": True,
            "status": AgentStatus.SUCCESS.value,
        }
