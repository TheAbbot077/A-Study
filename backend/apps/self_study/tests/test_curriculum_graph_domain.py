from apps.self_study.domain.curriculum_graph import CurriculumGraphSpecification, graph_fingerprint, stable_edge_key, stable_node_key


def test_stable_identity_normalizes_unicode_whitespace_and_symmetric_edges():
    first = stable_node_key(source_version_id="v1", authority_namespace="  KNEC ", external_identifier="MATH-1",
                            node_type="CONCEPT", structural_path="Root / Algebra", title="Linear   equations")
    second = stable_node_key(source_version_id="v1", authority_namespace="knec", external_identifier="math-1",
                             node_type="CONCEPT", structural_path="root / algebra", title="linear equations")
    assert first == second
    assert stable_edge_key(edge_type="EQUIVALENT_TO", source_key="a", target_key="b", requirement="") == stable_edge_key(
        edge_type="EQUIVALENT_TO", source_key="b", target_key="a", requirement="")


def test_specification_rejects_uncited_nodes_and_sources_outside_selection():
    payload = {"construction_method": "STRUCTURED_IMPORT", "producer": "registry-importer", "nodes": [{
        "local_key": "root", "node_type": "CURRICULUM_ROOT", "title": "Mathematics", "ordinal": 1,
        "source_curriculum_version_id": "other", "authority_namespace": "authority", "structural_path": "root"
    }], "edges": [], "citations": []}
    specification = CurriculumGraphSpecification.from_payload(payload)
    try:
        specification.validate_shape({"selected"})
    except ValueError as error:
        assert "outside the authoritative selection" in str(error)
    else:
        raise AssertionError("unselected source was accepted")


def test_graph_fingerprint_is_order_independent_but_content_sensitive():
    nodes = [{"stable_key": "b"}, {"stable_key": "a"}]
    arguments = dict(source_selection_fingerprint="selection", component_version_ids=["v2", "v1"],
                     edges=[], citations=[], construction_method="STRUCTURED_IMPORT")
    first = graph_fingerprint(nodes=nodes, **arguments)
    second = graph_fingerprint(nodes=list(reversed(nodes)), **arguments)
    changed = graph_fingerprint(nodes=[{"stable_key": "c"}], **arguments)
    assert first == second
    assert first != changed
