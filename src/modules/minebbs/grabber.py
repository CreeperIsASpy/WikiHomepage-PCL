"""AI 写的博文提取脚本"""

from datetime import datetime

import requests
import cloudscraper
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Referer": "https://minebbs.com/",
}

cf_scraper = cloudscraper.create_scraper()


def request_with_header_origin(url, **kwargs) -> requests.Response:
    """发送带有浏览器请求头的请求"""
    response = cf_scraper.get(url, **kwargs)
    return response


def request_with_header(url) -> str:
    """发送带有浏览器请求头的请求，返回文本"""
    response = request_with_header_origin(url)
    return response.text


def extract_blog_posts(html_content):
    """
    从HTML内容中提取博文信息并按时间排序
    """
    soup = BeautifulSoup(html_content, "html.parser")

    # 查找所有博文条目
    blog_posts = []

    # 查找所有包含博文的结构项
    struct_items = soup.find_all("div", class_="structItem")

    for item in struct_items:
        try:
            post_data = {}

            # 提取标题
            title_element = item.find("div", class_="structItem-title")
            if title_element:
                # 找到所有的链接，但排除标签链接
                all_links = title_element.find_all("a")
                title_link = None

                for link in all_links:
                    # 标签链接通常有labelLink类或者包含label元素
                    if "labelLink" not in link.get("class", []) and not link.find(
                        "span", class_="label"
                    ):
                        title_link = link
                        break

                if title_link:
                    title_text = title_link.get_text(strip=True)
                    post_data["title"] = title_text
                    post_data["url"] = title_link.get("href", "")

            # 提取标签信息 - 从标题区域提取
            if title_element:
                labels = []
                label_elements = title_element.find_all("span", class_="label")
                for label in label_elements:
                    labels.append(
                        {
                            "text": label.get_text(strip=True),
                            "class": label.get("class", []),
                        }
                    )
                post_data["labels"] = labels

            # 提取作者信息
            author_element = item.find("a", class_="username")
            if author_element:
                post_data["author"] = author_element.get_text(strip=True)

            # 提取发布时间
            start_date_element = item.find("li", class_="structItem-startDate")
            if start_date_element:
                time_element = start_date_element.find("time")
                if time_element:
                    post_data["publish_time_display"] = time_element.get_text(
                        strip=True
                    )

            # 只有当成功提取到标题时才添加到结果中
            if "title" in post_data and post_data["title"]:
                blog_posts.append(post_data)

        except Exception as e:
            print(f"处理博文时出错: {e}")
            continue

    return blog_posts


def sort_posts_by_time(posts, time_field="publish_time"):
    """
    按时间对博文进行排序
    """

    def get_sort_key(post):
        time_str = post.get(time_field, "")
        if not time_str:
            return datetime.min
        try:
            # 处理时区信息
            if "+" in time_str:
                return datetime.fromisoformat(time_str)
            else:
                # 如果没有时区信息，假设是本地时间
                return datetime.fromisoformat(time_str)
        except ValueError:
            return datetime.min

    return sorted(posts, key=get_sort_key, reverse=True)


def clean_post_data(posts):
    """
    清理和格式化博文数据
    """
    cleaned_posts = []
    for post in posts:
        cleaned_post = {
            "title": post.get("title", ""),
            "author": post.get("author", "未知作者"),
            "publish_time_display": post.get("publish_time_display", ""),
            "url": (
                "https://www.minebbs.com" + post.get("url", "")
                if post.get("url", "").startswith("/")
                else post.get("url", "")
            ),
            "labels": [label["text"] for label in post.get("labels", [])],
        }
        cleaned_posts.append(cleaned_post)

    return cleaned_posts


def filter_posts_by_title(posts, keyword):
    """
    根据标题关键词筛选博文

    Args:
        posts: 博文列表
        keyword: 要筛选的关键词

    Returns:
        包含关键词的博文列表
    """
    filtered_posts = []
    for post in posts:
        if keyword.lower() in post.get("title", "").lower():
            filtered_posts.append(post)
    return filtered_posts


def grab_post_lists(NEWS_LIST_URL: str) -> tuple[list, bool]:
    """
    主函数：提取、清理并排序博文数据
    """
    req = request_with_header_origin(NEWS_LIST_URL)

    # 确认是否有内容
    if req.status_code != 200:
        print(f"[DEBUG] Debugging Information")
        print(f"请求失败")
        print(f"URL：{NEWS_LIST_URL}")
        print(f"状态码：{req.status_code}")
        print(f"响应头部：{req.headers}")
        return (None, False)

    # 提取博文数据
    posts = extract_blog_posts(req.text)

    # 按发布时间排序
    sorted_posts = sort_posts_by_time(posts)

    # 清理数据
    cleaned_posts = clean_post_data(sorted_posts)

    # 过滤出含有 MINECRAFT | DEEP DIVES 字样的博文
    filtered_posts = filter_posts_by_title(cleaned_posts, "DEEP DIVES")

    return (filtered_posts, True)


def get_last_page_number():
    url = "https://www.minebbs.com/forums/news/page-9999999999"
    r = request_with_header_origin(url, allow_redirects=False)
    final_url = r.headers.get("Location", "")
    # 提取页码
    if "page-" in final_url:
        return int(final_url.split("page-")[-1].rstrip("/"))
    else:
        return 1  # 只有一页时不会带 page-


def grab_all():
    all_posts = []

    last_page = get_last_page_number()
    for count in range(1, last_page + 1):
        filtered_posts, should_continue = grab_post_lists(
            f"https://www.minebbs.com/forums/news/{f'page-{count}' if count > 1 else ''}"
        )
        if filtered_posts:
            all_posts.extend(filtered_posts)
        if not should_continue:
            raise Exception("意外获取到非 200 返回请求")

    return sort_posts_by_time(all_posts)
