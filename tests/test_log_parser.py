from app.core.log_parser import AppState, LogParser, final_state, line_has_error


def test_log_parser_counts_downloads_and_errors() -> None:
    parser = LogParser()
    parser.parse_line("2026-01-01 10:00:00 INFO Downloaded /tmp/a.jpg")
    parser.parse_line("2026-01-01 10:00:01 ERROR Failed to download /tmp/b.jpg")

    assert parser.summary.downloaded_count == 1
    assert parser.summary.error_count == 1
    assert "Failed to download" in parser.summary.last_error


def test_log_parser_case_insensitive() -> None:
    parser = LogParser()
    event = parser.parse_line("2026-01-01 10:00:01 error failed")
    assert event.error


def test_log_parser_does_not_flag_informational_error_word() -> None:
    parser = LogParser()
    event = parser.parse_line("2026-01-01 10:00:01 INFO previous error count: 0")
    assert not event.error
    assert parser.summary.error_count == 0


def test_log_parser_detects_mfa_and_webui_url() -> None:
    parser = LogParser()
    event1 = parser.parse_line(
        "2026-01-01 10:00:00 INFO Starting web server for WebUI authentication..."
    )
    event2 = parser.parse_line("2026-01-01 10:00:01 INFO Two-factor authentication is required (2fa)")

    assert event1.webui_url == "http://127.0.0.1:8080/"
    assert event2.mfa_required
    assert event2.webui_url == "http://127.0.0.1:8080/"


def test_log_parser_detects_done() -> None:
    parser = LogParser()
    event = parser.parse_line("2026-01-01 10:00:02 INFO All photos and videos have been downloaded")
    assert event.done


def test_log_parser_detects_exception_and_failed_patterns() -> None:
    parser = LogParser()
    event1 = parser.parse_line("2026-01-01 10:00:01 INFO failed to download photo")
    event2 = parser.parse_line("2026-01-01 10:00:02 INFO traceback (most recent call last)")
    assert event1.error
    assert event2.error
    assert parser.summary.error_count == 2


def test_final_state_rules() -> None:
    parser = LogParser()
    parser.parse_line("INFO Downloaded /tmp/x.jpg")
    assert final_state(0, parser.summary, was_stopped=False) == AppState.DONE
    assert final_state(1, parser.summary, was_stopped=False) == AppState.ERROR
    assert final_state(1, parser.summary, was_stopped=True) == AppState.IDLE


def test_log_parser_transient_error_detection() -> None:
    parser = LogParser()
    event = parser.parse_line("2026-01-01 10:00:01 ERROR connection reset by peer")
    assert event.error
    assert event.transient_error
    assert parser.summary.transient_error


def test_line_has_error() -> None:
    assert line_has_error("2026 ERROR bad")
    assert not line_has_error("2026 INFO all good")
