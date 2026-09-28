"""CMN-C2-683 — inner domain workflow graph (Cat 2).

Instantiated by ReliabilityAdvisoryWorkflowGraphNode.get_subgraph() in graph.py. Linear topology with
per-node skip guards (the portable Cat 2 form; conditional edges don't propagate across the subgraph
boundary):

    START → intent_classify → kb_retrieve → guidance_synthesize → END

On rejected / 0-hit input, intent_classify no-ops, kb_retrieve sets retrieval_hit_count=0 (+error_code),
and guidance_synthesize emits the out-of-scope safe answer — no fabricated, ungrounded guidance.
"""

from __future__ import annotations
from typing import Any

from langgraph.graph import END, START

from framework.graph.base_graph import BaseGraph
from framework.schemas.agent_state import AgentState

from src.nodes.guidance_synthesize_node import GuidanceSynthesizeNode
from src.nodes.intent_classify_node import IntentClassifyNode
from src.nodes.kb_retrieve_node import KbRetrieveNode
from src.schemas.state import State


class ReliabilityAdvisoryWorkflow(BaseGraph):
    """Inner graph: intent_classify → kb_retrieve → guidance_synthesize."""

    @property
    def name(self) -> str:
        return "ReliabilityAdvisoryWorkflow"

    @property
    def state_schema(self) -> type:
        return State

    def _validate_config(self) -> None:
        pass

    def register_nodes(self) -> None:
        # No super() — BaseGraph.register_nodes() is abstract.
        self._nodes["intent_classify"] = IntentClassifyNode()
        self._nodes["kb_retrieve"] = KbRetrieveNode()
        self._nodes["guidance_synthesize"] = GuidanceSynthesizeNode()

    def add_edges(self) -> None:
        # Static linear backbone; the 0-hit / rejected skip is handled by per-node guards.
        self._sg.add_edge(START, "intent_classify")
        self._sg.add_edge("intent_classify", "kb_retrieve")
        self._sg.add_edge("kb_retrieve", "guidance_synthesize")
        self._sg.add_edge("guidance_synthesize", END)

    def route(self, state: AgentState) -> str:
        """Required by the BaseGraph ABC. Linear topology → not wired to a conditional edge."""
        if state.get("error_code") or state.get("retrieval_hit_count", 0) == 0:
            return "guidance_synthesize"
        return "kb_retrieve"

    def get_output(self, state: AgentState) -> dict[str, Any]:
        return {
            "output": state.get("result"),
            "status": state.get("status"),
            "retrieval_hit_count": state.get("retrieval_hit_count", 0),
            "error_code": state.get("error_code"),
            "trace_id": state.get("trace_id"),
            "correlation_id": state.get("correlation_id"),
            "node_history": state.get("node_history", []),
        }
