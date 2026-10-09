import re
from datetime import datetime

LINE_RE = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})"
    r".*?\((?P<thread>[^)]+)\)\s+\[(?P<level>[A-Z]+)\s*\]"
    r".*?\[(?P=thread)\]\s+(?P<cls>\S+)"
)
RECORD_RE = re.compile(r"record\s?id\s*[=:]\s*(\d+)", re.IGNORECASE)


def parse_log_line(line: str) -> dict:
    # ChromaDB metadata cannot be None, so use plain defaults
    meta = {"level": "UNKNOWN", "thread": "", "class_name": "", "ts_ms": 0, "record_id": 0}

    m = LINE_RE.match(line)
    if m:
        dt = datetime.strptime(m.group("ts"), "%Y-%m-%d %H:%M:%S,%f")
        meta["ts_ms"] = int(dt.timestamp() * 1000)
        meta["thread"] = m.group("thread")
        meta["level"] = m.group("level")
        meta["class_name"] = m.group("cls")

    r = RECORD_RE.search(line)
    if r:
        meta["record_id"] = int(r.group(1))

    return meta