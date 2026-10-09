import logging
from pathlib import Path

from app.logingest import LogIngestion
from app.embedding import EmbeddingService
from app.chroma import ChromaService
from app.logparser import parse_log_line


logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent

LOG_FILE_PATH = BASE_DIR / "data" / "server.log"


class IngestionService:

    def __init__(self):
        try:
            logger.info("Initializing ingestion service.")

            self.log_ingestion = LogIngestion(str(LOG_FILE_PATH))
            self.embedding_service = EmbeddingService()
            self.chroma_service = ChromaService()

            logger.info("Ingestion service initialized successfully.")

        except Exception:
            logger.exception("Failed to initialize ingestion service.")
            raise

    def ingest_logs(self, batch_size=100):
        try:
            logger.info("Log ingestion started. Batch size=%s", batch_size)

            batch_number = 0
            total_logs = 0

            for logs in self.log_ingestion.read_logs(batch_size=batch_size):

                batch_number += 1

                logger.info("Processing batch=%s, size=%s", batch_number, len(logs))

                embeddings = self.embedding_service.create_embeddings(logs)

                ids = [f"server_log_{batch_number}_{i}" for i in range(len(logs))]

                # NEW: build metadata for each log line using the parser
                metadatas = []
                for i, log in enumerate(logs):
                    meta = {
                        "source": "server.log",
                        "batch_number": batch_number,
                        "seq": (batch_number - 1) * batch_size + i,
                    }
                    meta.update(parse_log_line(log))   # adds level, thread, class_name, ts_ms, record_id
                    metadatas.append(meta)

                self.chroma_service.add_documents(ids, logs, embeddings, metadatas)

                total_logs += len(logs)

                logger.info(
                    "Batch processed successfully. Batch=%s, Total logs=%s",
                    batch_number,
                    total_logs
                )

                # TEMPORARY TEST LIMIT
                if batch_number >= 50:
                    logger.info("Test limit reached. Stopping ingestion.")
                    break

            total_documents = self.chroma_service.count_documents()

            logger.info(
                "Log ingestion completed successfully. "
                "Total logs=%s, ChromaDB documents=%s",
                total_logs,
                total_documents
            )

        except Exception:
            logger.exception("Log ingestion failed.")
            raise