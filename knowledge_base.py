import chromadb
from chromadb.utils import embedding_functions
import os
from datetime import datetime


class KnowledgeBase:
    def __init__(self, db_path="./chroma_db", collection_name="my_knowledge"):
        self.db_path = os.path.abspath(db_path)
        os.makedirs(self.db_path, exist_ok=True)

        print(f"📁 知识库位置: {self.db_path}")

        # 使用持久化客户端
        self.client = chromadb.PersistentClient(path=self.db_path)

        # 使用默认嵌入函数（无需下载大模型，适合部署）
        self.embedding_function = embedding_functions.DefaultEmbeddingFunction()

        try:
            self.collection = self.client.get_collection(
                name=collection_name,
                embedding_function=self.embedding_function
            )
            count = self.collection.count()
            print(f"📚 已加载知识库: {collection_name}（{count} 条文档）")
        except Exception as e:
            self.collection = self.client.create_collection(
                name=collection_name,
                embedding_function=self.embedding_function
            )
            print(f"🆕 创建新知识库: {collection_name}")

    def add_documents(self, documents, metadatas=None, ids=None):
        if not documents:
            return False

        if ids is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            ids = [f"doc_{timestamp}_{i}" for i in range(len(documents))]

        if metadatas is None:
            metadatas = [{"add_time": datetime.now().isoformat()} for _ in documents]

        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

        print(f"✅ 成功添加 {len(documents)} 条文档")
        return True

    def add_from_file(self, file_path):
        if not os.path.exists(file_path):
            print(f"❌ 文件不存在: {file_path}")
            return False

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"❌ 读取文件失败: {e}")
            return False

        chunks = self._split_text(content, max_length=500)

        file_name = os.path.basename(file_path)
        metadatas = [{
            "source": file_name,
            "file_path": file_path,
            "chunk_index": i,
            "total_chunks": len(chunks),
            "add_time": datetime.now().isoformat()
        } for i in range(len(chunks))]

        ids = [f"{file_name}_chunk_{i}" for i in range(len(chunks))]
        self.add_documents(chunks, metadatas, ids)

        print(f"📄 文件 '{file_name}' 已切分为 {len(chunks)} 段加入知识库")
        return True

    def _split_text(self, text, max_length=500, overlap=50):
        if len(text) <= max_length:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = start + max_length
            chunk = text[start:end]

            if end < len(text):
                for sep in ['。', '？', '！', '.', '?', '!', '\n']:
                    last_sep = chunk.rfind(sep)
                    if last_sep > max_length * 0.5:
                        end = start + last_sep + 1
                        chunk = text[start:end]
                        break

            chunks.append(chunk.strip())
            start = end - overlap

        return chunks

    def search(self, query, n_results=3):
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            include=['documents', 'metadatas', 'distances']
        )

        documents = results['documents'][0] if results['documents'] else []
        metadatas = results['metadatas'][0] if results['metadatas'] else []

        formatted_results = []
        for doc, meta in zip(documents, metadatas):
            formatted_results.append({
                'content': doc,
                'source': meta.get('source', '未知来源'),
                'time': meta.get('add_time', '未知时间')
            })

        return formatted_results

    def list_all(self, limit=100):
        total = self.collection.count()
        results = self.collection.get(limit=limit)

        print(f"\n📋 知识库共有 {total} 条文档（显示前 {min(limit, total)} 条）：")
        print("-" * 50)

        for i, (doc_id, doc, meta) in enumerate(zip(results['ids'], results['documents'], results['metadatas'])):
            source = meta.get('source', '未知')
            preview = doc[:50] + "..." if len(doc) > 50 else doc
            print(f"{i + 1}. [{source}] {preview}")

        return results

    def delete_document(self, doc_id):
        try:
            self.collection.delete(ids=[doc_id])
            print(f"🗑️ 已删除文档: {doc_id}")
            return True
        except Exception as e:
            print(f"❌ 删除失败: {e}")
            return False