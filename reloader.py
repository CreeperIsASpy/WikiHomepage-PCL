import datetime
import hashlib
import re
import time
import json
import struct
from typing import Optional, Dict, Union

import requests
from bs4 import BeautifulSoup

VERSION = "0.0"
headers = {
    'User-Agent':
        f'PCL2 Magazine Homepage Bot/{VERSION}',
}

global obj


def get_text(
        url: str,
        params: Optional[Dict[str, Union[str, int]]] = None,
        headers: Optional[Dict[str, str]] = headers,
        timeout: float = 10.0,
        allow_redirects: bool = True,
        encoding: Optional[str] = None
) -> Optional[str]:
    """
    发起通用 GET 请求并返回响应文本。

    此函数封装 requests.get，用于向指定 URL 发送 GET 请求。支持传入查询参数、请求头、自定义编码、
    是否跟随重定向等设置。请求成功时返回响应文本；若出现异常则返回 None。

    参数:
        url (str): 请求地址。
        params (dict[str, str | int], 可选): URL 查询参数。
        headers (dict[str, str], 可选): 请求头信息。默认为 default_header。
        timeout (float): 请求超时时间（单位：秒），默认 10.0。
        allow_redirects (bool): 是否允许自动重定向，默认 True。
        encoding (str, 可选): 手动指定响应的编码格式（如 'utf-8'、'gbk' 等）。

    返回:
        str | None: 响应内容字符串；若请求失败则返回 None。

    异常:
        无抛出；若请求失败，会捕获异常并打印错误信息。
    """
    try:
        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=timeout,
            allow_redirects=allow_redirects
        )
        response.raise_for_status()  # 根据状态码抛出错误
        if encoding:
            response.encoding = encoding  # 手动设置编码（如 'utf-8'、'gbk'）
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] 请求失败: {e}")
        return None


def get_wiki_data():
    """
    获取中文 Minecraft Wiki 的页面解析数据。

    此函数使用 get_text() 向 zh.minecraft.wiki 的 API 发起请求，获取 "Minecraft_Wiki" 页面
    的解析内容（以 JSON 格式返回）。若请求失败，则抛出异常终止程序。

    参数:
        无。

    返回:
        dict: 从 Wiki API 返回的解析后的 JSON 数据。

    异常:
        Exception: 若请求失败（无响应），抛出异常并中止。
    """
    resp: str | None = get_text("https://zh.minecraft.wiki/api.php", {
        "action": "parse",
        "format": "json",
        "page": "Minecraft_Wiki"
    })
    if not resp:
        raise Exception("No response from https://zh.minecraft.wiki/w/api.php, ABORTED!")
    html = json.loads(resp)["parse"]["text"]["*"]

    global obj
    obj = BeautifulSoup(html, 'html.parser')

    return html


def while_delete(del_txts, txt, replacement=''):
    for del_txt in del_txts:
        while del_txt in txt:
            txt = txt.replace(del_txt, replacement)
    return txt


def get_news_card():
    resp = str(requests.get("https://news.bugjump.net/apis/versions/latest-card").text)
    return resp


def get_link_txt(txt):
    raw_links = re.findall(r'<a href=".*?" title=".*?"', txt, re.S)
    links = {}
    for link in raw_links:
        key = re.findall(r'title="(.*?)"', link, re.M)[0]
        ref = re.findall(r'href="(.*?)"', link, re.M)[0]
        links[key] = "https://zh.minecraft.wiki" + ref
    return links


def link_to_xaml(lk):
    xaml = f'''<Underline><local:MyTextButton EventType="打开网页" \
EventData="{lk[1]}" Margin="0,0,0,-8">{lk[0]}</local:MyTextButton></Underline>'''
    return xaml


def gr():
    origin = str(obj.select_one("div.mp-inline-sections > div.mp-left > div:nth-child(5)").text)
    result = origin.lstrip("\n特色条目").strip().split("。")
    result = [i.strip("\n") for i in result]
#   print(result)
    result = [f"<ListItem><Paragraph>{i}。</Paragraph></ListItem>" for i in result]
    
    # 获取原始HTML内容
    html_content = str(obj.select_one("div.mp-inline-sections > div.mp-left > div:nth-child(5)"))
    
    # 提取所有链接
    links = get_link_txt(html_content)
    
    # 按照键的长度降序排序，确保先替换长的复合词
    sorted_links = sorted(links.items(), key=lambda x: len(x[0]), reverse=True)
    
    # 处理每个段落
    for i, item in enumerate(result):
        # 提取段落文本内容（不包含ListItem和Paragraph标签）
        paragraph_text = re.search(r'<ListItem><Paragraph>(.*?)</Paragraph></ListItem>', item)
        if paragraph_text:
            text_content = paragraph_text.group(1)
            
            # 创建一个标记数组，记录哪些位置已经被替换过
            text_length = len(text_content)
            replaced = [False] * text_length
            
            # 对每个链接进行替换，按长度降序处理
            for key, url in sorted_links:
                # 查找所有匹配位置
                start_pos = 0
                while True:
                    pos = text_content.find(key, start_pos)
                    if pos == -1:
                        break
                        
                    # 检查这个位置是否已经被替换过
                    if not any(replaced[pos:pos+len(key)]):
                        # 标记这些位置为已替换
                        for j in range(pos, pos+len(key)):
                            if j < text_length:
                                replaced[j] = True
                                
                        # 替换文本
                        before = text_content[:pos]
                        after = text_content[pos+len(key):]
                        text_content = before + link_to_xaml((key, url)) + after
                        
                        # 更新标记数组以适应新的文本长度
                        new_length = len(text_content)
                        replaced = replaced[:pos] + [True] * len(link_to_xaml((key, url))) + replaced[pos+len(key):]
                        
                    # 移动到下一个可能的位置
                    start_pos = pos + 1
            
            # 重新组装段落
            result[i] = f"<ListItem><Paragraph>{text_content}</Paragraph></ListItem>"
    
    result.pop()
    return result


def gs():
    img_src = 'https://zh.minecraft.wiki' + obj.select_one("div.mp-featured-img img").get('src')
    img_src = re.sub(r'&', '&amp;', img_src)
    return img_src


def get_version():
    dt = datetime.datetime.now().strftime("%y%m%d")
    hsh = hashlib.md5(struct.pack('<f', time.time())).hexdigest()
    vid = f"{dt}:{hsh[:7]}"
    with open("Custom.xaml.ini", 'w') as f:
        f.write(f"{dt}:{hsh}")
    return vid


def get_wiki_page():
    return list(get_link_txt(str(obj.select_one("div.mp-inline-sections > div.mp-left > div:nth-child(5)"))).values())[0]


def get_topic():
    return list(get_link_txt(str(obj.select_one("div.mp-inline-sections > div.mp-left > div:nth-child(5)"))).keys())[0]


def validate_template(template):
    # 查找未转义的独立 % 符号（非占位符）
    standalone_percent = re.findall(r"(?<!%)%(?!\()", template)
    if standalone_percent:
        print(f"发现未转义的 % 符号: {len(standalone_percent)} 处")

    # 查找占位符
    placeholders = re.findall(r"%\((\w+)\)s", template)
    print(f"发现占位符：{len(placeholders)} 处")


