import datetime
import hashlib
import re
import time
import json
import struct
from typing import Optional, Dict, Tuple, List

import requests
from bs4 import BeautifulSoup, Tag

from ...utils.get_template import get_template


class WikiXamlGenerator:
    """
    一个用于从中文Minecraft Wiki获取数据并生成PCL2主页所需XAML文件的类。

    该类封装了所有网络请求、HTML解析、数据提取和XAML模板填充的逻辑。

    使用方法:
        generator = WikiXamlGenerator()
        generator.run()
    """

    VERSION = "2.0"
    WIKI_API_URL = "https://zh.minecraft.wiki/api.php"
    NEWS_API_URL = "https://news.bugjump.net/apis/versions/latest-card"
    BASE_WIKI_URL = "https://zh.minecraft.wiki"
    FEATURED_ARTICLE_SELECTOR = (
        "div.mp-inline-sections > div.mp-left > div:nth-child(5)"
    )
    FEATURED_IMAGE_SELECTOR = "div.mp-featured-img img"

    def __init__(self, template_path: str = "", output_path: str = "", ini_path: str = ""):
        """
        初始化生成器。

        Args:
            template_path (str): f-string模板文件的路径。
            output_path (str): 生成的XAML文件的输出路径。
            ini_path (str): 用于存储版本信息的ini文件的路径。
        """
        self.req_headers = {"User-Agent": f"PCL2MagazineHomepageBot/{self.VERSION}"}
        self.template_path = template_path or "main.fstring.xaml"
        self.output_path = output_path or "output/Custom.xaml"
        self.ini_path = ini_path or "output/Custom.xaml.ini"
        self.dom_content: Optional[BeautifulSoup] = None

    @staticmethod
    def _get_request(url: str, **kwargs) -> Optional[str]:
        """
        发起一个通用的GET请求并返回响应文本。

        Args:
            url (str): 请求的URL。
            **kwargs: 传递给 requests.get 的其他参数。

        Returns:
            Optional[str]: 成功则返回响应文本，否则返回None。
        """
        try:
            response = requests.get(url, **kwargs)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] 请求失败: {e}")
            return None

    def _fetch_and_parse_wiki_data(self) -> None:
        """
        从Wiki API获取主页HTML并使用BeautifulSoup进行解析。

        如果请求失败，将引发异常。
        """
        params = {"action": "parse", "format": "json", "page": "Minecraft_Wiki"}
        print("正在从 Minecraft Wiki API 获取数据...")
        response_text = self._get_request(
            self.WIKI_API_URL, params=params, headers=self.req_headers, timeout=10
        )
        if not response_text:
            raise ConnectionError("无法从 Wiki API 获取响应，程序中止。")

        html_content = json.loads(response_text)["parse"]["text"]["*"]
        self.dom_content = BeautifulSoup(html_content, "html.parser")
        print("Wiki 数据获取并解析成功。")

    @staticmethod
    def _fetch_news_card() -> str:
        """
        从新闻API获取最新的新闻卡片XAML。

        如果API请求失败，会返回一个包含错误状态码的占位卡片。
        """
        print("正在请求新闻主页 API...")
        try:
            response = requests.get(WikiXamlGenerator.NEWS_API_URL, timeout=10)
            print(
                f"新闻 API 状态码: {response.status_code}，请求{'成功' if response.ok else '失败'}！"
            )
            if response.ok:
                return response.text
            else:
                # 如果请求失败，返回一个错误提示卡片
                return get_template("newsapi_error").format()
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] 新闻 API 请求异常: {e}")
            return get_template("newsapi_error").format()

    @staticmethod
    def _extract_links_from_html(html_content: str) -> Dict[str, str]:
        """
        从一段HTML文本中提取所有链接的文本和URL。

        Args:
            html_content (str): 包含HTML链接的字符串。

        Returns:
            Dict[str, str]: 一个字典，键是链接文本，值是完整的URL。
        """
        links = {}
        # 正则表达式查找所有<a>标签的href和title属性
        for match in re.finditer(
            r'<a href="(?P<url>.*?)" title="(?P<text>.*?)"', html_content
        ):
            links[match.group("text")] = WikiXamlGenerator.BASE_WIKI_URL + match.group(
                "url"
            )
        return links

    @staticmethod
    def _format_link_as_xaml(link_text: str, link_url: str) -> str:
        """
        将链接文本和URL格式化为XAML的MyTextButton字符串。

        Args:
            link_text (str): 链接的显示文本。
            link_url (str): 链接的目标URL。

        Returns:
            str: XAML格式的字符串。
        """
        return (
            f'<Underline><local:MyTextButton EventType="打开网页" '
            f'EventData="{link_url}" Margin="0,0,0,-8">{link_text}</local:MyTextButton></Underline>'
        )

    def _parse_featured_article_to_xaml(self, article_element: Tag) -> List[str]:
        """
        解析特色条目HTML元素，将其转换为带超链接的XAML格式字符串列表。

        此方法重构了原有的 `gr` 函数，采用了更清晰的逻辑来处理链接替换。
        它通过将句子分解为文本和XAML片段的列表来操作，以防止出现无效的嵌套链接。

        Args:
            article_element (Tag): 代表特色条目容器的BeautifulSoup Tag对象。

        Returns:
            List[str]: 一个字符串列表，每个字符串都是一个XAML <ListItem>。
        """
        # 步骤 1: 提取并清理纯文本，分割成句子。
        raw_text = article_element.text
        cleaned_text = raw_text.lstrip("\n特色条目").strip()
        sentences = [s.strip() for s in cleaned_text.split("。") if s.strip()]

        # 步骤 2: 从原始HTML中获取所有超链接。
        html_content = str(article_element)
        links_map = self._extract_links_from_html(html_content)

        # 步骤 3: 按链接文本长度降序排序，这是防止嵌套错误的关键。
        # 确保优先替换长词组（如“铜箱子”）而不是其中的短词（如“箱子”）。
        sorted_links = sorted(
            links_map.items(), key=lambda item: len(item[0]), reverse=True
        )

        processed_xaml_items = []
        for sentence in sentences:
            text_with_period = sentence + "。"

            # 步骤 4: 使用“片段列表”的策略来替换链接，避免嵌套错误。
            # 初始时，整个句子是一个“文本”片段。
            parts = [{"type": "text", "content": text_with_period}]

            # 迭代所有排序后的链接
            for link_text, link_url in sorted_links:
                new_parts = []
                xaml_hyperlink = self._format_link_as_xaml(link_text, link_url)

                # 遍历当前所有的片段
                for part in parts:
                    # 只对“文本”类型的片段进行操作
                    if part["type"] == "text":
                        # 按链接文本分割该片段
                        sub_parts = part["content"].split(link_text)

                        # 将分割后的文本和新的XAML片段交错地添加回新列表
                        for i, sub_part_content in enumerate(sub_parts):
                            if sub_part_content:
                                new_parts.append(
                                    {"type": "text", "content": sub_part_content}
                                )
                            if i < len(sub_parts) - 1:
                                new_parts.append(
                                    {"type": "xaml", "content": xaml_hyperlink}
                                )
                    else:
                        # 如果已经是XAML片段，则原样保留
                        new_parts.append(part)

                # 更新片段列表以进行下一轮链接的替换
                parts = new_parts

            # 步骤 5: 将所有片段的内容连接起来，形成最终的段落内容。
            final_content = "".join(part["content"] for part in parts)

            xaml_item = (
                f'<ListItem><Paragraph Foreground="{{DynamicResource ColorBrush1}}">'
                f"{final_content}</Paragraph></ListItem>"
            )
            processed_xaml_items.append(xaml_item)

        # 去掉最后一句无用的“阅读更多”。
        if processed_xaml_items:
            processed_xaml_items.pop()

        return processed_xaml_items

    def _get_featured_image_url(self) -> str:
        """从解析后的HTML中获取特色条目的图片URL。"""
        if not self.dom_content:
            return ""
        img_tag = self.dom_content.select_one(self.FEATURED_IMAGE_SELECTOR)
        if img_tag and img_tag.get("src"):
            img_src = self.BASE_WIKI_URL + img_tag.get("src")
            # 转义URL中的 '&' 符号以适应XML/XAML格式。
            return img_src.replace("&", "&amp;")
        return ""

    def _generate_version_id(self) -> str:
        """生成一个基于日期和时间戳哈希的版本ID，并写入ini文件。"""
        dt = datetime.datetime.now().strftime("%y%m%d")
        hsh = hashlib.md5(struct.pack("<f", time.time())).hexdigest()
        vid = f"{dt}:{hsh[:7]}"
        try:
            with open(self.ini_path, "w") as f:
                f.write(f"{dt}:{hsh}")
        except IOError as e:
            print(f"[ERROR] 无法写入版本文件 '{self.ini_path}': {e}")
        return vid

    def _get_featured_article_title_and_link(
        self, article_element: Tag
    ) -> Tuple[str, str]:
        """
        从特色条目元素中获取主标题和主链接。

        Args:
            article_element (Tag): 特色条目的BeautifulSoup Tag对象。

        Returns:
            Tuple[str, str]: (标题, 链接URL)
        """
        links = self._extract_links_from_html(str(article_element))
        if links:
            # 通常第一个链接是文章的主题链接
            first_item = next(iter(links.items()))
            return first_item[0], first_item[1]
        return "未知主题", self.BASE_WIKI_URL

    def run(self, latest_deepdives: str, previous_deepdives: str):
        """
        执行整个流程：获取数据，解析，并生成最终的XAML文件。
        """
        try:
            # 步骤 1: 获取并解析Wiki数据
            self._fetch_and_parse_wiki_data()
            if not self.dom_content:
                return

            # 步骤 2: 提取所有需要填充到模板中的数据
            now = datetime.datetime.now()
            featured_article_element = self.dom_content.select_one(
                self.FEATURED_ARTICLE_SELECTOR
            )

            if not featured_article_element:
                print("[ERROR] 无法在 HTML 中找到特色条目元素，请检查选择器。")
                return

            print("正在解析特色条目...")
            title, main_link = self._get_featured_article_title_and_link(
                featured_article_element
            )
            parsed_items = self._parse_featured_article_to_xaml(
                featured_article_element
            )

            # 步骤 3: 读取模板并填充内容
            print("正在读取模板文件...")
            template_content = get_template(self.template_path)
            final_output = template_content.format(
                WikiPage = main_link,
                version = self._generate_version_id(),
                img = self._get_featured_image_url(),
                topic = title,
                intro = parsed_items[0] if len(parsed_items) > 0 else "",
                intro_2 = parsed_items[1] if len(parsed_items) > 1 else "",
                body = "\n".join(parsed_items[2:]) if len(parsed_items) > 2 else "",
                datetime = f'最后更新：{now.strftime("%Y-%m-%d")}',
                NewsCard = self._fetch_news_card(),
                Latest_DeepDives = latest_deepdives,
                Previous_DeepDives = previous_deepdives,
            )

            # 步骤 4: 将结果写入输出文件
            with open(self.output_path, "w", encoding="UTF-8") as f:
                f.write(final_output)

            print(f"成功生成XAML文件: {self.output_path}")

        except Exception as e:
            print(f"[FATAL] 发生严重错误: {e}")
