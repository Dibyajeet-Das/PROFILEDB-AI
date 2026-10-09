from app.chroma import ChromaService

c = ChromaService()
print("count:", c.count_documents())
print("metadata:", c.get_by_id("server_log_16_42")["metadatas"])
print("ERROR lines:", len(c.get_where({"level": "ERROR"}, limit=500)["ids"]))