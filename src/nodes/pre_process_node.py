"""CMN-C2-683 — pre_process node: InputValidate (S-1 validation + S-2 gate + slot extraction).

Accepts a structured JSON request or NL text describing a **design-time** structured-output /
constrained-decoding reliability question, normalizes it (NFKC), enforces S-1/S-2 (size cap +
prompt-injection markers + non-executable/non-confidential request), and extracts
``{question, declared_constraints, current_setup}``.

Advisory-only / read-only: the agent never decodes/repairs JSON and never executes a tool call. Any
inadvertently supplied credential is redacted before the request is persisted to ``validated_input``
(defense-in-depth).

All rejects (prompt-injection / empty / oversize) return ``status=SUCCESS + error_code`` (degraded —
the untrusted content is never processed: ``validated_input="{}"`` so the inner workflow reaches the
out-of-scope safe answer and post_process S-3/S-4 always run). Injection / oversize are NOT
``status=ERROR`` hard rejects: an ERROR short-circuits ``__call__`` so the framework ``route()`` sends
it straight to ``finalize`` and main / post_process (disclaimer / redaction / audit) never run.
"""

from __future__ import annotations

import json
import re
import unicodedata
from typing import Any, ClassVar

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel

from src.utils.audit import emit_trace_event

_MAX_INPUT = 20_000
_INJECTION_MARKERS = (
    "ignore previous",
    "ignore all previous",
    "disregard the above",
    "system prompt",
    "you are now",
    "###system",
    "<|im_start|>",
)
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
# Defense-in-depth: redact anything that looks like a secret a developer may paste into a
# reliability question (API keys / bearer tokens), before it is persisted to State.
_CRED_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9]{16,}"),
    re.compile(r"AKIA[0-9A-Z]{12,}"),
    re.compile(r"eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}"),  # JWT
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]{16,}"),
)
_CRED_MASK = "[CREDENTIAL-REDACTED]"


def _nfkc(text: str) -> str:
    return unicodedata.normalize("NFKC", text or "")


def _sanitize(text: str) -> str:
    """Strip control chars (S-2) and redact credential-shaped tokens (defense-in-depth)."""
    clean = _CONTROL.sub("", text or "")
    for pat in _CRED_PATTERNS:
        clean = pat.sub(_CRED_MASK, clean)
    return clean


class PreProcessNode(FunctionNode):
    """Validate the request and extract the reliability-question slots."""

    required_trust_level: ClassVar[TrustLevel] = TrustLevel.VERIFIED_EXTERNAL

    def _extra_security_gate_input(self, state: dict[str, Any]) -> dict[str, Any]:
        """S-2 domain hook — no hard reject.

        SDK 1.0.0 contract: MUST NOT raise. Prompt-injection / oversize are handled as a degraded
        ``status=SUCCESS + error_code`` path in ``execute()`` (the untrusted content is never
        processed) so main / post_process S-3/S-4 always run. A ``status=ERROR`` here would
        short-circuit ``__call__`` and skip main / post_process. The framework
        default S-2 PII masking still applies. Returns state unchanged.
        """
        return dict(state)

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        raw = state.get("user_input", "") or ""
        input_context = state.get("input_context", {})  # read-only [C1]
        enriched = json.dumps(
            {
                "source": "StructuredOutputConstrainedDecodingReliabilityAgent",
                "channel": input_context.get("channel", "unknown"),
            },
            ensure_ascii=False,
        )
        normalized = _nfkc(raw).strip()

        # Prompt-injection -> degraded SUCCESS + error_code (never processed). NOT status=ERROR: ERROR
        # short-circuits __call__ so main / post_process (disclaimer / redaction / audit) would be
        # skipped. The untrusted body is discarded (validated_input="{}"); the inner
        # workflow reaches the out-of-scope safe answer.
        if any(marker in normalized.lower() for marker in _INJECTION_MARKERS):
            emit_trace_event("input_validate.rejected", {"reason": "prompt_injection"}, state)
            return {
                "validated_input": "{}",
                "input_format": "rejected",
                "enriched_context": enriched,
                "error_code": "INJECTION_REJECTED",
                "error_message": "prompt-injection marker detected; input not processed",
                "status": AgentStatus.SUCCESS.value,
            }

        if not raw.strip():
            emit_trace_event("input_validate.rejected", {"reason": "empty_input"}, state)
            return {
                "validated_input": "{}",
                "input_format": "empty",
                "enriched_context": enriched,
                "error_code": "INPUT_REJECTED",
                "error_message": "no reliability question submitted",
                "status": AgentStatus.SUCCESS.value,
            }

        if len(normalized) > _MAX_INPUT:
            emit_trace_event("input_validate.rejected", {"reason": "oversize"}, state)
            return {
                "validated_input": "{}",
                "input_format": "oversize",
                "enriched_context": enriched,
                "error_code": "INPUT_TOO_LONG",
                "error_message": f"input exceeds size cap ({_MAX_INPUT} chars)",
                "status": AgentStatus.SUCCESS.value,
            }

        scope, fmt = self._parse(normalized)
        emit_trace_event("input_validate.validated", {"input_format": fmt}, state)
        return {
            "validated_input": json.dumps(scope, ensure_ascii=False),
            "input_format": fmt,
            "enriched_context": enriched,
            "status": AgentStatus.SUCCESS.value,
        }

    def _parse(self, text: str) -> tuple[dict[str, Any], str]:
        try:
            obj = json.loads(text)
            if isinstance(obj, dict):
                question = str(obj.get("question") or obj.get("query") or "")
                constraints = obj.get("declared_constraints") or obj.get("constraints") or ""
                setup = obj.get("current_setup") or obj.get("setup") or ""
                return {
                    "question": _sanitize(question),
                    "declared_constraints": _sanitize(str(constraints)),
                    "current_setup": _sanitize(str(setup)),
                }, "json"
        except (ValueError, TypeError):
            pass
        clean = _sanitize(text)
        return {"question": clean, "declared_constraints": "", "current_setup": ""}, "text"
