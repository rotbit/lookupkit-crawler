from bs4 import BeautifulSoup
import logging
import sys
import os
from playwright.async_api import async_playwright


sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))


from utils.common_util import CommonUtil
from utils.llm_util import LLMUtil
from utils.oss_util import OSSUtil
from utils.mongodb_utils import GetMongoClient

llm = LLMUtil()
oss = OSSUtil()

# 设置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(filename)s - %(funcName)s - %(lineno)d - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

global_agent_headers = [
    "Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:30.0) Gecko/20100101 Firefox/30.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_2) AppleWebKit/537.75.14 (KHTML, like Gecko) Version/7.0.3 Safari/537.75.14",
    "Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.2; Win64; x64; Trident/6.0)",
    'Mozilla/5.0 (Windows; U; Windows NT 5.1; it; rv:1.8.1.11) Gecko/20071127 Firefox/2.0.0.11',
    'Opera/9.25 (Windows NT 5.1; U; en)',
    'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; .NET CLR 1.1.4322; .NET CLR 2.0.50727)',
    'Mozilla/5.0 (compatible; Konqueror/3.5; Linux) KHTML/3.5.5 (like Gecko) (Kubuntu)',
    'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.8.0.12) Gecko/20070731 Ubuntu/dapper-security Firefox/1.5.0.12',
    'Lynx/2.8.5rel.1 libwww-FM/2.14 SSL-MM/1.4.1 GNUTLS/1.2.9',
    "Mozilla/5.0 (X11; Linux i686) AppleWebKit/535.7 (KHTML, like Gecko) Ubuntu/11.04 Chromium/16.0.912.77 Chrome/16.0.912.77 Safari/535.7",
    "Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:10.0) Gecko/20100101 Firefox/10.0 "
]

class WebsiteCrawler:
    def __init__(self):
        self.browser = None
        
    async def collect_website_info(self, url):
        async with async_playwright() as playwright:
            result = await self.collect_website_info_v2(playwright, url)
            return result
    
    # 提取站点数据        
    def get_website_data(self, origin_content, url):
        soup = BeautifulSoup(origin_content, 'html.parser')
         # 通过标签名提取内容
        title = soup.title.string.strip() if soup.title else ''

        # 根据url提取域名生成name
        name = CommonUtil.get_name_by_url(url)

        # 获取网页描述
        description = ''
        meta_description = soup.find('meta', attrs={'name': 'description'})
        if meta_description:
            description = meta_description['content'].strip()

        if not description:
            meta_description = soup.find('meta', attrs={'property': 'og:description'})
            description = meta_description['content'].strip() if meta_description else ''
            
        # 抓取整个网页内容
        content = soup.get_text()
        
        return {
            'name': name,
            'title': title,
            'description': description,
            'content': content
        }
        
    async def capture_screenshot(self, page, url):
        width = 1920  # 默认宽度为 1920
        height = 1080  # 默认高度为 1080
        dimensions = await page.evaluate('''({width, height}) => {
            return {
                width: Number(width),
                height: Number(height),
                deviceScaleFactor: window.devicePixelRatio
            };
        }''', { 'width': width, 'height': height })
        
        screenshot_path = './' + url.replace("https://", "").replace("http://", "").replace("/", "").replace(".", "-") + '.png'
        await page.screenshot(path=screenshot_path, clip={
            'x': 0,
            'y': 0,
            'width': dimensions['width'],
            'height': dimensions['height']
        })
        
        # 图片上传oss
        image_key = oss.get_default_file_key(url)
        # 上传图片，返回图片地址
        screenshot = oss.upload_file_to_r2(screenshot_path, image_key)

        # 生成缩略图
        thumnbail = oss.generate_thumbnail_image(url, image_key)
        
        return {
            "screenshot": screenshot,
            "thumbnail": thumnbail
        }

    async def collect_website_info_v2(self, playwright, url):
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        await page.goto(url)
        # 获取网页的内容
        content = await page.content()
        
        # 提取网站数据
        site_data = self.get_website_data(content, url)
        
        # 获取网站截图
        screenshot = await self.capture_screenshot(page, url)
        
        # 将数据写入mongodb
        collect_data = {
            **site_data,
            **screenshot
        }
        
        collect_data["url"] = url
        
        await browser.close()
        
        return collect_data