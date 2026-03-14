"""Tests for pipeline.parse_issue module."""

import pytest

from pipeline.parse_issue import parse_issue_body


FULL_BODY = """\
### Idea title

Automated loan document summarizer

### Problem statement

Banks process thousands of loan documents daily.
Manual review is slow and error-prone.
We need an automated solution.

### Hypothesis

Using LLMs we can extract key fields from loan docs
with 95%+ accuracy, reducing review time by 80%.

### Business value

Saves 200 FTE-hours per month.
Reduces error rate from 5% to <1%.
Enables faster loan decisions.

### Strategic area

Credit

### Architectural pattern

Inference

### Current status

In development

### Contact name

Anna Svensson

### Contact email

anna.svensson@seb.se

### Business stakeholder

WAM / CIB

### Tech components

pdf-extraction, claude-api, structured-output

### Source

hackathon-010

### Pitch video URL

https://example.com/pitch.mp4

### Repository URL

_No response_

### Documentation URL

_No response_
"""

PARTIAL_BODY = """\
### Idea title

Quick credit check

### Problem statement

Need faster credit checks.

### Strategic area

Credit
"""


class TestBasicFieldExtraction:
    """Test basic field extraction from a complete Issue body."""

    def test_title(self) -> None:
        result = parse_issue_body(FULL_BODY)
        assert result["title"] == "Automated loan document summarizer"

    def test_strategic_area(self) -> None:
        result = parse_issue_body(FULL_BODY)
        assert result["strategic_area"] == "Credit"

    def test_arch_pattern(self) -> None:
        result = parse_issue_body(FULL_BODY)
        assert result["arch_pattern"] == "Inference"

    def test_status(self) -> None:
        result = parse_issue_body(FULL_BODY)
        assert result["status"] == "In development"

    def test_contact_name(self) -> None:
        result = parse_issue_body(FULL_BODY)
        assert result["contact_name"] == "Anna Svensson"

    def test_contact_email(self) -> None:
        result = parse_issue_body(FULL_BODY)
        assert result["contact_email"] == "anna.svensson@seb.se"

    def test_business_stakeholder(self) -> None:
        result = parse_issue_body(FULL_BODY)
        assert result["business_stakeholder"] == "WAM / CIB"

    def test_source(self) -> None:
        result = parse_issue_body(FULL_BODY)
        assert result["source"] == "hackathon-010"


class TestMultilineFields:
    """Test multiline field content for problem, hypothesis, business_value."""

    def test_problem_multiline(self) -> None:
        result = parse_issue_body(FULL_BODY)
        assert "Banks process thousands" in result["problem"]
        assert "Manual review is slow" in result["problem"]
        assert "We need an automated solution." in result["problem"]

    def test_hypothesis_multiline(self) -> None:
        result = parse_issue_body(FULL_BODY)
        assert "Using LLMs" in result["hypothesis"]
        assert "95%+ accuracy" in result["hypothesis"]

    def test_business_value_multiline(self) -> None:
        result = parse_issue_body(FULL_BODY)
        assert "Saves 200 FTE-hours" in result["business_value"]
        assert "Reduces error rate" in result["business_value"]
        assert "Enables faster loan decisions." in result["business_value"]


class TestTechComponents:
    """Test tech_components split into list."""

    def test_splits_into_list(self) -> None:
        result = parse_issue_body(FULL_BODY)
        assert result["tech_components"] == [
            "pdf-extraction",
            "claude-api",
            "structured-output",
        ]

    def test_empty_when_missing(self) -> None:
        result = parse_issue_body(PARTIAL_BODY)
        assert result["tech_components"] == []

    def test_empty_when_no_response(self) -> None:
        body = "### Tech components\n\n_No response_\n"
        result = parse_issue_body(body)
        assert result["tech_components"] == []


class TestLinks:
    """Test link fields: pitch_url present, repo_url/docs_url as _No response_."""

    def test_pitch_url_present(self) -> None:
        result = parse_issue_body(FULL_BODY)
        assert result["pitch_url"] == "https://example.com/pitch.mp4"

    def test_repo_url_no_response_is_none(self) -> None:
        result = parse_issue_body(FULL_BODY)
        assert result["repo_url"] is None

    def test_docs_url_no_response_is_none(self) -> None:
        result = parse_issue_body(FULL_BODY)
        assert result["docs_url"] is None


class TestEmptyBody:
    """Test empty body returns all None/[]."""

    def test_empty_string(self) -> None:
        result = parse_issue_body("")
        assert result["title"] is None
        assert result["problem"] is None
        assert result["hypothesis"] is None
        assert result["business_value"] is None
        assert result["strategic_area"] is None
        assert result["arch_pattern"] is None
        assert result["status"] is None
        assert result["contact_name"] is None
        assert result["contact_email"] is None
        assert result["business_stakeholder"] is None
        assert result["tech_components"] == []
        assert result["source"] is None
        assert result["pitch_url"] is None
        assert result["repo_url"] is None
        assert result["docs_url"] is None


class TestPartialBody:
    """Test partial body with only some headers."""

    def test_present_fields(self) -> None:
        result = parse_issue_body(PARTIAL_BODY)
        assert result["title"] == "Quick credit check"
        assert result["problem"] == "Need faster credit checks."
        assert result["strategic_area"] == "Credit"

    def test_missing_fields_are_none(self) -> None:
        result = parse_issue_body(PARTIAL_BODY)
        assert result["hypothesis"] is None
        assert result["business_value"] is None
        assert result["arch_pattern"] is None
        assert result["status"] is None
        assert result["contact_name"] is None
        assert result["contact_email"] is None
        assert result["business_stakeholder"] is None
        assert result["source"] is None
        assert result["pitch_url"] is None
        assert result["repo_url"] is None
        assert result["docs_url"] is None
