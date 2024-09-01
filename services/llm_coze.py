import requests
import os
from dotenv import load_dotenv

load_dotenv()

class LLMCoze:
    def __init__(self):
        self.api_key = os.getenv('COZE_API_KEY')
        self.base_url = os.getenv('COZE_BASE_URL')
        
    def generate_response(self, prompt):
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        data = {
            "bot_id": "7348293334459318316",
            "user_id": "123456789",
            "stream": False,
            "auto_save_history": True,
            "additional_messages": [
                {
                    "role": "user",
                    "content": "What a nice day",
                    "content_type": "text"
                }
            ]
        }
                
            