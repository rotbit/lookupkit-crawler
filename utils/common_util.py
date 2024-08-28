import logging
import re
from urllib.parse import urlparse

# 设置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(filename)s - %(funcName)s - %(lineno)d - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CommonUtil:
    def detail_handle(self,detail):
        if detail:
            index1 = detail.find("#")
            index2 = detail.find("*")

            if index1 != -1 and index2 != -1:
                index = min(index1, index2)
                substring = detail[index:]
                return re.sub(r'\*\*(.+?)\*\*', '### \\1', substring)
            elif index1 != -1:
                substring = detail[index1:]
                return re.sub(r'\*\*(.+?)\*\*', '### \\1', substring)
            elif index2 != -1:
                substring = detail[index2:]
                return re.sub(r'\*\*(.+?)\*\*', '### \\1', substring)
            else:
                return re.sub(r'\*\*(.+?)\*\*', '### \\1', detail)
        else:
            return None

    # 根据url提取域名/path，返回为-拼接的方式
    @staticmethod
    def get_name_by_url(url):
        if url:
            domain = urlparse(url).netloc
            path= urlparse(url).path
            if path and path.endswith("/"):
                path = path[:-1]
            return (domain.replace("www.","") + path.replace("/", "-")).replace(".", "-")
        else:
            return None
        
def GetSupportLanguages():
    return ["chinese", "english", "japanese", "french", "spanish", "german", "russian", "portuguese", "繁体中文"]
        
def GetLangeageCode(language: str):
    language = str.lower(language)
    if language == "chinese":
        return "cn"
    if language == "english":
        return "en"
    if language == "japanese":
        return "jp"
    if language == "korean":
        return "kr"
    if language == "french":
        return "fr"
    if language == "spanish":
        return "es"
    if language == "german":
        return "de"
    if language == "italian":
        return "it"
    if language == "russian":
        return "ru"
    if language == "portuguese":
        return "pt"
    if language == "dutch":
        return "nl"
    if language == "polish":
        return "pl"
    if language == "turkish":
        return "tr"
    if language == "arabic":
        return "ar"
    if language == "swedish":
        return "sv"
    if language == "indonesian":
        return "id"
    if language == "thai":
        return "th"
    if language == "vietnamese":
        return "vi"
    if language == "greek":
        return "el"
    if language == "czech":
        return "cs"
    if language == "danish":
        return "da"
    if language == "finnish":
        return "fi"
    if language == "繁体中文":
        return "tw"
    return "en"

