import os
import tempfile
from src.api.logger import SessionLogger

def test_session_logger_creates_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = SessionLogger(tmpdir, "test-session")
        logger.log("Hello world", "你好世界")
        log_file = logger.session_dir / "session.md"
        assert log_file.exists()

def test_session_logger_format():
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = SessionLogger(tmpdir, "test-session")
        logger.log("Hello world", "你好世界")
        content = (logger.session_dir / "session.md").read_text()
        assert "Hello world" in content
        assert "你好世界" in content
        assert "test-session" in content