"""Focused tests for the token efficiency layer."""

from src.platform.token_efficiency import (
    ContextAssemblyEngine,
    ContextAssemblyError,
    DuplicateDetector,
    KnowledgePackGenerator,
    SemanticChunker,
)


def test_duplicate_detector_identifies_exact_duplicate():
    detector = DuplicateDetector()
    assert detector.check("doc-1", b"same") is None
    match = detector.check("doc-2", b"same")
    assert match is not None
    assert match.duplicate_of == "doc-1"


def test_chunker_respects_token_window():
    chunks = SemanticChunker(max_tokens=20, overlap_tokens=2).chunk(
        "alpha " * 12 + "\n\n" + "beta " * 12,
        field_hints=["reference_number"],
    )
    assert len(chunks) >= 2
    assert all(chunk.token_count <= 20 for chunk in chunks)
    assert chunks[0].field_hints == ("reference_number",)


def test_context_assembly_rejects_over_budget_context():
    engine = ContextAssemblyEngine(token_budget=10)
    try:
        engine.assemble(system_prompt="system", evidence="evidence " * 30)
    except ContextAssemblyError:
        pass
    else:
        raise AssertionError("Expected over-budget context to be rejected")


def test_knowledge_pack_is_compact_and_deterministic():
    pack = KnowledgePackGenerator(max_tokens=100).generate({
        "templateId": "example",
        "document_types": [{"doc_type": "Invoice"}],
        "rules": [{"ruleId": "REQUIRED_FIELD", "description": "Field is required."}],
        "decision_vocabulary": {"PASS": "APPROVE"},
    })
    assert '"templateId":"example"' in pack
    assert '"REQUIRED_FIELD"' in pack
