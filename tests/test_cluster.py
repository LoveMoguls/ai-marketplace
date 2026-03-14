"""Tests for pipeline.cluster module."""

from pipeline.cluster import detect_enablers


def _make_ideas(n):
    ideas = []
    for i in range(n):
        ideas.append({
            "id": f"test-{i:03d}",
            "summary": f"Idea {i} about document processing and AI",
            "tech_components": ["pdf-extraction", "claude-api"] if i % 2 == 0 else ["data-pipeline"],
            "enabler_candidate": False,
        })
    return ideas


class TestDetectEnablers:
    """Tests for detect_enablers function."""

    def test_detect_enablers_marks_shared_components(self) -> None:
        """4 ideas where components appear in >= 2 ideas get enabler_candidate = True."""
        ideas = _make_ideas(4)
        # ideas 0, 2 share pdf-extraction and claude-api (each appears 2x)
        # idea 1, 3 share data-pipeline (appears 2x)
        result = detect_enablers(ideas)
        for idea in result:
            assert idea["enabler_candidate"] is True

    def test_detect_enablers_single_component_not_marked(self) -> None:
        """2 ideas with unique components stay enabler_candidate = False."""
        ideas = [
            {
                "id": "test-000",
                "summary": "Idea about X",
                "tech_components": ["unique-component-a"],
                "enabler_candidate": False,
            },
            {
                "id": "test-001",
                "summary": "Idea about Y",
                "tech_components": ["unique-component-b"],
                "enabler_candidate": False,
            },
        ]
        result = detect_enablers(ideas)
        for idea in result:
            assert idea["enabler_candidate"] is False
