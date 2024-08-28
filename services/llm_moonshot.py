import os
from dotenv import load_dotenv
import logging
from openai import OpenAI

# 设置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(filename)s - %(funcName)s - %(lineno)d - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

moonshot_url = "https://api.moonshot.cn/v1"
class LLMMoonshot:    
    def __init__(self, model_name: str):
        load_dotenv()
        
        self.detail_sys_prompt = os.getenv('DETAIL_SYS_PROMPT')
        self.tag_selector_sys_prompt = os.getenv('TAG_SELECTOR_SYS_PROMPT')
        self.language_sys_prompt = os.getenv('LANGUAGE_SYS_PROMPT')
        self.introduction_sys_prompt = os.getenv('INTRODUCTION_SYS_PROMPT')
        self.features_sys_prompt = os.getenv('FEATURE_SYS_PROMPT')
        self.model_name = model_name
        
    def completion(self, system_prompt, user_prompt) -> str:
        client = OpenAI(
            api_key = os.getenv('MOONSHOT_API_KEY'),
            base_url = moonshot_url,
        )
        completion = client.chat.completions.create(
            model = self.model_name,
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature = 0.3,
        )
        return completion.choices[0].message.content

    def process_detail(self, user_prompt):
        logger.info("正在处理Detail...")
        return self.completion(self.detail_sys_prompt, user_prompt)

    def generate_introduction(self, sys_prompt, user_prompt):
        logger.info("正在生成简介...")
        if len(sys_prompt) == 0:
            sys_prompt = self.introduction_sys_prompt
        print(sys_prompt, user_prompt)
        return self.completion(sys_prompt, user_prompt)
    
    def generate_features(self, sys_prompt,user_prompt):
        logger.info("正在生成特性...")
        if len(sys_prompt) == 0:
            sys_prompt = self.features_sys_prompt
        return self.completion(sys_prompt, user_prompt)
        
    def process_tags(self, user_prompt):
        logger.info(f"正在处理tags...")
        tags = []
        result = self.completion(self.tag_selector_sys_prompt, user_prompt)
        if result:
            tags = [element.strip() for element in result.split(',')]
        else:
            tags = []
        return tags

    def process_language(self, language, user_prompt):
        logger.info(f"正在处理多语言:{language}, user_prompt:{user_prompt}")
        # 如果language 包含 English字符，则直接返回
        if 'english'.lower() in language.lower():
            result = user_prompt
        else:
            result = self.completion(self.language_sys_prompt.replace("{language}", language), user_prompt)
            if result and not user_prompt.startswith("#"):
                # 如果原始输入没有包含###开头的markdown标记，则去掉markdown标记
                result = result.replace("### ", "").replace("## ", "").replace("# ", "").replace("**", "")
            logger.info(f"多语言:{language}, 处理结果:{result}")
        return result

