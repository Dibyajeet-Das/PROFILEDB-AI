import logging

from app.ingest_service import IngestionService

logging.basicConfig(level=logging.INFO,format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")

ingestion_service = IngestionService()

ingestion_service.ingest_logs(batch_size=100)

