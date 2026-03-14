"""Tests for pipeline.extract module."""
import json
from unittest.mock import MagicMock, patch

import pytest

MOCK_RESPONSE_JSON = {
    "summary": "An AI tool that summarizes loan documents to save processing time.",
    "arch_pattern": "Inference",
    "business_value_score": 7,
    "feasibility_score": 5,
}

SAMPLE_FIELDS = {
    "title": "Automated loan document summarizer",
    "problem": "Loan officers spend 2 hours reading docs.",
    "hypothesis": "AI can summarize in 30 seconds.",
    "business_value": "Save 1.5 hours across 500 daily apps.",
    "strategic_area": "Credit",
    "arch_pattern": "Inference",
    "tech_components": ["pdf-extraction", "claude-api"],
}


def _make_mock_response():
    """Build a mock Anthropic messages.create response."""
    content_block = MagicMock()
    content_block.text = json.dumps(MOCK_RESPONSE_JSON)
    response = MagicMock()
    response.content = [content_block]
    return response


@patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
@patch("pipeline.extract.anthropic")
def test_extract_returns_enriched_fields(mock_anthropic):
    """Mock Claude response, verify summary, arch_pattern, scores are correctly extracted."""
    mock_client = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client
    mock_client.messages.create.return_value = _make_mock_response()

    from pipeline.extract import extract_idea

    result = extract_idea(SAMPLE_FIELDS, None)

    assert result["summary"] == MOCK_RESPONSE_JSON["summary"]
    assert result["arch_pattern"] == "Inference"
    assert result["scores"]["business_value"] == 7
    assert result["scores"]["feasibility"] == 5

    mock_anthropic.Anthropic.assert_called_once_with(api_key="test-key")
    mock_client.messages.create.assert_called_once()


@patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
@patch("pipeline.extract.anthropic")
def test_extract_with_transcript(mock_anthropic):
    """Verify transcript is included in the user message sent to Claude."""
    mock_client = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client
    mock_client.messages.create.return_value = _make_mock_response()

    from pipeline.extract import extract_idea

    transcript = "This idea will revolutionize loan processing."
    extract_idea(SAMPLE_FIELDS, transcript)

    call_kwargs = mock_client.messages.create.call_args
    user_message = call_kwargs.kwargs["messages"][0]["content"]
    assert "Pitch transcript:" in user_message
    assert transcript in user_message
