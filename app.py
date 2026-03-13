from flask import Flask, render_template, request, jsonify
from bot import QuestionBot
from knowledge_base import KnowledgeBase
import os

app = Flask(__name__)

# 配置路径（PythonAnywhere 特定）
UPLOAD_FOLDER = os.path.join(os.path.expanduser('~'), 'QuestionBot', 'uploaded_files')
DB_PATH = os.path.join(os.path.expanduser('~'), 'QuestionBot', 'chroma_db')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 初始化
print("正在初始化系统...")
kb = KnowledgeBase(db_path=DB_PATH, collection_name="question_bot_kb")
bot = QuestionBot()


@app.route('/')
def index():
    try:
        stats = {"total_docs": kb.collection.count(), "db_path": DB_PATH}
    except:
        stats = {"total_docs": 0, "db_path": DB_PATH}
    return render_template('index.html', stats=stats)


@app.route('/ask', methods=['POST'])
def ask():
    try:
        data = request.get_json()
        question = data.get('question', '').strip()
        if not question:
            return jsonify({'error': '问题不能为空'}), 400

        context_results = kb.search(question, n_results=3)
        context = [r['content'] for r in context_results]
        answer = bot.ask(question, context)

        return jsonify({
            'success': True,
            'question': question,
            'answer': answer,
            'sources': [{'content': r['content'][:200] + "...", 'source': r['source']} for r in context_results]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/upload', methods=['POST'])
def upload_file():
    # 简化版：只支持文本上传
    try:
        data = request.get_json()
        text = data.get('text', '').strip()
        source = data.get('source', '手动输入')

        if not text:
            return jsonify({'error': '文本不能为空'}), 400

        kb.add_documents([text], metadatas=[{"source": source}])
        return jsonify({'success': True, 'message': '已添加到知识库'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/knowledge_base', methods=['GET'])
def get_knowledge_base():
    try:
        results = kb.list_all(limit=50)
        documents = []
        for doc_id, doc, meta in zip(results['ids'], results['documents'], results['metadatas']):
            documents.append({
                'id': doc_id,
                'content': doc[:200] + "..." if len(doc) > 200 else doc,
                'source': meta.get('source', '未知')
            })
        return jsonify({'success': True, 'total': kb.collection.count(), 'documents': documents})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# WSGI 需要这个变量名
application = app

if __name__ == '__main__':
    app.run(debug=True)