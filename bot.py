import requests
import os


class QuestionBot:
    def __init__(self):
        # 优先从环境变量读取（部署环境），其次从 .env（本地开发）
        self.api_key = os.getenv("DEEPSEEK_API_KEY")

        if not self.api_key:
            # 本地开发时尝试从 .env 加载
            try:
                from dotenv import load_dotenv
                load_dotenv()
                self.api_key = os.getenv("DEEPSEEK_API_KEY")
            except:
                pass

        if not self.api_key:
            raise ValueError("未设置 DEEPSEEK_API_KEY 环境变量")

        self.api_url = "https://api.deepseek.com/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def ask(self, question, context=None):
        system_prompt = "你是一个智能助手，基于提供的知识库信息回答用户问题。"

        if context:
            context_text = "\n".join([f"- {doc}" for doc in context])
            user_prompt = f"""基于以下知识库信息回答问题：

知识库内容：
{context_text}

用户问题：{question}

请根据以上信息给出准确、简洁的回答："""
        else:
            user_prompt = question

        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 1000
        }

        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()

            result = response.json()
            return result['choices'][0]['message']['content']

        except Exception as e:
            return f"API 调用失败：{str(e)}"