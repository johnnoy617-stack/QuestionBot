from flask import Flask, render_template, request, jsonify, send_from_directory
from bot import QuestionBot
from knowledge_base import KnowledgeBase
import os

# ========== PythonAnywhere 配置 ==========
# 获取环境变量（在 PythonAnywhere 的 Web 标签中设置）
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY')

app = Flask(__name__)

# 配置上传文件夹（PythonAnywhere 有特定路径限制）
# 免费用户只能用 /home/你的用户名/ 下的目录
UPLOAD_FOLDER = os.path.join(os.path.expanduser('~'), 'QuestionBot', 'uploaded_files')
ALLOWED_EXTENSIONS = {'txt', 'md', 'py', 'json', 'csv'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 知识库存储路径（必须在用户目录下）
DB_PATH = os.path.join(os.path.expanduser('~'), 'QuestionBot', 'chroma_db')

# 初始化（全局只初始化一次）
print("正在初始化系统...")
kb = KnowledgeBase(db_path=DB_PATH, collection_name="question_bot_kb")
bot = QuestionBot()  # 确保从环境变量读取 API Key


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    """渲染首页"""
    try:
        stats = {
            "total_docs": kb.collection.count(),
            "db_path": DB_PATH
        }
    except:
        stats = {"total_docs": 0, "db_path": DB_PATH}

    return render_template('index.html', stats=stats)


@app.route('/ask', methods=['POST'])
def ask():
    """处理用户提问"""
    try:
        data = request.get_json()
        question = data.get('question', '').strip()

        if not question:
            return jsonify({'error': '问题不能为空'}), 400

        print(f"\n收到问题：{question}")

        # RAG 流程
        print("正在检索知识库...")
        context_results = kb.search(question, n_results=3)
        context = [r['content'] for r in context_results]
        print(f"检索到 {len(context)} 条相关知识")

        answer = bot.ask(question, context)

        return jsonify({
            'success': True,
            'question': question,
            'answer': answer,
            'sources': [{'content': r['content'][:200] + "...", 'source': r['source']} for r in context_results]
        })

    except Exception as e:
        import traceback
        error_msg = f"处理请求时出错：{str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        return jsonify({'error': str(e)}), 500


@app.route('/upload', methods=['POST'])
def upload_file():
    """处理文件上传"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': '没有文件'}), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({'error': '文件名为空'}), 400

        if file and allowed_file(file.filename):
            filename = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filename)

            success = kb.add_from_file(filename)

            if success:
                return jsonify({
                    'success': True,
                    'message': f'文件 {file.filename} 上传成功',
                    'filename': file.filename
                })
            else:
                return jsonify({'error': '加入知识库失败'}), 500
        else:
            return jsonify({'error': '不支持的文件类型'}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/upload_text', methods=['POST'])
def upload_text():
    """直接上传文本"""
    try:
        data = request.get_json()
        text = data.get('text', '').strip()
        source = data.get('source', '手动输入')

        if not text:
            return jsonify({'error': '文本内容不能为空'}), 400

        kb.add_documents([text], metadatas=[{"source": source}])

        return jsonify({
            'success': True,
            'message': '文本已加入知识库',
            'length': len(text)
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/knowledge_base', methods=['GET'])
def get_knowledge_base():
    """获取知识库信息"""
    try:
        limit = request.args.get('limit', 50, type=int)
        results = kb.list_all(limit=limit)

        documents = []
        for doc_id, doc, meta in zip(results['ids'], results['documents'], results['metadatas']):
            documents.append({
                'id': doc_id,
                'content': doc[:200] + "..." if len(doc) > 200 else doc,
                'source': meta.get('source', '未知'),
                'time': meta.get('add_time', '未知')
            })

        return jsonify({
            'success': True,
            'total': kb.collection.count(),
            'documents': documents
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/delete_doc', methods=['POST'])
def delete_doc():
    """删除指定文档"""
    try:
        data = request.get_json()
        doc_id = data.get('id')

        if not doc_id:
            return jsonify({'error': '缺少文档ID'}), 400

        success = kb.delete_document(doc_id)

        if success:
            return jsonify({'success': True, 'message': '删除成功'})
        else:
            return jsonify({'error': '删除失败'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ========== PythonAnywhere 需要的特定配置 ==========

# 这个变量名必须是 'application'，PythonAnywhere 默认找它
# 但我们用 Flask 的 app，所以需要兼容
application = app

if __name__ == '__main__':
    # 本地开发用
    app.run(debug=True, host='0.0.0.0', port=5000)
else:
    # 生产环境（PythonAnywhere）
    # 确保模板和静态文件路径正确
    import os

    project_dir = os.path.dirname(os.path.abspath(__file__))
    app.template_folder = os.path.join(project_dir, 'templates')
    app.static_folder = os.path.join(project_dir, 'static')