def update():
    now = datetime.datetime.now()
    content_text = '''<!-- "The Magazine Homepage for PCL2" made by CreeperIsASpy. Copyright 2025 CreeperIsASpy, all rights reserved. (CC BY-NC-SA 4.0).-->
<!-- 由 仿生猫梦见苦力怕 制作该 "PCL2 杂志主页"。@仿生猫梦见苦力怕 / CreeperIsASpy 版权所有，保留所有权利。（使用CC BY-NC-SA 4.0 授权代码部分内容）。-->

<StackPanel Margin="0,-10,0,0"
xmlns:sys="clr-namespace:System;assembly=mscorlib"
xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
xmlns:local="clr-namespace:PCL;assembly=Plain Craft Launcher 2">
<StackPanel.Resources>
<!--Styles Starts-->
<Style x:Key="TabControlStyle" TargetType="{x:Type TabControl}">
    <Setter Property="Padding" Value="2"/>
    <Setter Property="HorizontalContentAlignment" Value="Center"/>
    <Setter Property="VerticalContentAlignment" Value="Center"/>
    <Setter Property="Background" Value="Transparent"/>
    <Setter Property="BorderBrush" Value="#FFACACAC"/>
    <Setter Property="BorderThickness" Value="0"/>
    <Setter Property="Foreground" Value="{DynamicResource {x:Static SystemColors.ControlTextBrushKey}}"/>
        <Setter Property="Template">
            <Setter.Value>
                <ControlTemplate TargetType="{x:Type TabControl}">
                    <Grid x:Name="templateRoot" ClipToBounds="True" SnapsToDevicePixels="True" KeyboardNavigation.TabNavigation="Local">
                        <Grid.ColumnDefinitions>
                            <ColumnDefinition x:Name="ColumnDefinition0"/>
                            <ColumnDefinition x:Name="ColumnDefinition1" Width="0"/>
                        </Grid.ColumnDefinitions>
                        <Grid.RowDefinitions>
                            <RowDefinition x:Name="RowDefinition0" Height="Auto"/>
                            <RowDefinition x:Name="RowDefinition1" Height="*"/>
                        </Grid.RowDefinitions>
                    <UniformGrid x:Name="HeaderPanel" Rows="1" Background="Transparent" Grid.Column="0" IsItemsHost="True" Margin="0" Grid.Row="0" KeyboardNavigation.TabIndex="1" Panel.ZIndex="1"/>
                    <Line X1="0" X2="{Binding ActualWidth, RelativeSource={RelativeSource Self}}" Stroke="White" StrokeThickness="0.1" VerticalAlignment="Bottom" Margin="0 0 0 1" SnapsToDevicePixels="True"/>
                    <Border x:Name="ContentPanel" BorderBrush="{DynamicResource ColorBrush2}" BorderThickness="0" Background="Transparent" Grid.Column="0" KeyboardNavigation.DirectionalNavigation="Contained" Grid.Row="1" KeyboardNavigation.TabIndex="2" KeyboardNavigation.TabNavigation="Local" CornerRadius="7">
                        <ContentPresenter x:Name="PART_SelectedContentHost" ContentTemplate="{TemplateBinding SelectedContentTemplate}" Content="{TemplateBinding SelectedContent}" ContentStringFormat="{TemplateBinding SelectedContentStringFormat}" ContentSource="SelectedContent" Margin="0" SnapsToDevicePixels="{TemplateBinding SnapsToDevicePixels}"/>
                    </Border>
                </Grid>
                <ControlTemplate.Triggers>
                    <Trigger Property="TabStripPlacement" Value="Bottom">
                        <Setter Property="Grid.Row" TargetName="HeaderPanel" Value="1"/>
                        <Setter Property="Grid.Row" TargetName="ContentPanel" Value="0"/>
                        <Setter Property="Height" TargetName="RowDefinition0" Value="*"/>
                        <Setter Property="Height" TargetName="RowDefinition1" Value="Auto"/>
                    </Trigger>
                    <Trigger Property="TabStripPlacement" Value="Left">
                        <Setter Property="Grid.Row" TargetName="HeaderPanel" Value="0"/>
                        <Setter Property="Grid.Row" TargetName="ContentPanel" Value="0"/>
                        <Setter Property="Grid.Column" TargetName="HeaderPanel" Value="0"/>
                        <Setter Property="Grid.Column" TargetName="ContentPanel" Value="1"/>
                        <Setter Property="Width" TargetName="ColumnDefinition0" Value="Auto"/>
                        <Setter Property="Width" TargetName="ColumnDefinition1" Value="*"/>
                        <Setter Property="Height" TargetName="RowDefinition0" Value="*"/>
                        <Setter Property="Height" TargetName="RowDefinition1" Value="0"/>
                    </Trigger>
                    <Trigger Property="TabStripPlacement" Value="Right">
                        <Setter Property="Grid.Row" TargetName="HeaderPanel" Value="0"/>
                        <Setter Property="Grid.Row" TargetName="ContentPanel" Value="0"/>
                        <Setter Property="Grid.Column" TargetName="HeaderPanel" Value="1"/>
                        <Setter Property="Grid.Column" TargetName="ContentPanel" Value="0"/>
                        <Setter Property="Width" TargetName="ColumnDefinition0" Value="*"/>
                        <Setter Property="Width" TargetName="ColumnDefinition1" Value="Auto"/>
                        <Setter Property="Height" TargetName="RowDefinition0" Value="*"/>
                        <Setter Property="Height" TargetName="RowDefinition1" Value="0"/>
                    </Trigger>
                    <Trigger Property="IsEnabled" Value="False">
                        <Setter Property="TextElement.Foreground" TargetName="templateRoot" Value="{DynamicResource {x:Static SystemColors.GrayTextBrushKey}}"/>
                    </Trigger>
                </ControlTemplate.Triggers>
            </ControlTemplate>
        </Setter.Value>
    </Setter>
</Style>
<Style x:Key="TabItemStyle" TargetType="{x:Type TabItem}">
    <Setter Property="Foreground" Value="Black"/>
    <Setter Property="Background" Value="Transparent"/>
    <Setter Property="BorderBrush" Value="#fff"/>
    <Setter Property="Margin" Value="0,0,0,8"/>
    <Setter Property="HorizontalContentAlignment" Value="Stretch"/>
    <Setter Property="VerticalContentAlignment" Value="Stretch"/>
    <Setter Property="Template">
        <Setter.Value>
            <ControlTemplate TargetType="{x:Type TabItem}">
                <Grid x:Name="templateRoot"  SnapsToDevicePixels="True" Background="Transparent">
                    <Grid.ColumnDefinitions>
                        <ColumnDefinition Width="*"/>
                    </Grid.ColumnDefinitions>
                    <Border x:Name="ContentPanel" BorderBrush="{DynamicResource ColorBrush2}" BorderThickness="0,0,0,2" Background="White" Grid.Column="0" KeyboardNavigation.DirectionalNavigation="Contained"
                        Grid.Row="0" KeyboardNavigation.TabIndex="2" KeyboardNavigation.TabNavigation="Local" CornerRadius="7" Height="30" Margin="2,0,2,0"/>
                    <TextBlock x:Name="txt" Visibility="Visible" VerticalAlignment="Center" HorizontalAlignment="Center"
                    Text="{TemplateBinding Header}" ToolTip="{TemplateBinding Header}" Foreground="{TemplateBinding Foreground}" TextTrimming="CharacterEllipsis"/>
                </Grid>
                <ControlTemplate.Triggers>
                    <MultiDataTrigger>
                        <MultiDataTrigger.Conditions>
                            <Condition Binding="{Binding IsMouseOver, RelativeSource={RelativeSource Self}}" Value="true"/>
                            <Condition Binding="{Binding TabStripPlacement, RelativeSource={RelativeSource FindAncestor, AncestorLevel=1, AncestorType={x:Type TabControl}}}" Value="Top"/>
                        </MultiDataTrigger.Conditions>

                        <Setter Property="Foreground" TargetName="txt" Value="Blue"/>
                    </MultiDataTrigger>
                    <MultiDataTrigger>
                        <MultiDataTrigger.Conditions>
                            <Condition Binding="{Binding IsEnabled, RelativeSource={RelativeSource Self}}" Value="false"/>
                            <Condition Binding="{Binding TabStripPlacement, RelativeSource={RelativeSource FindAncestor, AncestorLevel=1, AncestorType={x:Type TabControl}}}" Value="Left"/>
                        </MultiDataTrigger.Conditions>
                            <Setter Property="Opacity" TargetName="templateRoot" Value="0.56"/>
                    </MultiDataTrigger>
                    <MultiDataTrigger>
                        <MultiDataTrigger.Conditions>
                            <Condition Binding="{Binding IsEnabled, RelativeSource={RelativeSource Self}}" Value="false"/>
                            <Condition Binding="{Binding TabStripPlacement, RelativeSource={RelativeSource FindAncestor, AncestorLevel=1, AncestorType={x:Type TabControl}}}" Value="Bottom"/>
                        </MultiDataTrigger.Conditions>
                        <Setter Property="Opacity" TargetName="templateRoot" Value="0.56"/>
                    </MultiDataTrigger>
                    <MultiDataTrigger>
                        <MultiDataTrigger.Conditions>
                            <Condition Binding="{Binding IsEnabled, RelativeSource={RelativeSource Self}}" Value="false"/>
                            <Condition Binding="{Binding TabStripPlacement, RelativeSource={RelativeSource FindAncestor, AncestorLevel=1, AncestorType={x:Type TabControl}}}" Value="Right"/>
                        </MultiDataTrigger.Conditions>
                        <Setter Property="Opacity" TargetName="templateRoot" Value="0.56"/>
                    </MultiDataTrigger>
                    <MultiDataTrigger>
                        <MultiDataTrigger.Conditions>
                            <Condition Binding="{Binding IsEnabled, RelativeSource={RelativeSource Self}}" Value="false"/>
                            <Condition Binding="{Binding TabStripPlacement, RelativeSource={RelativeSource FindAncestor, AncestorLevel=1, AncestorType={x:Type TabControl}}}" Value="Top"/>
                        </MultiDataTrigger.Conditions>
                        <Setter Property="Opacity" TargetName="templateRoot" Value="0.56"/>
                    </MultiDataTrigger>

                    <MultiDataTrigger>
                        <MultiDataTrigger.Conditions>
                            <Condition Binding="{Binding IsSelected, RelativeSource={RelativeSource Self}}" Value="true"/>
                            <Condition Binding="{Binding TabStripPlacement, RelativeSource={RelativeSource FindAncestor, AncestorLevel=1, AncestorType={x:Type TabControl}}}" Value="Top"/>
                        </MultiDataTrigger.Conditions>
                        <Setter Property="Panel.ZIndex" Value="1"/>
                        <Setter Property="Foreground" TargetName="txt" Value="Green"/>
                    </MultiDataTrigger>
                </ControlTemplate.Triggers>
            </ControlTemplate>
        </Setter.Value>
    </Setter>
</Style>
<Style TargetType="FlowDocumentScrollViewer">
<Setter Property="IsSelectionEnabled" Value="False"/>
<Setter Property="VerticalScrollBarVisibility" Value="Hidden"/>
<Setter Property="Margin" Value="0"/>
</Style>
<Style TargetType="FlowDocument" >
<Setter Property="FontFamily" Value="Microsoft YaHei UI"/>
<Setter Property="FontSize" Value="14"/>
<Setter Property="TextAlignment" Value="Left"/>
</Style>
<Style TargetType="StackPanel" x:Key="ContentStack" >
<Setter Property="Margin" Value="20,20,20,20"/>
</Style>
<Style TargetType="local:MyCard" x:Key="Card" >
<Setter Property="Margin" Value="0,5"/>
</Style>
<Style TargetType="Image" x:Key="InnerImage" >
<Setter Property="MaxHeight" Value="500"/>
<Setter Property="HorizontalAlignment" Value="Center"/>
</Style>
<Style TargetType="TextBlock" >
<Setter Property="TextWrapping" Value="Wrap"/>
<Setter Property="HorizontalAlignment" Value="Left"/>
<Setter Property="FontSize" Value="14"/>
<Setter Property="Foreground" Value="Black"/>
</Style>
<Style TargetType="List" >
<Setter Property="Foreground" Value="{DynamicResource ColorBrush3}"/>
<Setter Property="Margin" Value="20,0,0,0"/>
<Setter Property="MarkerStyle" Value="1"/>
<Setter Property="Padding" Value="0"/>
</Style>
<Style TargetType="ListItem" >
<Setter Property="Foreground" Value="Black"/>
<Setter Property="LineHeight" Value="22"/>
</Style
><Style TargetType="Paragraph" x:Key="H1" >
<Setter Property="FontSize" Value="24"/>
<Setter Property="Margin" Value="0,10,0,10"/>
<Setter Property="FontWeight" Value="Bold"/>
<Setter Property="Foreground" Value="{DynamicResource ColorBrush3}"/>
</Style>
<Style TargetType="Paragraph" x:Key="H2" >
<Setter Property="FontSize" Value="22"/>
<Setter Property="Margin" Value="0,10,0,5"/>
<Setter Property="FontWeight" Value="Bold"/>
<Setter Property="Foreground" Value="{DynamicResource ColorBrush3}"/>
</Style>
<Style TargetType="Paragraph" x:Key="H3" >
<Setter Property="FontSize" Value="18"/>
<Setter Property="Margin" Value="0,5,0,5"/>
<Setter Property="FontWeight" Value="Bold"/>
<Setter Property="Foreground" Value="{DynamicResource ColorBrush4}"/>
</Style>
<Style TargetType="Paragraph" x:Key="H5" >
<Setter Property="FontSize" Value="15"/>
<Setter Property="Margin" Value="0,3,0,5"/>
<Setter Property="Foreground" Value="{DynamicResource ColorBrush4}"/>
</Style>
<Style TargetType="Paragraph" x:Key="H7" >
<Setter Property="FontSize" Value="14"/>
<Setter Property="Margin" Value="0,2,0,2"/>
<Setter Property="Foreground" Value="{DynamicResource ColorBrush4}"/>
</Style>
<Style TargetType="Border" x:Key="Quote" >
<Setter Property="BorderThickness" Value="5,0,0,0"/>
<Setter Property="BorderBrush" Value="{DynamicResource ColorBrush4}"/>
<Setter Property="Padding" Value="10,5"/>
<Setter Property="Margin" Value="0,5"/>
</Style>
<Style x:Key="imgTitle" TargetType="TextBlock">
  <Setter Property="FontSize" Value="14" />
  <Setter Property="Foreground" Value="#FF777777" />
  <Setter Property="HorizontalAlignment" Value="Center" />
  <Setter Property="Margin" Value="0,0,0,15" />
</Style>
<sys:String x:Key="WikiIcon">
M172.61,196.65h31a7.69,7.69,0,0,1,7.62,6.65l11.19,80.95c2.58,20.09,5.16,40.18,7.73,60.79h1c3.61-20.61,7.47-41,11.34-60.79l18.23-81.58a7.7,7.7,0,0,1,7.52-6h26.58a7.7,7.7,0,0,1,7.51,6l18.48,81.6c3.86,19.57,7.21,40.18,11.07,60.79h1.29c2.32-20.61,4.9-41,7.22-60.79l11.67-81a7.7,7.7,0,0,1,7.62-6.6h27.72a7.7,7.7,0,0,1,7.59,9L364.41,382.2a7.69,7.69,0,0,1-7.58,6.38H311.61a7.7,7.7,0,0,1-7.54-6.14l-16-77.33c-3.09-14.68-5.67-30.14-7.47-44.57h-1c-2.58,14.43-4.9,29.89-7.73,44.57L256.34,382.4a7.7,7.7,0,0,1-7.54,6.18H204.6a7.69,7.69,0,0,1-7.58-6.32L165,205.72A7.71,7.71,0,0,1,172.61,196.65ZM286.87,507.39,159.71,455.25v22.82L97.54,451.18v-23.3l-89-2,9.54-119.29H44.78V291.24L31.45,280.81V247l14.09-4.23L45,227.13,63.33,220V207.1l5.51-2v-16.2l15.65-4.93V167.63l24.06-11.81,1.65-21.95,4.94-1.72-2-1V95.6h13V89.45l27.56-14.79L169,84.43,185.79,76l21.47,15.34,8.1,1v7.91h6.51l60.65-30.56,8,3.49,17-12.08L324,71l.12-2.19,39.15-22,18.06,12.53h26.37l3.79-1.62,36.38,27.4v28.77l16.81,8.15V149l6.08,3V164l10.15,5.51v11.32h9v11.52l1,0c1.54,0,3.44.08,5.91,0l15.13-.13V212.7h9.28v49.71h-5.8v36.1l-16,9h56l6.78,119.85-116.84-1.4Zm-157.16-85.7h27.23l128.51,52.7,152.82-78.54,92.15,1.1-3.36-59.47H456.67V325.89h-5.8v-40l22.37,1.81L485.36,281v-.86h-7.24V268.5h-7V236.33l-11.31,8.61V210.82h-9V187.35l-10.15-5.51V170.59l-11.59-5.79V138.2l-38.25-18.53,26.95-17.27v-2.29l-10.59-8-24.49,10.41V89.37H371.9l-10.35-7.18-8.38,4.7-.6,11.32-22.31,11.61-21.4-12.9L294,107.45l-10.58-4.63L192,148.87V130.24h-6.67V119l-1-.12V121l-28.12,4v.58h-7.1L151.49,150l-5.17-.37.11,3.38-1.27.44,14.7,10.59-45.37,22.26V206l-15.65,4.93V226l-5.51,2v12.57l-17.6,6.81.61,17.43-12,3.61,10.46,8.18v1.59h11.6v24l43.44,34.42h-84l-4.8,60,86.54,1.93v32.93l2.17.94ZM476.3,232.41h5.58v-4.25Z
</sys:String>
<sys:String x:Key="TranslateIcon">
M640 416h256c35.36 0 64 28.48 64 64v416c0 35.36-28.48 64-64 64H480c-35.36 0-64-28.48-64-64V640h128c53.312 0 96-42.976 96-96V416zM64 128c0-35.36 28.48-64 64-64h416c35.36 0 64 28.48 64 64v416c0 35.36-28.48 64-64 64H128c-35.36 0-64-28.48-64-64V128z m128 276.256h46.72v-24.768h67.392V497.76h49.504V379.488h68.768v20.64h50.88V243.36H355.616v-34.368c0-10.08 1.376-18.784 4.16-26.112a10.56 10.56 0 0 0 1.344-4.16c0-0.896-3.2-1.792-9.6-2.72h-46.816v67.36H192v160.896z m46.72-122.368h67.392v60.48h-67.36V281.92z m185.664 60.48h-68.768V281.92h68.768v60.48z m203.84 488l19.264-53.632h100.384l19.264 53.632h54.976L732.736 576h-64.64L576 830.4h52.256z m33.024-96.256l37.12-108.608h1.376l34.368 108.608h-72.864zM896 320h-64a128 128 0 0 0-128-128v-64a192 192 0 0 1 192 192zM128 704h64a128 128 0 0 0 128 128v64a192 192 0 0 1-192-192z
</sys:String>
<sys:String x:Key="CreeperIcon">
M213.333333 128a85.333333 85.333333 0 0 0-85.333333 85.333333v597.333334a85.333333 85.333333 0 0 0 85.333333 85.333333h597.333334a85.333333 85.333333 0 0 0 85.333333-85.333333V213.333333a85.333333 85.333333 0 0 0-85.333333-85.333333H213.333333z m0 64h597.333334c11.754667 0 21.333333 9.578667 21.333333 21.333333v597.333334c0 11.754667-9.578667 21.333333-21.333333 21.333333H213.333333c-11.754667 0-21.333333-9.578667-21.333333-21.333333V213.333333c0-11.754667 9.578667-21.333333 21.333333-21.333333z m64 106.666667a21.333333 21.333333 0 0 0-21.333333 21.333333v128a21.333333 21.333333 0 0 0 21.333333 21.333333h149.333334v-149.333333a21.333333 21.333333 0 0 0-21.333334-21.333333h-128z m149.333334 170.666666v85.333334h-64a21.333333 21.333333 0 0 0-21.333334 21.333333v160a32 32 0 1 0 64 0V704h213.333334v32a32 32 0 1 0 64 0V576a21.333333 21.333333 0 0 0-21.333334-21.333333h-64v-85.333334h-170.666666z m170.666666 0h149.333334a21.333333 21.333333 0 0 0 21.333333-21.333333v-128a21.333333 21.333333 0 0 0-21.333333-21.333333h-128a21.333333 21.333333 0 0 0-21.333334 21.333333v149.333333z
</sys:String>
<sys:String x:Key="thanks" xml:space="preserve">鸣谢|一些对主页开发有帮助的人:
土星仙鹤                                     @ QQ(2480379448) 主页初版的首个测试者!
ess的大清要活了 ~喵                   @ QQ(1837750594) 带我接触了自定义主页,没有他我可能到现在还不知道主页是什么!
最亮的信标                                  @ Github(Nattiden) 提供主页模板,本主页使用他的NewsHomepage为基础开发!
Mfn233                                       @ Github(Mfn233) 为主页提供最开始的技术支持支持和鼓励!
主页群的各位                               @ QQ群(828081791等) 为主页的开发提供持续的精神力量,快来一起咕咕咕!
凌云                                            @ Github(JingHai-Lingyun) 提供挂载主页的oss,真的真的非常感激!
排列没啥顺序，个个我都非常非常非常谢谢你们!</sys:String>
<sys:String x:Key="WikiPage">%(WikiPage)s</sys:String>
<sys:String x:Key="VersionID">%(version)s</sys:String>
<BitmapImage x:Key="Img" UriSource="%(img)s"/>
<sys:String x:Key="Topic">%(topic)s</sys:String>
<Style TargetType="Border" x:Key="HeadImageBorder" >
<Setter Property="HorizontalAlignment" Value="Center"/>
<Setter Property="BorderThickness" Value="4"/>
<Setter Property="VerticalAlignment" Value="Top"/>
<Setter Property="BorderBrush" Value="{DynamicResource ColorBrush3}"/>
<Setter Property="CornerRadius" Value="7"/>
<Setter Property="MaxHeight" Value="140"/>
</Style><Style TargetType="Border" x:Key="TitleBorder" >
<Setter Property="Margin" Value="0,-20,-1,10"/>
<Setter Property="Background" Value="{DynamicResource ColorBrush3}"/>
<Setter Property="Width" Value="170"/>
<Setter Property="Height" Value="30"/>
<Setter Property="CornerRadius" Value="7"/>
<Setter Property="BorderThickness" Value="0,0,0,2"/>
<Setter Property="BorderBrush" Value="{DynamicResource ColorBrush2}"/>
</Style><Style TargetType="TextBlock" x:Key="TitleBlock" >
<Setter Property="HorizontalAlignment" Value="Center"/>
<Setter Property="TextAlignment" Value="Center"/>
<Setter Property="VerticalAlignment" Value="Center"/>
<Setter Property="Foreground" Value="{DynamicResource ColorBrush7}"/>
<Setter Property="Width" Value="180"/>
<Setter Property="TextWrapping" Value="Wrap"/>
<Setter Property="FontSize" Value="18"/>
</Style>
</StackPanel.Resources>
<local:MyCard CanSwap="False" IsSwaped="false" Margin="0,-2,0,5">
<Border Margin="0,0,0,0" Padding="2,8" BorderThickness="1" Background="{DynamicResource ColorBrush5}" CornerRadius="5" VerticalAlignment="Top" BorderBrush="{DynamicResource ColorBrush3}" Opacity="0.7">
    <Grid Margin="10,0,0,0">
        <TextBlock FontWeight="Bold" FontSize="12" VerticalAlignment="Center" Foreground="#FF000000">
                📚 欢迎使用杂志主页
    </TextBlock>
        <TextBlock FontWeight="Bold" FontSize="12" VerticalAlignment="Center" Foreground="#00000000">
                📚 欢迎使用杂志主页
    </TextBlock>
    </Grid>
</Border>
</local:MyCard>

<TabControl Style="{StaticResource TabControlStyle}" FontFamily="Microsoft YaHei UI" FontSize="17">
    <TabItem Header="中文 Minecraft Wiki 摘录 - 特色条目" Style="{StaticResource TabItemStyle}">
<local:MyCard>
<StackPanel Style="{StaticResource ContentStack}">
<Border Style="{StaticResource HeadImageBorder}">
<Border.Background>
<ImageBrush ImageSource="{StaticResource Img}" Stretch="UniformToFill" />
</Border.Background>
<Image Source="{StaticResource Img}" Opacity="0" Stretch="Fill"/>
</Border>
<Border Style="{StaticResource TitleBorder}">
<TextBlock Style="{StaticResource TitleBlock}" Text="{StaticResource Topic}" />
</Border><FlowDocumentScrollViewer >
<FlowDocument>
    <Paragraph Style="{StaticResource H2}">
        <Run FontSize="22" FontWeight="Bold" Foreground="{DynamicResource ColorBrush3}" Text="{StaticResource Topic}"/>
    </Paragraph>
<List>
<!-- intro -->
%(intro)s
<!-- end_intro -->

</List><Paragraph Style="{StaticResource H3}">合成 &amp; 生成</Paragraph><List><!-- intro_2 -->
%(intro_2)s
<!-- end_intro_2 -->
</List>
<Paragraph Style="{StaticResource H3}">特性 &amp; 用途</Paragraph><List>
%(body)s
</List>
</FlowDocument>
</FlowDocumentScrollViewer>
<Grid VerticalAlignment="Center" Margin="6,10,0,0" HorizontalAlignment="Right">
<Grid.ColumnDefinitions >
<ColumnDefinition Width="45"/>
<ColumnDefinition />
</Grid.ColumnDefinitions>
<Path Grid.Column="0" Margin="8,0" Height="28" Fill="{DynamicResource ColorBrush4}"
                    Stretch="Uniform"
                    Data="M4 2H2v12h2V4h10V2zm2 4h12v2H8v10H6zm4 4h12v12H10zm10 10v-8h-8v8z"/>
<TextBlock HorizontalAlignment="Right" Grid.Column="1" Text="仿生猫梦见苦力怕" FontSize="14" VerticalAlignment="Center" Foreground="{DynamicResource ColorBrush4}"/>
</Grid>
<TextBlock Margin="0,2" Grid.Column="1" HorizontalAlignment="Right" Text="%(datetime)s" FontSize="12" Foreground="{DynamicResource ColorBrush4}"/>
<local:MyIconTextButton Text="WIKI" ToolTip="在 Minecraft Wiki 上查看该页面" EventType="打开网页"
    EventData="{StaticResource WikiPage}" LogoScale="1.05" Logo="{StaticResource WikiIcon}" HorizontalAlignment="Left"/>
</StackPanel>
</local:MyCard>
    </TabItem>
<TabItem Header="Minecraft官方博文 - 识海漫谈" Style="{StaticResource TabItemStyle}">
<local:MyCard>
<StackPanel Style="{StaticResource ContentStack}">
<Border Style="{StaticResource HeadImageBorder}">
<Border.Background>
<ImageBrush ImageSource="https://www.helloimg.com/i/2025/04/21/68062e0edcfaf.jpg" Stretch="UniformToFill" />
</Border.Background>
<Image Source="https://www.helloimg.com/i/2025/04/21/68062e0edcfaf.jpg" Opacity="0" Stretch="Fill"/>
</Border>
<Border Style="{StaticResource TitleBorder}">
<TextBlock Style="{StaticResource TitleBlock}" Text="末影人" />
</Border><FlowDocumentScrollViewer>
<FlowDocument>
<Paragraph Style="{StaticResource H7}">Mob Menagerie: Enderman</Paragraph>
<Paragraph Style="{StaticResource H2}">生物圈栏：末影人</Paragraph>
<Paragraph Style="{StaticResource H7}">A tall dark stranger that doesn’t like being stared at.</Paragraph>
<Paragraph Style="{StaticResource H5}">个子高、肤色深、讨厌被人盯着的怪人</Paragraph>
<Paragraph Margin="0,0" FontSize="12" Foreground="silver">Quick – what are the top three weirdest mobs in Minecraft?</Paragraph>
<Paragraph Margin="0,0" Foreground="black">一秒内，你能想到《我的世界》三大奇怪的生物是哪些么？</Paragraph>
<Paragraph Margin="0,0" FontSize="12" Foreground="silver">Here’s my list. Number three – the strider, happily wading around its lava pools. Number two – the mooshroom, an unholy hybrid of moo and shroom. But topping the list, at number one, is our mob of the month – the creepy, otherworldly, block-rearranging, Enderman.</Paragraph>
<Paragraph Margin="0,0" Foreground="black">在我心中，排名第三的是喜欢到处“玩岩浆”的炽足兽，第二是由哞哞叫的牛和蘑菇“杂交”而成的奇异生物 —— 哞菇，第一则是我们的本月生物 —— 令人毛骨悚然、远离世俗喧嚣、喜欢乱挪方块的末影人。</Paragraph>
<Paragraph Margin="0,0" FontSize="12" Foreground="silver">Endermen were added to Minecraft alongside melons, glass panes and iron bars in the Adventure Update, released in September 2011.</Paragraph>
<Paragraph Margin="0,0" Foreground="black">2011年11月，《我的世界》“冒险更新”版本发布，末影人被加入游戏，随之加入的还有西瓜、玻璃板和铁栏杆。</Paragraph>
<Paragraph Margin="0,0" FontSize="12" Foreground="silver">Originally they had green eyes and emitted smoke as they moved around, but those were changed to the now-familiar pink eyes and portal particles on release.</Paragraph>
<Paragraph Margin="0,0" Foreground="black">起初，末影人有双绿色的眼睛，移动时周围会烟雾弥漫。后来，末影人迎来大变样，眼睛变成了粉红色，突然出现时，会出现传送门粒子。</Paragraph>
<BlockUIContainer>
<StackPanel Margin="0,4,0,4">
<Image Style="{StaticResource InnerImage}" Source="https://www.helloimg.com/i/2025/04/21/68062e0da2e29.jpg"/>
</StackPanel>
</BlockUIContainer>
<Paragraph Margin="0,0" FontSize="12" Foreground="silver">Finding an Enderman should be easy. They’re the only mob that spawns naturally in all three of the game’s dimensions – the Overworld, the Nether, and the End. But actually they’re quite rare in the first two of those. </Paragraph>
<Paragraph Margin="0,0" Foreground="black">末影人一点也不难找。它是主世界、下界、末地三个维度都会生成的唯一一种怪物。前两个维度中，末影人应该很少出现。</Paragraph>
<Paragraph Margin="0,0" FontSize="12" Foreground="silver">My advice for finding one in the Overworld is to head somewhere where the terrain is relatively flat so you can see a good distance, then pillar up beyond the range of skeleton bows and wait for night time.</Paragraph>
<Paragraph Margin="0,0" Foreground="black">要想在主世界找到末影人，建议去一些地形平坦的地方，这样能一目千里，再原地往上搭几格，骷髅便攻击不到你，然后静静等待夜晚到来即可。</Paragraph>
<Paragraph Margin="0,0" FontSize="12" Foreground="silver"> Once the sun sets, begin to look out in all directions. Eventually, you’ll spot one – shuffling around, perhaps with a block in its hands.</Paragraph>
<Paragraph Margin="0,0" Foreground="black">夕阳西下，夜幕降临，便要开始眼观四方了。最后，你肯定能发现一只末影人 —— 它穿梭于地方之间，手里或许还拿着一个方块。</Paragraph>
<Paragraph Margin="0,0" FontSize="12" Foreground="silver">But be careful with that crosshair. Endermen really don’t like it when you look directly at their face. If you do, they’ll start screaming and shaking, and as soon as you look away it’ll begin teleporting towards you and begin to attack. </Paragraph>
<Paragraph Margin="0,0" Foreground="black">但要注意你屏幕上的十字准心，末影人可不会喜欢有人直勾勾地盯着它们的脸。你敢这样做，末影人便会抽泣，颤抖，随后朝你瞬移过来，向你发起攻击。</Paragraph>
<Paragraph Margin="0,0" FontSize="12" Foreground="silver">They’ll also teleport in a couple of other situations. </Paragraph>
<Paragraph Margin="0,0" Foreground="black">在其他一些情况下，末影人也会瞬移。</Paragraph>
<Paragraph Margin="0,0" FontSize="12" Foreground="silver">This means that you’ll need a melee weapon to take one down. </Paragraph>
<Paragraph Margin="0,0" Foreground="black">如果你将投掷物扔向末影人，它便会在投掷物击中的前一刻迅速躲开。所以，要想击杀末影人，必须用近战武器。</Paragraph>
<Paragraph Margin="0,0" FontSize="12" Foreground="silver">Also, Endermen don’t really like liquids or bright sunlight – if they come into contact with either, they’ll begin teleporting randomly, often ending up in caves below the surface where they lurk until it’s dark again. </Paragraph>
<Paragraph Margin="0,0" Foreground="black">同时，末影人也不喜欢和液体接触，更不喜欢在明媚的阳光下逗留 —— 遇到以上任何一种情况，末影人便会传送到任意地点，最终会躲到地表下的洞穴内，直到黑夜降临，才会再次出现在地面。</Paragraph>
<BlockUIContainer>
<StackPanel Margin="0,4,0,4">
<Image Style="{StaticResource InnerImage}" Source="https://www.helloimg.com/i/2025/04/21/68062e10eb1f6.png"/>
</StackPanel>
</BlockUIContainer>
<Paragraph Margin="0,0" FontSize="12" Foreground="silver">You don’t have to fight Endermen, you know. These strange, tall beings will happily ignore you if you ignore them and their habit of quietly moving blocks around from one place to another. </Paragraph>
<Paragraph Margin="0,0" Foreground="black">众所周知，你完全不需要与末影人搏斗。你不看这位身材高挑的怪家伙，它压根不会盯上你，而是自顾自悄悄拿起一个方块运到另一处。</Paragraph>
<Paragraph Margin="0,0" FontSize="12" Foreground="silver">But if you want to complete the game you will need to end a few, so here are a few useful things to know.</Paragraph>
<Paragraph Margin="0,0" Foreground="black">但若想通关游戏的话，你可能要“亲密接触”一些末影人了，下面是一些实用提示：</Paragraph>
<Paragraph Margin="0,0" FontSize="12" Foreground="silver">First, Endermen hit hard – about twice as hard as a zombie. They also have twice the health of a zombie, meaning that you’ll want to be prepared before taking one on. </Paragraph>
<Paragraph Margin="0,0" Foreground="black">第一，末影人攻击伤害可不低，大概有僵尸的两倍，血量也是僵尸的两倍。因此，与末影人斗智斗勇前，要准备充分。</Paragraph>
<Paragraph Margin="0,0" FontSize="12" Foreground="silver">Second, Endermen are tall enough that they won’t fit under a two-block high ceiling. You can often hide below a tree and attack one without it being able to hit back very effectively. </Paragraph>
<Paragraph Margin="0,0" Foreground="black">第二，末影人个子高，进不去2格高的地方。通常，你可以躲在一棵树下，然后用你的武器反击，这样一点也不用担心末影人会反击了。</Paragraph>
<Paragraph Margin="0,0" FontSize="12" Foreground="silver">Finally, when ended an Enderman, they will drop any block that they’re holding as an item, and will also sometimes drop an Ender pearl – a strange object that grants the holder the Endermen’s power of teleportation, as well as access to the End dimension. </Paragraph>
<Paragraph Margin="0,0" Foreground="black">最后，当你击杀了末影人，地上会掉落一些它们手上拿着的方块，有时也会掉落一个末影珍珠。末影珍珠是一种奇异物品，能让玩家拥有末影人的瞬移能力，更能解锁末地维度。</Paragraph>
<Paragraph Margin="0,0" FontSize="12" Foreground="silver">That’s where you’ll find the Ender Dragon – the closest thing that Minecraft has to a final boss. So get some practice in on the Endermen, and good luck – you’ll no doubt need it. </Paragraph>
<Paragraph Margin="0,0" Foreground="black">在末地，你便会见到《我的世界》最终BOSS —— 末影龙。因此，记得多在末影人上做点功课，未来肯定会派上用场。祝你好运！</Paragraph>
</FlowDocument>
</FlowDocumentScrollViewer>

<StackPanel Margin="0,0,0,20">
<Grid VerticalAlignment="Center" Margin="0,10,20,0" HorizontalAlignment="Right">
<Grid.ColumnDefinitions>
<ColumnDefinition Width="64"/>
<ColumnDefinition Width="*"/>
<ColumnDefinition Width="64"/>
<ColumnDefinition Width="*"/>
</Grid.ColumnDefinitions>
<Grid.RowDefinitions>
<RowDefinition Height="42"/>
<RowDefinition />
</Grid.RowDefinitions>
<Path Grid.Column="0" Margin="0,0" Height="28" Fill="{DynamicResource ColorBrush4}"
                    Stretch="Uniform"
                    Data="M640 416h256c35.36 0 64 28.48 64 64v416c0 35.36-28.48 64-64 64H480c-35.36 0-64-28.48-64-64V640h128c53.312 0 96-42.976 96-96V416zM64 128c0-35.36 28.48-64 64-64h416c35.36 0 64 28.48 64 64v416c0 35.36-28.48 64-64 64H128c-35.36 0-64-28.48-64-64V128z m128 276.256h46.72v-24.768h67.392V497.76h49.504V379.488h68.768v20.64h50.88V243.36H355.616v-34.368c0-10.08 1.376-18.784 4.16-26.112a10.56 10.56 0 0 0 1.344-4.16c0-0.896-3.2-1.792-9.6-2.72h-46.816v67.36H192v160.896z m46.72-122.368h67.392v60.48h-67.36V281.92z m185.664 60.48h-68.768V281.92h68.768v60.48z m203.84 488l19.264-53.632h100.384l19.264 53.632h54.976L732.736 576h-64.64L576 830.4h52.256z m33.024-96.256l37.12-108.608h1.376l34.368 108.608h-72.864zM896 320h-64a128 128 0 0 0-128-128v-64a192 192 0 0 1 192 192zM128 704h64a128 128 0 0 0 128 128v64a192 192 0 0 1-192-192z"/>
<TextBlock Grid.Column="1" Text="(MineBBS)Glorydark" FontSize="14" HorizontalAlignment="Right" VerticalAlignment="Center" Foreground="{DynamicResource ColorBrush4}"/>
<Path Grid.Column="2" Margin="8,0" Height="28" Fill="{DynamicResource ColorBrush4}"
                    Stretch="Uniform" HorizontalAlignment="Right"
                    Data="M14 21v-3.075l5.525-5.5q.225-.225.5-.325t.55-.1q.3 0 .575.113t.5.337l.925.925q.2.225.313.5t.112.55t-.1.563t-.325.512l-5.5 5.5zM4 20v-2.8q0-.85.438-1.562T5.6 14.55q1.55-.775 3.15-1.162T12 13q.925 0 1.825.113t1.8.362L12 17.1V20zm16.575-4.6l.925-.975l-.925-.925l-.95.95zM12 12q-1.65 0-2.825-1.175T8 8t1.175-2.825T12 4t2.825 1.175T16 8t-1.175 2.825T12 12"/>
<TextBlock HorizontalAlignment="Right" Grid.Column="3" Text="Duncan Geere" FontSize="14" VerticalAlignment="Center" Foreground="{DynamicResource ColorBrush4}"/>
<TextBlock Margin="0,2" Grid.Row="1" Grid.Column="1" Grid.ColumnSpan="2" HorizontalAlignment="Left" Text="最后更新: 2025-04-21" FontSize="12" Foreground="{DynamicResource ColorBrush4}"/>
<TextBlock Margin="0,2" Grid.Row="1" Grid.Column="3" Grid.ColumnSpan="2" HorizontalAlignment="Left" Text="源日期: 2025-04-07" FontSize="12" Foreground="{DynamicResource ColorBrush4}"/>
</Grid>
<local:MyIconTextButton Text="访问原址" ToolTip="在 Minecraft 官网上查看该页面原文" EventType="打开网页" Margin="8"
    EventData="https://www.minecraft.net/zh-hans/article/enderman" LogoScale="1.05" Logo="{StaticResource CreeperIcon}" HorizontalAlignment="Left"/>
</StackPanel>

<StackPanel Margin="16,0,23,20" VerticalAlignment="bottom">
    <Grid>
      <Grid.ColumnDefinitions>
        <ColumnDefinition Width="1*"/>
        <ColumnDefinition Width="120"/>
      </Grid.ColumnDefinitions>
      <local:MyComboBox x:Name="jumpbox" Height="30" SelectedIndex="0">
        <local:MyComboBoxItem Content="古迹废墟"/>
        <local:MyComboBoxItem Content="废弃矿井"/>
        <local:MyComboBoxItem Content="望远镜"/>
      </local:MyComboBox>
        <local:MyButton HorizontalAlignment="Center" Width="92"
            Grid.Column="1" Text="打开→" EventType="打开帮助"
            EventData="{Binding Path=Text,ElementName=jumpbox,StringFormat=http://pclhomeplazaoss.lingyunawa.top:26995/d/Homepages/Ext1nguisher/h{0}.json}"/>
    </Grid>
</StackPanel>
</StackPanel>
</local:MyCard>
</TabItem>
<TabItem Header="其他" Style="{StaticResource TabItemStyle}">
<StackPanel>
<local:MyCard CanSwap="False" IsSwaped="false" Margin="0,0,0,10">
<Border Margin="0,0,0,0" Padding="2,8" BorderThickness="1" Background="{DynamicResource ColorBrush5}" CornerRadius="5" VerticalAlignment="Top" BorderBrush="{DynamicResource ColorBrush3}" Opacity="0.7">
    <Grid Margin="10,0,0,0">
        <TextBlock FontWeight="Bold" FontSize="12" VerticalAlignment="Center" Foreground="#FF000000">
                ⚠️ &quot;最新版本&quot; 板块为每周更新时同步，并不一定为最新！
    </TextBlock>
        <TextBlock FontWeight="Bold" FontSize="12" VerticalAlignment="Center" Foreground="#00000000">
                ⚠️ &quot;最新版本&quot; 板块为每周更新时同步，并不一定为最新！
    </TextBlock>
    </Grid>
</Border>
</local:MyCard>
<!-- NewsCard -->
%(NewsCard)s
<!-- end_NewsCard -->
</StackPanel>
</TabItem>
</TabControl>
<local:MyCard Margin="0,10,0,14">
<Border BorderBrush="{DynamicResource ColorBrush2}" Margin="-0.6" CornerRadius="5" BorderThickness="0,0,0,10">
<StackPanel>
  <Grid Margin="26,20,20,2">
    <StackPanel>
    <StackPanel Orientation="Horizontal" VerticalAlignment="Center" Margin="0,0,0,4">
    <TextBlock FontSize="18" Foreground="{DynamicResource ColorBrush2}"><Bold>PCL2 杂志主页</Bold></TextBlock>
    <local:MyIconTextButton ColorType="Highlight" Margin="4,0" Text="{StaticResource VersionID}" ToolTip="当前版本号(非git), 点击复制" EventType="复制文本" EventData="{StaticResource VersionID}"
    LogoScale="1.1" Logo="M11.93 8.5a4.002 4.002 0 0 1-7.86 0H.75a.75.75 0 0 1 0-1.5h3.32a4.002 4.002 0 0 1 7.86 0h3.32a.75.75 0 0 1 0 1.5Zm-1.43-.75a2.5 2.5 0 1 0-5 0 2.5 2.5 0 0 0 5 0Z" />
    </StackPanel>
    <StackPanel Orientation="Horizontal" VerticalAlignment="Center" Margin="0,0,0,10">
    <TextBlock HorizontalAlignment="Left" Grid.Column="0" FontSize="13" VerticalAlignment="Center" Foreground="{DynamicResource ColorBrush4}">
        <Run>主页制作: 仿生猫梦见苦力怕 / CreeperIsASpy</Run>
        <LineBreak/>
        <Run>更新时间: 周一下午到周二下午（本人初中生学业紧张理解一下）</Run>
        <LineBreak/>
        <Run>内容取自</Run><Underline><local:MyTextButton EventType="打开网页" EventData="https://zh.minecraft.wiki">中文 Minecraft Wiki</local:MyTextButton></Underline>
        <Run>中“本周页面”板块以及 </Run><Underline><local:MyTextButton EventType="打开网页" EventData="https://minecraft.net">MC 官网</local:MyTextButton></Underline>。
    </TextBlock>
    </StackPanel>
    <StackPanel Orientation="Horizontal" VerticalAlignment="Center" Margin="-8,0,0,10">
    <local:MyIconTextButton HorizontalAlignment="Left" Text="Gitee" ToolTip="前往杂志主页 Gitee 页面" EventType="打开网页"
    EventData="https://gitee.com/planet_of_daniel/pcl2-homepage-fhg"
    LogoScale="1" Logo="M11.984 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12a12 12 0 0 0 12-12A12 12 0 0 0 12 0zm6.09 5.333c.328 0 .593.266.592.593v1.482a.594.594 0 0 1-.593.592H9.777c-.982 0-1.778.796-1.778 1.778v5.63c0 .327.266.592.593.592h5.63c.982 0 1.778-.796 1.778-1.778v-.296a.593.593 0 0 0-.592-.593h-4.15a.59.59 0 0 1-.592-.592v-1.482a.593.593 0 0 1 .593-.592h6.815c.327 0 .593.265.593.592v3.408a4 4 0 0 1-4 4H5.926a.593.593 0 0 1-.593-.593V9.778a4.444 4.444 0 0 1 4.445-4.444h8.296Z"/>
    <local:MyIconTextButton Text="CC BY-NC-SA 4.0" ToolTip="无特殊声明本主页文字内容使用该授权协议" EventType="打开网页"
    EventData="https://creativecommons.org/licenses/by-nc-sa/4.0/"
    LogoScale="1" Logo="M8.75.75V2h.985c.304 0 .603.08.867.231l1.29.736c.038.022.08.033.124.033h2.234a.75.75 0 0 1 0 1.5h-.427l2.111 4.692a.75.75 0 0 1-.154.838l-.53-.53.529.531-.001.002-.002.002-.006.006-.006.005-.01.01-.045.04c-.21.176-.441.327-.686.45C14.556 10.78 13.88 11 13 11a4.498 4.498 0 0 1-2.023-.454 3.544 3.544 0 0 1-.686-.45l-.045-.04-.016-.015-.006-.006-.004-.004v-.001a.75.75 0 0 1-.154-.838L12.178 4.5h-.162c-.305 0-.604-.079-.868-.231l-1.29-.736a.245.245 0 0 0-.124-.033H8.75V13h2.5a.75.75 0 0 1 0 1.5h-6.5a.75.75 0 0 1 0-1.5h2.5V3.5h-.984a.245.245 0 0 0-.124.033l-1.289.737c-.265.15-.564.23-.869.23h-.162l2.112 4.692a.75.75 0 0 1-.154.838l-.53-.53.529.531-.001.002-.002.002-.006.006-.016.015-.045.04c-.21.176-.441.327-.686.45C4.556 10.78 3.88 11 3 11a4.498 4.498 0 0 1-2.023-.454 3.544 3.544 0 0 1-.686-.45l-.045-.04-.016-.015-.006-.006-.004-.004v-.001a.75.75 0 0 1-.154-.838L2.178 4.5H1.75a.75.75 0 0 1 0-1.5h2.234a.249.249 0 0 0 .125-.033l1.288-.737c.265-.15.564-.23.869-.23h.984V.75a.75.75 0 0 1 1.5 0Zm2.945 8.477c.285.135.718.273 1.305.273s1.02-.138 1.305-.273L13 6.327Zm-10 0c.285.135.718.273 1.305.273s1.02-.138 1.305-.273L3 6.327Z" />
    </StackPanel>
    </StackPanel>
    <StackPanel HorizontalAlignment="Right" >
    <local:MyIconTextButton HorizontalAlignment="Left" Text="反馈" ToolTip="反馈主页问题" EventType="打开网页"
    EventData="https://gitee.com/planet_of_daniel/pcl2-homepage-fhg/issues/new"
    LogoScale="1" Logo="M8 9.5a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3z M8 0a8 8 0 1 1 0 16A8 8 0 0 1 8 0z M1.5 8a6.5 6.5 0 1 0 13 0 6.5 6.5 0 0 0-13 0z"/>
    <local:MyIconTextButton HorizontalAlignment="Left" Text="刷新" ToolTip="刷新主页" EventType="刷新主页"
    LogoScale="0.9" Logo="M960 416V192l-73.056 73.056a447.712 447.712 0 0 0-373.6-201.088C265.92 63.968 65.312 264.544 65.312 512S265.92 960.032 513.344 960.032a448.064 448.064 0 0 0 415.232-279.488 38.368 38.368 0 1 0-71.136-28.896 371.36 371.36 0 0 1-344.096 231.584C308.32 883.232 142.112 717.024 142.112 512S308.32 140.768 513.344 140.768c132.448 0 251.936 70.08 318.016 179.84L736 416h224z"/>
    <local:MyIconTextButton HorizontalAlignment="Left" Text="鸣谢" ToolTip="鸣谢人员名单及其联系方式" EventType="弹出窗口" EventData="{StaticResource thanks}"
    LogoScale="0.9" Logo="M6.26 21.388H6c-.943 0-1.414 0-1.707-.293C4 20.804 4 20.332 4 19.389v-1.112c0-.518 0-.777.133-1.009s.334-.348.736-.582c2.646-1.539 6.403-2.405 8.91-.91q.253.151.45.368a1.49 1.49 0 0 1-.126 2.134a1 1 0 0 1-.427.24q.18-.021.345-.047c.911-.145 1.676-.633 2.376-1.162l1.808-1.365a1.89 1.89 0 0 1 2.22 0c.573.433.749 1.146.386 1.728c-.423.678-1.019 1.545-1.591 2.075s-1.426 1.004-2.122 1.34c-.772.373-1.624.587-2.491.728c-1.758.284-3.59.24-5.33-.118a15 15 0 0 0-3.017-.308m4.601-18.026C11.368 2.454 11.621 2 12 2s.632.454 1.139 1.363l.13.235c.145.259.217.388.329.473s.252.117.532.18l.254.058c.984.222 1.476.334 1.593.71s-.218.769-.889 1.553l-.174.203c-.19.223-.285.334-.328.472s-.029.287 0 .584l.026.27c.102 1.047.152 1.57-.154 1.803s-.767.02-1.688-.404l-.239-.11c-.261-.12-.392-.18-.531-.18s-.27.06-.531.18l-.239.11c-.92.425-1.382.637-1.688.404s-.256-.756-.154-1.802l.026-.271c.029-.297.043-.446 0-.584s-.138-.25-.328-.472l-.174-.203c-.67-.784-1.006-1.177-.889-1.553s.609-.488 1.593-.71l.254-.058c.28-.063.42-.095.532-.18s.184-.214.328-.473zm8.569 4.319c.254-.455.38-.682.57-.682s.316.227.57.682l.065.117c.072.13.108.194.164.237s.126.058.266.09l.127.028c.492.112.738.167.796.356s-.109.384-.444.776l-.087.101c-.095.112-.143.168-.164.237s-.014.143 0 .292l.013.135c.05.523.076.785-.077.901s-.383.01-.844-.202l-.12-.055c-.13-.06-.196-.09-.265-.09c-.07 0-.135.03-.266.09l-.119.055c-.46.212-.69.318-.844.202c-.153-.116-.128-.378-.077-.901l.013-.135c.014-.15.022-.224 0-.292c-.021-.07-.069-.125-.164-.237l-.087-.101c-.335-.392-.503-.588-.444-.776s.304-.244.796-.356l.127-.028c.14-.032.21-.048.266-.09c.056-.043.092-.108.164-.237zm-16 0C3.685 7.227 3.81 7 4 7s.316.227.57.682l.065.117c.072.13.108.194.164.237s.126.058.266.09l.127.028c.492.112.738.167.797.356c.058.188-.11.384-.445.776l-.087.101c-.095.112-.143.168-.164.237s-.014.143 0 .292l.013.135c.05.523.076.785-.077.901s-.384.01-.844-.202l-.12-.055c-.13-.06-.196-.09-.265-.09c-.07 0-.135.03-.266.09l-.119.055c-.46.212-.69.318-.844.202c-.153-.116-.128-.378-.077-.901l.013-.135c.014-.15.022-.224 0-.292c-.021-.07-.069-.125-.164-.237l-.087-.101c-.335-.392-.503-.588-.445-.776c.059-.189.305-.244.797-.356l.127-.028c.14-.032.21-.048.266-.09c.056-.043.092-.108.164-.237z"/>
    </StackPanel>
  </Grid>
</StackPanel>
</Border>
</local:MyCard>
</StackPanel>'''
#   validate_template(content_text) 防止出现 f-string 问题
    content_text = re.sub(r"(?<!%)%(?!\()", "%%", content_text)
