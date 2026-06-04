import pytest
from unittest.mock import patch
from app.agent import _extract_code


def test_extract_code_strips_markdown_fences():
    raw = "```python\nprint('hello')\n```"
    assert _extract_code(raw) == "print('hello')"


def test_extract_code_no_fences():
    raw = "import sys\nprint(sys.argv)"
    assert _extract_code(raw) == raw.strip()


def test_extract_code_generic_fence():
    raw = "```\nsome code\n```"
    assert _extract_code(raw) == "some code"


def test_generate_parser_calls_ai(sample_csv):
    from tests.conftest import SAMPLE_OUTPUT_JSON
    from app import agent as agent_module

    with patch.object(agent_module, "_call_ai", return_value="import sys, json\nprint(json.dumps({}))") as mock_ai, \
         patch.object(agent_module, "run_parser_in_sandbox", return_value=SAMPLE_OUTPUT_JSON), \
         patch.object(agent_module, "validate_output", return_value=(True, "")):

        code, output = agent_module.generate_parser(sample_csv, b"%PDF-fake")

        mock_ai.assert_called_once()
        # Untrusted file content must be fenced in <raw_data> tags in the prompt.
        assert "<raw_data>" in mock_ai.call_args[0][0]


def test_generate_parser_raises_after_retries_exhausted(sample_csv):
    from app import agent as agent_module

    # validate_output always fails → retry loop exhausts all attempts and raises.
    # Patch both the initial call and the retry/fix call so no network is hit.
    with patch.object(agent_module, "_call_ai", return_value="import sys\nprint('{}')"), \
         patch.object(agent_module, "_call_retry_model", return_value="import sys\nprint('{}')"), \
         patch.object(agent_module, "run_parser_in_sandbox", return_value={}), \
         patch.object(agent_module, "validate_output", return_value=(False, "missing fields")):

        with pytest.raises(RuntimeError, match="Parser failed after"):
            agent_module.generate_parser(sample_csv, b"%PDF-fake")


@pytest.fixture
def sample_csv():
    return "well,value\nA1,0.5\nA2,0.6\n"
