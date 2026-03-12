from flask import Flask, render_template, request, jsonify, send_from_directory
from bot import QuestionBot
from knowledge_base import KnowledgeBase
import os
import json

app = Flask(__name__)

# 配置上传文件夹
UPLOAD_FOLDER = './uploaded_files'
ALLOWED_EXTENSIONS = {'txt', 'md', 'py', 'json', 'csv', 'docx', 'pdf'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 最大 16MB

# 确保上传文件夹存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 初始化知识库（使用持久化存储）
print("正在初始化系统...")
kb = KnowledgeBase(db_path="./chroma_db", collection_name="question_bot_kb")
bot = QuestionBot()


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    """渲染首页"""
    # 获取知识库统计，传递给前端显示
    try:
        stats = {
            "total_docs": kb.collection.count(),
            "db_path": kb.db_path
        }
    except:
        stats = {
            "total_docs": 0,
            "db_path": "未连接"
        }

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

        # 1. 检索知识库
        print("正在检索知识库...")
        context_results = kb.search(question, n_results=3)
        context = [r['content'] for r in context_results]
        print(f"检索到 {len(context)} 条相关知识")

        # 2. 调用大模型
        answer = bot.ask(question, context)

        # 3. 返回结果（包含来源信息）
        return jsonify({
            'success': True,
            'question': question,
            'answer': answer,
            'sources': [{'content': r['content'][:200] + "...", 'source': r['source']} for r in context_results]
        })

    except Exception as e:
        error_msg = f"处理请求时出错：{str(e)}"
        print(error_msg)
        return jsonify({'error': error_msg}), 500


@app.route('/upload', methods=['POST'])
def upload_file():
    """处理文件上传"""
    try:
        # 检查是否有文件
        if 'file' not in request.files:
            return jsonify({'error': '没有文件'}), 400

        file = request.files['file']

        # 检查文件名
        if file.filename == '':
            return jsonify({'error': '文件名为空'}), 400

        if file and allowed_file(file.filename):
            # 安全保存文件
            filename = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filename)

            # 添加到知识库
            success = kb.add_from_file(filename)

            if success:
                return jsonify({
                    'success': True,
                    'message': f'文件 {file.filename} 上传成功并已加入知识库',
                    'filename': file.filename
                })
            else:
                return jsonify({'error': '文件保存成功但加入知识库失败'}), 500
        else:
            return jsonify({'error': f'不支持的文件类型，请上传: {ALLOWED_EXTENSIONS}'}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/upload_text', methods=['POST'])
def upload_text():
    """直接上传文本内容"""
    try:
        data = request.get_json()
        text = data.get('text', '').strip()
        source = data.get('source', '手动输入')

        if not text:
            return jsonify({'error': '文本内容不能为空'}), 400

        # 添加到知识库
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


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """访问上传的文件"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("🤖 智能 Question Bot 已启动！")
    print(f"📁 知识库位置: {os.path.abspath('./chroma_db')}")
    print(f"📂 上传文件位置: {os.path.abspath(UPLOAD_FOLDER)}")
    print("💡 访问: http://127.0.0.1:5000")
    print("=" * 60 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5000)