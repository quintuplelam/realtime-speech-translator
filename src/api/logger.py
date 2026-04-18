from pathlib import Path
from datetime import datetime

class SessionLogger:
    def __init__(self, base_dir: str | Path, session_id: str):
        self.base_dir = Path(base_dir)
        self.session_id = session_id
        self.session_dir = self.base_dir / session_id
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self._init_log_file()

    def _init_log_file(self):
        log_file = self.session_dir / "session.md"
        if not log_file.exists():
            log_file.write_text(f"# Session Log: {self.session_id}\n\n")

    def log(self, en: str, zh: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"| {timestamp} | {en} | {zh} |\n"
        log_file = self.session_dir / "session.md"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(entry)