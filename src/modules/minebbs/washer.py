import re

from bs4 import BeautifulSoup

from .grabber import grab_post_lists, request_with_header

# --- #

def extract_detailed_content(html_content):
    soup = BeautifulSoup(html_content, "html.parser")

    # 查找主要内容容器
    message_body = soup.find("article", class_="message-body")

    if not message_body:
        return "未找到正文内容"

    # 提取各个部分
    content_parts = []

    # 提取标题和简介
    header = message_body.find("div", style=lambda x: x and "text-align:center" in x)
    if header:
        content_parts.append("标题部分:")
        content_parts.append(header.get_text(strip=True))
        content_parts.append("")

    # 提取主要内容段落
    paragraphs = message_body.find_all("div", class_="bbWrapper")
    for i, para in enumerate(paragraphs):
        text = para.get_text(strip=True)
        if text and len(text) > 10:  # 过滤掉太短的文本
            content_parts.append(f"段落 {i + 1}:")
            content_parts.append(text)
            content_parts.append("")

    return "\n".join(content_parts)


# 提取纯文本版本（修改后的版本）
def extract_clean_text(html_content):
    soup = BeautifulSoup(html_content, "html.parser")

    # 找到文章主体
    message_body = soup.find("article", class_="message-body")

    if not message_body:
        return "未找到正文内容"

    # 移除脚本和样式标签
    for script in message_body(["script", "style"]):
        script.decompose()

    # 提取图片并创建占位符
    image_counter = 1
    image_placeholders = {}

    # 查找所有图片
    img_tags = message_body.find_all("img")
    for img in img_tags:
        src = img.get("data-src") or img.get("src")
        if src and not src.startswith("data:"):
            # 创建占位符
            placeholder = f"%(img{image_counter})s"
            image_placeholders[placeholder] = src
            # 替换图片为占位符文本
            img.replace_with(f" [{placeholder}] ")
            image_counter += 1

    # 获取纯文本
    text = message_body.get_text()

    # 清理文本
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = "\n".join(chunk for chunk in chunks if chunk)

    return text, image_placeholders


def extract_main_content(html_content):
    soup = BeautifulSoup(html_content, "html.parser")

    # 查找包含文章内容的区域
    # 根据HTML结构，主要内容在message-body类中
    message_body = soup.find("article", class_="message-body")

    if not message_body:
        return "未找到正文内容"

    # 提取文本内容，清理多余的空格和换行
    content = message_body.get_text(separator="\n", strip=True)

    # 进一步清理：移除过多的空行
    content = re.sub(r"\n\s*\n", "\n\n", content)
    content = re.findall(r"\|([^|]+)\|", content)[0]

    return content


def clean_extracted_text(text):
    # 按行分割文本
    lines = text.split("\n")
    cleaned_lines = []

    # 标记是否已经开始正文内容
    content_started = False

    for line in lines:
        line = line.strip()

        # 跳过开头的非正文内容
        if not content_started:
            if "协议" in line or "DEEP DIVES" in line:
                continue
            if line:
                content_started = True

        # 跳过结尾的非正文内容
        if "【本文排版借助了：SPXXMB 用户脚本 v3.2.5】" in line:
            break
        if "Powered by SPXXMB 3.2.5 with love" in line:
            break

        # 处理翻译信息行，提取所需信息
        if "译自" in line:
            # 提取作者、日期和标题
            author = extract_pattern(line, r"译自([^0-9]+)")
            date = extract_pattern(line, r"(\d{4} 年 \d{1,2} 月 \d{1,2} 日)")
            title = extract_pattern(line, r"发布的 (.+)】")

            # 重新构建该行
            if author and date and title:
                line = f"{author} {date} {title}"

        # 添加有效的正文行
        if line and content_started:
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


def extract_pattern(text, pattern):
    """从文本中提取匹配模式的内容"""
    match = re.search(pattern, text)
    return match.group(1) if match else None


def extract_article_images(html_content):
    """
    专门提取文章正文中的图片（更精确的提取）
    """
    soup = BeautifulSoup(html_content, "html.parser")
    image_urls = []

    # 找到文章正文区域
    article_body = soup.find("article", class_="message-body")
    if not article_body:
        # 如果没有找到特定的文章区域，则在整个页面中查找
        article_body = soup

    # 在正文区域查找图片
    # 1. 查找带有特定类的图片容器
    image_wrappers = article_body.find_all("div", class_="bbImageWrapper")
    for wrapper in image_wrappers:
        img = wrapper.find("img")
        if img:
            src = img.get("data-src") or img.get("src")
            if src and not src.startswith("data:"):
                image_urls.append(src)

    # 2. 查找所有图片标签（备用方法）
    if not image_urls:
        img_tags = article_body.find_all("img")
        for img in img_tags:
            src = img.get("data-src") or img.get("src")
            if src and not src.startswith("data:"):
                image_urls.append(src)

    # 去掉作者头像
    for url in image_urls:
        if "mojavatar" in url.lower():
            image_urls.remove(url)

    # 去重
    return list(set(image_urls))