#   test = "{%(datetime)s} \n %(WikiPage)s \n %(topic)s \n %(intro)s \n %(intro_2)s \n %(body)s \n %(alt)s \n %(img)s \n %(NewsCard)s \n %(version)s"
    meta = {
        'WikiPage': get_wiki_page(),
        'version': get_version(),
        'img': gs(),
        'topic': get_topic(),
        'intro': gr()[0],
        'intro_2': gr()[1],
        'body': '\n'.join(gr()[2:]),
        'datetime': f'最后更新: {now.strftime("%Y-%m-%d")}',
        'NewsCard': get_news_card()
    }
    for k, v in meta.items():
        meta[k] = str(v)

    #   content_text = re.sub(r'}', "}}", re.sub(r'\{', '{{', content_text))
    content_text = content_text.replace("}", "}}").replace("{", "{{")
    #   output = re.sub(r'}}', "}", re.sub(r'\{\{', '{', (content_text % meta)))
    output = (content_text % meta).replace("}}", "}").replace("{{", "{")
    print(output)
    with open("Custom.xaml", "w", encoding='UTF-8') as f:
        f.write(output)


def print_out():
    print(f'INTRO $1:\n\t{gr()[0]}\n')
    print(f'INTRO $2:\n\t{gr()[1]}\n')
    BODYTXT = '\n'.join(gr()[2:-1])
    print(f'BODY:    \n{BODYTXT}\n')
    ALTTXT = gr()[-1].replace("<ListItem>", '').replace("</ListItem>", '')
    print(f'ALT:\n\t{ALTTXT}\n')
    print(f'IMG: \n\t{gs()}\n')
    print(f'$NEWSCARD:     \n{get_news_card()}\n')
    print(f'$VID:     {get_version()}')


if __name__ == "__main__":
    get_wiki_data()
    update()
