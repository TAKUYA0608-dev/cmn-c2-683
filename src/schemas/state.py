"""CMN-C2-683 — Agent state (Structured Output & Constrained Decoding Reliability, Cat 2).

ADR-005: State is a flat TypedDict — never a validation/BaseModel instance. Complex fields are stored
as JSON strings (``NotRequired[str]`` + ``# JSON:``); nodes ``json.dumps`` on write / ``json.loads`` on read.

S-5 / State Safety: **advisory-only, read-only** — the agent never decodes/repairs JSON, never executes a
tool-call, and never mutates a production schema, prompt, or config. It answers design-time reliability
questions with a cited Structured-Output Reliability Plan (DRAFT). Requests are non-executable and
non-confidential; any inadvertently supplied credential is redacted at pre_process (defense-in-depth).

All agent-specific fields are NotRequired (populated progressively; absent at empty-start invoke).
"""

from __future__ import annotations


from framework.schemas.agent_state import AgentState


class State(AgentState):
    """Agent state for the structured-output / constrained-decoding reliability advisory workflow."""

    # ── pre_process (InputValidate, S-1/S-2 validated request) ───────────────
    validated_input: str  # JSON: {question, declared_constraints, current_setup}
    input_format: str  # "json" | "text" | "empty"
    enriched_context: str  # JSON: {source, channel} (read-only caller context)

    # ── inner workflow (intent_classify → kb_retrieve → guidance_synthesize) ──
    intent: str  # JSON: {primary_intent, concerns[], constraints{}}
    retrieved_evidence: str  # JSON: [{topic_id, title, contract_type, source, score, ...}]
    retrieval_hit_count: int  # KB topics retrieved (0 → out-of-scope safe answer)
    reliability_plan: str  # JSON: {contract, validation_placement, failure_handling, ...}
    result: str  # JSON: assembled reliability-plan report

    # ── post_process (S-3 gate + S-4 audit) ──────────────────────────────────
    formatted_output: str  # JSON: final response envelope (plan + advisory disclaimer)
    disclaimer: str  # mandatory advisory / DRAFT disclaimer (read-only, human review)
    audit_logged: bool  # True once the terminal audit event is emitted

    # ── degraded-path signalling (SUCCESS + error_code, never status=ERROR) ──
    error_code: str  # INJECTION_REJECTED | INPUT_REJECTED | INPUT_TOO_LONG | NO_EVIDENCE
    error_message: str  # operator-facing detail
