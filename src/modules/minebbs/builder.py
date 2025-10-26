import re
from datetime import datetime

from .grabber import request_with_header
from .washer import extract_clean_text, clean_extracted_text
from ...utils.get_template import get_template


def convert_text_to_xaml(content_part, image_map) -> str:
    """
    将特定格式的 Minecraft 文章文本转换为 PCL 使用的 XAML 格式。

    Args:
        content_part: 包含文章内容的字符串。
        image_map: 包含图片映射的字典。

    Returns:
        转换后的 XAML 格式字符串。
    """

    # --- 1. 分离内容与元数据 ---
    try:
        content_lines = content_part.strip().split("\n")
    except (ValueError, SyntaxError) as e:
        raise ValueError(f"无法解析输入文本的结构或图片映射: {e}")

    for image_key, image_url in image_map.copy().items():
        if "mojavatar" in image_url.lower():
            del image_map[image_key]
            for line in content_lines[:]:
                if image_key in line:
                    content_lines.remove(line)

    # --- 2. 解析元数据 ---
    # 通常元数据在文章内容的最后一行
    author, source_date_str, eng_title, ch_title = "", "", "", ""
    if content_lines:
        meta_line = content_lines[-1]
        # 匹配 "作者 日期 英文标题"
        meta_match = re.match(
            r"^\s*(?P<author>.*?)\s+(?P<date>\d{4}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日)\s+(?P<title>.*)",
            meta_line,
        )
        if meta_match:
            author = meta_match.group("author").strip()
            # 格式化日期
            date_obj = datetime.strptime(
                meta_match.group("date").replace(" ", ""), "%Y年%m月%d日"
            )
            source_date_str = date_obj.strftime("%Y-%m-%d")
            # 英文标题可能在同一行，也可能在文章开头
            if not eng_title:
                eng_title = meta_match.group("title").strip()
            content_lines = content_lines[:-1]  # 从内容中移除元数据行

    # --- 3. 构建 XAML 主体 ---
    xaml_parts = []

    # 查找文章的各级标题
    # 跳过开头的图片占位符和空行
    first_content_line_index = 0
    for i, line in enumerate(content_lines):
        if line.strip() and not line.strip().startswith("[%("):
            first_content_line_index = i
            break

    # 提取标题
    try:
        sub_title_eng = content_lines[first_content_line_index].strip()
        main_title_eng = content_lines[first_content_line_index + 1].strip()
        main_title_ch = content_lines[first_content_line_index + 2].strip()
        sub_title_eng_2 = content_lines[first_content_line_index + 3].strip()
        sub_title_ch_2 = content_lines[first_content_line_index + 4].strip()

        if not eng_title:
            eng_title = main_title_eng
        if not ch_title:
            ch_title = main_title_ch

        # 添加标题段落
        xaml_parts.append(
            f'<Paragraph Style="{{StaticResource H7}}">{sub_title_eng}</Paragraph>'
        )
        xaml_parts.append(
            f'<Paragraph Style="{{StaticResource H2}}">{main_title_eng}</Paragraph>'
        )
        xaml_parts.append(
            f'<Paragraph Style="{{StaticResource H2}}">{main_title_ch}</Paragraph>'
        )
        xaml_parts.append(
            f'<Paragraph Style="{{StaticResource H7}}">{sub_title_eng_2}</Paragraph>'
        )
        xaml_parts.append(
            f'<Paragraph Style="{{StaticResource H5}}">{sub_title_ch_2}</Paragraph>'
        )

        # 更新循环起始位置
        content_start_index = first_content_line_index + 5
    except IndexError:
        # 如果标题结构不匹配，则正常处理
        content_start_index = first_content_line_index
        ch_title = "未知标题"  # 设置一个默认值

    # --- 4. 迭代处理文章内容 ---
    i = content_start_index
    while i < len(content_lines):
        line = content_lines[i].strip()
        if not line:
            i += 1
            continue

        # 处理图片
        if line.startswith("[%(") and line.endswith(")s]"):
            img_key = line[1:-1]  # 去掉首尾的中括号
            img_url = image_map.get(img_key, "")

            # 检查下一行是否为版权信息
            caption = ""
            if i + 1 < len(content_lines):
                next_line = content_lines[i + 1].strip()
                if next_line.lower().startswith(
                    "image credit:"
                ) or next_line.startswith("图片来源："):
                    # 优先使用中文格式
                    caption_text = (
                        next_line.replace("Image credit:", "图片来源：")
                        .replace("//", "/")
                        .strip()
                    )
                    caption = f'<TextBlock Text="{caption_text}" Style="{{StaticResource imgTitle}}" />'
                    i += 1  # 跳过版权行
                    # 再检查下一行是否是中文版权
                    if i + 1 < len(content_lines):
                        next_next_line = content_lines[i + 1].strip()
                        if next_next_line.startswith("图片来源："):
                            i += 1

            xaml_parts.append(
                f"""<BlockUIContainer>
<StackPanel Margin="0,4,0,4">
<Image Style="{{StaticResource InnerImage}}" Source="{img_url}"/>{caption}
</StackPanel> 
</BlockUIContainer>"""
            )
            i += 1
        # 处理成对的中英文段落
        else:
            eng_para = line
            ch_para = ""
            if i + 1 < len(content_lines):
                ch_para = content_lines[i + 1].strip()
                # 假设中文段落不以'['开头，也不是常见的英文句子开头
                if (
                    ch_para
                    and not ch_para.startswith("[")
                    and not re.match(r"^[A-Z]", ch_para)
                ):
                    xaml_parts.append(
                        f'<Paragraph Margin="0,0" FontSize="12" Foreground="silver">{eng_para}</Paragraph>'
                    )
                    xaml_parts.append(
                        f'<Paragraph Margin="0,0" Foreground="black">{ch_para}</Paragraph>'
                    )
                    i += 2
                else:
                    # 只有单行英文
                    xaml_parts.append(
                        f'<Paragraph Margin="0,0" FontSize="12" Foreground="silver">{eng_para}</Paragraph>'
                    )
                    i += 1
            else:
                # 只有最后一行英文
                xaml_parts.append(
                    f'<Paragraph Margin="0,0" FontSize="12" Foreground="silver">{eng_para}</Paragraph>'
                )
                i += 1

    flow_document_content = "\n".join(xaml_parts)

    # --- 5. 准备最终的 XAML 模板并填充 ---
    # 获取图片
    header_img_url = image_map.get("%(img1)s", "")

    # 获取当前日期
    last_update_str = datetime.now().strftime("%Y-%m-%d")

    # 构造原文链接
    original_url = f"https://www.minecraft.net/zh-hans/article/{eng_title.lower().replace(':', '').replace(' ', '-')}"

    final_xaml = get_template("bbsmain.fstring.xaml").format(
        header_img_url=header_img_url,
        source_date_str=source_date_str,
        last_update_str=last_update_str,
        original_url=original_url,
        flow_document_content=flow_document_content,
        ch_title=ch_title,
        sub_title_eng_2=sub_title_eng_2,
        sub_title_ch_2=sub_title_ch_2,
        main_title_ch=main_title_ch,
        author=author,
    )

    return final_xaml


def run(post) -> str:
    """
    主函数：将博文转换为 PCL XAML 格式
    """
    content = request_with_header(post.get("url"))
    clean_text, image_dict = extract_clean_text(content)
    return convert_text_to_xaml(clean_extracted_text(clean_text), image_dict)
