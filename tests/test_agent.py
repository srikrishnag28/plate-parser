import pytest
from unittest.mock import patch, MagicMock
from app.agent import _extract_code, _extract_pdf_text


def test_extract_code_strips_markdown_fences():
    raw = "```python\nprint('hello')\n```"
    assert _extract_code(raw) == "print('hello')"


def test_extract_code_no_fences():
    raw = "import sys\nprint(sys.argv)"
    assert _extract_code(raw) == raw.strip()


def test_extract_code_generic_fence():
    raw = "```\nsome code\n```"
    assert _extract_code(raw) == "some code"


def test_extract_pdf_text_invalid_bytes():
    result = _extract_pdf_text(b"not a pdf")
    assert result == ""


def test_extract_pdf_text_empty():
    result = _extract_pdf_text(b"")
    assert result == ""


def test_generate_parser_calls_gemini(sample_csv):
    from tests.conftest import SAMPLE_OUTPUT_JSON
    from app import agent as agent_module

    with patch.object(agent_module, "_call_gemini", return_value="import sys, json\nprint(json.dumps({}))") as mock_gemini, \
         patch.object(agent_module, "run_parser_in_sandbox", return_value=SAMPLE_OUTPUT_JSON), \
         patch.object(agent_module, "validate_output", return_value=(True, "")):

        code, output = agent_module.generate_parser(sample_csv, b"%PDF-fake")

        mock_gemini.assert_called_once()
        assert "<raw_data>" in mock_gemini.call_args[0][0]


def test_generate_parser_raises_on_invalid_output(sample_csv):
    from app import agent as agent_module

    with patch.object(agent_module, "_call_gemini", return_value="import sys\nprint('{}')"), \
         patch.object(agent_module, "run_parser_in_sandbox", return_value={}), \
         patch.object(agent_module, "validate_output", return_value=(False, "missing fields")):

        with pytest.raises(RuntimeError, match="invalid output"):
            agent_module.generate_parser(sample_csv, b"%PDF-fake")


@pytest.fixture
def sample_csv():
    return "well,value\nA1,0.5\nA2,0.6\n"
