import chromadb
from chromadb.utils import embedding_functions
import os
import json
from datetime import datetime


class KnowledgeBase:
    def __init__(self, db_path="./chroma_db", collection_name="my_knowledge"):
        """
        db_path: 数据库文件夹路径（相对于项目根目录）
        collection_name: 集合名称（类似数据库的表名）
        """
        self.db_path = os.path.abspath(db_path)
        os.makedirs(self.db_path, exist_ok=True)

        print(f"📁 知识库位置: {self.db_path}")

        # 使用持久化客户端（数据保存到硬盘）
        self.client = chromadb.PersistentClient(path=self.db_path)

        # 使用默认嵌入函数（无需下载大模型）
        self.embedding_function = embedding_functions.DefaultEmbeddingFunction()

        # 获取或创建集合
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
        """
        添加文档到知识库

        documents: 文本内容列表 ["内容1", "内容2"]
        metadatas: 元数据列表 [{"source": "file1.txt", "time": "2024-01-01"}, ...]
        ids: 唯一标识列表（可选，不传会自动生成）
        """
        if not documents:
            return False

        # 自动生成 ID（基于时间和序号）
        if ids is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            ids = [f"doc_{timestamp}_{i}" for i in range(len(documents))]

        # 默认元数据
        if metadatas is None:
            metadatas = [{"add_time": datetime.now().isoformat()} for _ in documents]

        # 添加到 ChromaDB
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

        print(f"✅ 成功添加 {len(documents)} 条文档")
        return True

    def add_from_file(self, file_path):
        """
        从文件添加文档（支持 .txt, .md, .py, .json 等文本文件）
        """
        if not os.path.exists(file_path):
            print(f"❌ 文件不存在: {file_path}")
            return False

        # 读取文件
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"❌ 读取文件失败: {e}")
            return False

        # 智能切分长文档（如果文件太大）
        chunks = self._split_text(content, max_length=500)

        # 准备元数据
        file_name = os.path.basename(file_path)
        metadatas = [{
            "source": file_name,
            "file_path": file_path,
            "chunk_index": i,
            "total_chunks": len(chunks),
            "add_time": datetime.now().isoformat()
        } for i in range(len(chunks))]

        # 添加
        ids = [f"{file_name}_chunk_{i}" for i in range(len(chunks))]
        self.add_documents(chunks, metadatas, ids)

        print(f"📄 文件 '{file_name}' 已切分为 {len(chunks)} 段加入知识库")
        return True

    def add_from_directory(self, dir_path, file_types=None):
        """
        批量添加文件夹中的所有文档

        file_types: 文件后缀列表，如 ['.txt', '.md', '.py']
        """
        if file_types is None:
            file_types = ['.txt', '.md', '.py', '.json', '.csv', '.docx']

        added_count = 0
        for root, dirs, files in os.walk(dir_path):
            for file in files:
                if any(file.endswith(ext) for ext in file_types):
                    file_path = os.path.join(root, file)
                    if self.add_from_file(file_path):
                        added_count += 1

        print(f"\n📂 批量导入完成！共添加 {added_count} 个文件")
        return added_count

    def _split_text(self, text, max_length=500, overlap=50):
        """
        将长文本切分成小块（避免超过模型处理长度）

        text: 原始文本
        max_length: 每块最大字符数
        overlap: 块之间重叠字符数（保证语义连贯）
        """
        if len(text) <= max_length:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = start + max_length
            chunk = text[start:end]

            # 尽量在句子结尾处切断
            if end < len(text):
                # 找最后一个句号、问号或换行
                for sep in ['。', '？', '！', '.', '?', '!', '\n']:
                    last_sep = chunk.rfind(sep)
                    if last_sep > max_length * 0.5:  # 至少保留一半内容
                        end = start + last_sep + 1
                        chunk = text[start:end]
                        break

            chunks.append(chunk.strip())
            start = end - overlap  # 重叠部分保证上下文连贯

        return chunks

    def search(self, query, n_results=3):
        """搜索知识库"""
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            include=['documents', 'metadatas', 'distances']
        )

        documents = results['documents'][0] if results['documents'] else []
        metadatas = results['metadatas'][0] if results['metadatas'] else []

        # 格式化返回结果
        formatted_results = []
        for doc, meta in zip(documents, metadatas):
            formatted_results.append({
                'content': doc,
                'source': meta.get('source', '未知来源'),
                'time': meta.get('add_time', '未知时间')
            })

        return formatted_results

    def list_all(self, limit=100):
        """列出知识库中的所有文档"""
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
        """删除指定文档"""
        try:
            self.collection.delete(ids=[doc_id])
            print(f"🗑️ 已删除文档: {doc_id}")
            return True
        except Exception as e:
            print(f"❌ 删除失败: {e}")
            return False

    def clear_all(self):
        """清空整个知识库（危险操作！）"""
        confirm = input("⚠️ 确定要清空所有数据吗？输入 'yes' 确认: ")
        if confirm.lower() == 'yes':
            # 获取所有 ID 并删除
            all_data = self.collection.get()
            if all_data['ids']:
                self.collection.delete(ids=all_data['ids'])
                print("🧹 知识库已清空")
            return True
        else:
            print("操作已取消")
            return False


# 测试代码
if __name__ == "__main__":
    kb = KnowledgeBase()

    # 方式1：直接添加文本
    kb.add_documents([
        "Python 是一种高级编程语言，由 Guido van Rossum 于 1991 年创建。",
        "Flask 是一个用 Python 编写的轻量级 Web 应用框架。"
    ], metadatas=[
        {"source": "manual_input", "topic": "编程"},
        {"source": "manual_input", "topic": "Web开发"}
    ])

    # 方式2：从文件添加（创建测试文件）
    with open("test_doc.txt", "w", encoding="utf-8") as f:
        f.write("ChromaDB 是一个开源的向量数据库，用于 AI 应用。")

    kb.add_from_file("test_doc.txt")

    # 查看所有文档
    kb.list_all()

    # 测试搜索
    print("\n🔍 搜索 'Python':")
    results = kb.search("Python", n_results=2)
    for r in results:
        print(f"  来源: {r['source']}")
        print(f"  内容: {r['content'][:100]}...")
        print()