from pathlib import Path

from src.modules.wiki.builder import WikiXamlGenerator
from src.modules.minebbs.grabber import grab_all
from src.modules.minebbs.builder import run
from src.utils.get_template import get_template

HistoryOutput = Path(__file__).parent / "output" / "history"

if __name__ == "__main__":
    HistoryOutput.mkdir(parents=True, exist_ok=True)

    latest_post = ""
    previous_post = ""

    all_posts = grab_all()

    for index, post in enumerate(all_posts):
        built_content = run(post)

        # 保存为 XAML 文件和 JSON 文件
        filename = (
            post.get("url").split("/")[-2].replace(".", "-")
            or "minecraft-net-deep-dives-unknown"
        )
        with open(
            HistoryOutput / (filename + ".xaml"), "w", encoding="utf-8"
        ) as xamlFile:
            xamlFile.write(built_content)
        with open(
            HistoryOutput / (filename + ".json"), "w", encoding="utf-8"
        ) as jsonFile:
            jsonFile.write(built_content)

        # 制作主页入口点
        template = get_template("deepdives_link.fstring.xaml")
        title = (
            (post.get("title").strip() + f"（{'最新' if index==0 else '历史'}博文）",)[
                0
            ]
            .split("]")[-1]
            .replace(":", "：")
            .replace(": ", "：")
            .strip()
        )
        _date = post.get("publish_time_display")
        _author = post.get("author")

        built_template = template.format(
            lamp_status="On" if index == 0 else "Off",
            title=title,
            info=f"更新于 {_date}，由 {_author} 翻译。",
            json_name=filename,
        )

        if index == 0:
            latest_post = built_template
        else:
            previous_post += built_template + "\n"

    generator = WikiXamlGenerator()
    generator.run(latest_post, previous_post)
