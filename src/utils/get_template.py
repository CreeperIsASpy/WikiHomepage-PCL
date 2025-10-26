from pathlib import Path


def get_template(template_name: str) -> str:
    """
    获取指定名称的模板字符串。

    Args:
        template_name (str): 模板文件的名称（包含扩展名）。

    Returns:
        str: 模板字符串。
    """

    fp = Path(__file__).parent.parent.parent / "assets" / "templates" / template_name

    try:
        with open(fp, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"[ERROR] 模板文件 {template_name} 不存在")
        return ""
