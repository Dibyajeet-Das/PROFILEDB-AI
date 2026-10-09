import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class LogIngestion:

    def __init__(self, log_file_path: str):
        self.log_file_path = Path(log_file_path)

    def read_logs(self, batch_size=100):
        try:
            logger.info("Starting log file reading. File=%s", self.log_file_path)

            if not self.log_file_path.exists():
                raise FileNotFoundError(f"Log file not found: {self.log_file_path}")

            batch = []

            with open(self.log_file_path, "r", encoding="utf-8", errors="replace") as file:

                for line in file:
                    line = line.strip()

                    if not line:
                        continue

                    batch.append(line)

                    if len(batch) == batch_size:
                        logger.info("Log batch created. Size=%s", len(batch))
                        yield batch
                        batch = []

                # Remaining logs
                if batch:
                    logger.info("Final log batch created. Size=%s", len(batch))
                    yield batch

            logger.info("Log file reading completed.")

        except Exception:
            logger.exception("Failed while reading log file: %s", self.log_file_path)
            raise