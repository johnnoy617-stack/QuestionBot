import requests
import os


class QuestionBot:
    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("未设置 DEEPSEEK_API_KEY 环境变量")

        self.api_url = "https://api.deepseek.com/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def ask(self, question, context=None):
        system_prompt = "你是一个智能助手，基于知识库信息回答问题。"

        if context:
            context_text = "\n".join([f"- {doc}" for doc in context])
            user_prompt = f"""基于以下知识库信息回答：

{context_text}

问题：{question}"""
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
            return response.json()['choices'][0]['message']['content']
        except Exception as e:
            return f"API调用失败：{str(e)}"