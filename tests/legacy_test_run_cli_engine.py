import json
import sys

from engines import CliEngineConfig, run_cli_engine


def test_run_cli_engine_sends_prompt_via_stdin(tmp_path):
    prompt = "You are being piped"
    script = (
        "import json, sys; "
        "print(json.dumps({'argv': sys.argv[1:], 'stdin': sys.stdin.read()}))"
    )
    config = CliEngineConfig(binary=sys.executable, base_args=["-c", script], use_stdin=True)

    result = run_cli_engine(config, prompt)
    payload = json.loads(result.stdout.strip())

    assert payload["argv"] == []
    assert payload["stdin"] == prompt + "\n"
