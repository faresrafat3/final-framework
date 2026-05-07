import json
from io import StringIO
from unittest.mock import patch

import pytest

from aio.cli import _cmd_run


class TestCLIStreaming:
    def test_stream_flag_prints_ndjson(self, capsys):
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            exit_code = _cmd_run(["echo hello", "--stream"])
            assert exit_code == 0
            output = mock_stdout.getvalue()
            lines = [ln for ln in output.splitlines() if ln.strip()]
            # At least one NDJSON line (the final JSON result) plus streaming events
            ndjson_events = []
            final_json = None
            for line in lines:
                try:
                    data = json.loads(line)
                    if "layer" in data:
                        ndjson_events.append(data)
                    else:
                        final_json = data
                except json.JSONDecodeError:
                    pass
            assert len(ndjson_events) > 0
            assert final_json is not None
            assert final_json.get("output") is not None

    def test_no_stream_flag_no_ndjson(self, capsys):
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            exit_code = _cmd_run(["echo hello"])
            assert exit_code == 0
            output = mock_stdout.getvalue()
            lines = [ln for ln in output.splitlines() if ln.strip()]
            # Should have exactly one JSON block (the result)
            assert len(lines) == 1
            data = json.loads(lines[0])
            assert "layer" not in data
            assert data.get("output") is not None
