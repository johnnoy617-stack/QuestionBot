import requests
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class QuestionBot:
    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("请在 .env 文件中设置 DEEPSEEK_API_KEY")

        self.api_url = "https://api.deepseek.com/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def ask(self, question, context=None):
        """
        调用 DeepSeek API 回答问题
        context: 从知识库检索到的相关文本列表
        """
        # 构建系统提示词
        system_prompt = "你是一个智能助手，基于提供的知识库信息回答用户问题。如果知识库中没有相关信息，请基于你的知识回答。"

        # 构建用户提示词（结合上下文）
        if context:
            context_text = "\n".join([f"- {doc}" for doc in context])
            user_prompt = f"""基于以下知识库信息回答问题：

知识库内容：
{context_text}

用户问题：{question}

请根据以上信息给出准确、简洁的回答："""
        else:
            user_prompt = question

        # 构建请求体
        payload = {
            "model": "deepseek-chat",  # 使用 DeepSeek-V3 模型
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 1000
        }

        try:
            print(f"正在调用 DeepSeek API，问题：{question[:50]}...")
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()

            result = response.json()
            answer = result['choices'][0]['message']['content']
            print("API 调用成功！")
            return answer

        except requests.exceptions.RequestException as e:
            error_msg = f"API 调用失败：{str(e)}"
            print(error_msg)
            return error_msg
        except (KeyError, IndexError) as e:
            error_msg = f"解析响应失败：{str(e)}"
            print(error_msg)
            return error_msg


# 测试代码
if __name__ == "__main__":
    bot = QuestionBot()
    answer = bot.ask("什么是 Python？")
    print("回答：", answer)