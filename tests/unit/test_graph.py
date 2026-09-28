# CMN-C2-683 — Unit Tests: Cat 2 graph wiring (outer GraphNode + inner workflow)

import pytest

from src.graph.domain_workflow_graph import ReliabilityAdvisoryWorkflow
from src.graph.graph import (
    Graph,
    ReliabilityAdvisoryWorkflowGraphNode,
    StructuredOutputConstrainedDecodingReliabilityAgent,
)
from src.schemas.state import State


class TestOuterGraph:
    def test_registry_alias(self):
        assert StructuredOutputConstrainedDecodingReliabilityAgent is Graph

    def test_name_and_state_schema(self):
        g = Graph()
        assert g.name == "StructuredOutputConstrainedDecodingReliabilityAgent"
        assert g.state_schema is State

    def test_main_slot_is_graphnode(self):
        g = Graph()
        g.register_nodes()
        assert isinstance(g._nodes["main"], ReliabilityAdvisoryWorkflowGraphNode)
        for slot in ("pre_process", "main", "post_process"):
            assert slot in g._nodes

    def test_error_strategy_propagate(self):
        assert ReliabilityAdvisoryWorkflowGraphNode.error_strategy == "propagate"
        assert ReliabilityAdvisoryWorkflowGraphNode.propagate_hitl is False

    def test_get_subgraph_is_cached(self):
        node = ReliabilityAdvisoryWorkflowGraphNode()
        assert node.get_subgraph() is node.get_subgraph()

    def test_extract_input_prefers_validated(self):
        node = ReliabilityAdvisoryWorkflowGraphNode()
        assert node.extract_input({"validated_input": "V", "user_input": "U"}) == "V"

    def test_merge_output_maps_fields(self):
        node = ReliabilityAdvisoryWorkflowGraphNode()
        merged = node.merge_output(
            {}, {"output": '{"x":1}', "retrieval_hit_count": 2, "status": "success", "error_code": None})
        assert merged["result"] == '{"x":1}' and merged["retrieval_hit_count"] == 2


class TestInnerWorkflow:
    def test_inner_registers_three_nodes(self):
        wf = ReliabilityAdvisoryWorkflow(config={})
        wf.register_nodes()
        for slot in ("intent_classify", "kb_retrieve", "guidance_synthesize"):
            assert slot in wf._nodes

    def test_name_and_state_schema(self):
        wf = ReliabilityAdvisoryWorkflow(config={})
        assert wf.name == "ReliabilityAdvisoryWorkflow"
        assert wf.state_schema is State

    def test_route_zero_hit_to_synthesize(self):
        wf = ReliabilityAdvisoryWorkflow(config={})
        assert wf.route({"retrieval_hit_count": 0}) == "guidance_synthesize"

    def test_route_with_hits_to_retrieve(self):
        wf = ReliabilityAdvisoryWorkflow(config={})
        assert wf.route({"retrieval_hit_count": 3}) == "kb_retrieve"

    def test_get_output_surfaces_result(self):
        wf = ReliabilityAdvisoryWorkflow(config={})
        out = wf.get_output({"result": "R", "status": "success", "retrieval_hit_count": 1})
        assert out["output"] == "R" and out["retrieval_hit_count"] == 1


class TestServerModule:
    def test_server_imports(self):
        try:
            import src.api.server as server
        except ModuleNotFoundError as exc:
            pytest.skip(f"platform module unavailable in the local stub env: {exc}")
        assert server.app is not None and server.agent is not None
