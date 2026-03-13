import chromadb
from chromadb.utils import embedding_functions
import os
from datetime import datetime


class KnowledgeBase:
    def __init__(self, db_path="./chroma_db", collection_name="my_knowledge"):
        self.db_path = os.path.abspath(db_path)
        os.makedirs(self.db_path, exist_ok=True)

        print(f"知识库位置: {self.db_path}")

        self.client = chromadb.PersistentClient(path=self.db_path)
        self.embedding_function = embedding_functions.DefaultEmbeddingFunction()

        try:
            self.collection = self.client.get_collection(
                name=collection_name,
                embedding_function=self.embedding_function
            )
            print(f"已加载知识库: {collection_name}（{self.collection.count()} 条）")
        except:
            self.collection = self.client.create_collection(
                name=collection_name,
                embedding_function=self.embedding_function
            )
            print(f"创建新知识库: {collection_name}")

    def add_documents(self, documents, metadatas=None, ids=None):
        if not documents:
            return False

        if ids is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            ids = [f"doc_{timestamp}_{i}" for i in range(len(documents))]

        if metadatas is None:
            metadatas = [{"add_time": datetime.now().isoformat()} for _ in documents]

        self.collection.add(documents=documents, metadatas=metadatas, ids=ids)
        print(f"添加 {len(documents)} 条文档")
        return True

    def search(self, query, n_results=3):
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            include=['documents', 'metadatas']
        )

        documents = results['documents'][0] if results['documents'] else []
        metadatas = results['metadatas'][0] if results['metadatas'] else []

        return [{'content': doc, 'source': meta.get('source', '未知')}
                for doc, meta in zip(documents, metadatas)]

    def list_all(self, limit=100):
        return self.collection.get(limit=limit)

    def delete_document(self, doc_id):
        try:
            self.collection.delete(ids=[doc_id])
            return True
        except:
            return False