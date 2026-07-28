import json

from asgi_correlation_id import correlation_id

from gene_explorer.logging_config import _add_request_id, configure_logging, get_logger


def test_add_request_id_includes_id_when_set():
    token = correlation_id.set("abc-123")
    try:
        out = _add_request_id(None, "info", {"event": "x"})
        assert out["request_id"] == "abc-123"
    finally:
        correlation_id.reset(token)


def test_add_request_id_omits_id_when_unset():
    out = _add_request_id(None, "info", {"event": "x"})
    assert "request_id" not in out


def test_json_logging_emits_valid_json(capsys):
    configure_logging("INFO", json_logs=True)
    get_logger("test").info("hello", answer=0.032)
    line = capsys.readouterr().out.strip().splitlines()[-1]
    record = json.loads(line)
    assert record["event"] == "hello"
    assert record["answer"] == 0.032
    assert record["level"] == "info"


def test_console_logging_traceback_omits_frame_locals(capsys):
    # Regression: the console traceback must NOT dump frame locals, which can
    # contain the user's message (PII).
    configure_logging("INFO", json_logs=False)
    secret = "SENTINEL-PII-4242"
    try:
        message = secret  # a frame local a naive traceback would render
        raise ValueError("boom-" + message[:0])
    except ValueError:
        get_logger("test").exception("failed")
    out = capsys.readouterr().out
    assert "failed" in out
    assert secret not in out
