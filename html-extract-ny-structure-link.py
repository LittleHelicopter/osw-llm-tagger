import requests
import re
from urllib.parse import urljoin
from utils.http_utils import process_link

from bs4 import BeautifulSoup, Tag
import json

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://portal.nyserda.ny.gov"
}


# 获取标题的数字级别 (h1 -> 1, h2 -> 2, etc.)
def get_heading_level(tag):
    if not tag or not tag.name or not tag.name.startswith('h'):
        return 0
    try:
        return int(tag.name[1])
    except ValueError:
        return 0

# 处理单个HTML元素
def process_element(element, section_data, link_tracker, section_name, headers, url):
    # 提取段落文本
    if hasattr(element, 'stripped_strings'):
        texts = list(element.stripped_strings)
        for text in texts:
            if text:
                section_data["paragraphs"].append(text)

    # 提取链接
    links = element.find_all('a', href=True) if hasattr(element, 'find_all') else []
    for link in links:
        if link.text.strip():
            link_data = process_link(link["href"], link.text.strip(), headers, url)
            section_data["links"].append(link_data)

            # 统计链接 (使用link_tracker而不是直接计数)
            add_link_to_stats(link_data, section_name, link_tracker)

    # 提取表格
    tables = element.find_all('table') if hasattr(element, 'find_all') else []
    for table in tables:
        table_data = []
        rows = table.find_all('tr')

        # 处理表头
        headers_row = rows[0] if rows else None
        table_headers = []
        if headers_row:
            table_headers = [th.text.strip() for th in headers_row.find_all(['th'])]

        # 处理表格内容行
        data_rows = rows[1:] if table_headers else rows
        for row in data_rows:
            cells = row.find_all(['td'])
            row_data = {}

            # 为每个单元格分配表头
            for idx, cell in enumerate(cells):
                header_name = table_headers[idx] if idx < len(table_headers) else f"Column {idx + 1}"
                row_data[header_name] = cell.text.strip()


            # 处理单元格中的链接
            for idx, cell in enumerate(cells):
                links_in_cell = cell.find_all('a', href=True)
                if links_in_cell:
                    cell_links = []
                    for link in links_in_cell:
                        if link.text.strip():
                            link_data = process_link(link["href"], link.text.strip(), headers, url)
                            cell_links.append(link_data)

                            # 使用相同的跟踪系统，但增加表格链接标记
                            add_link_to_stats(link_data, section_name, link_tracker, is_table_link=True)

                    if cell_links:
                        header_name = table_headers[idx] if idx < len(table_headers) else f"Column {idx + 1}"
                        row_data[f"{header_name}_links"] = cell_links

            table_data.append(row_data)

        if table_data:
            section_data["tables"].append(table_data)


# 添加链接到统计信息，使用link_tracker跟踪已处理过的链接
def add_link_to_stats(link_data, section_name, link_tracker, is_table_link=False):
    # 创建唯一标识符 (使用URL作为唯一标识)
    link_id = link_data["url"]

    # 如果链接已经计数过，只需更新section级别的统计信息
    if link_id in link_tracker["counted_links"]:
        # 只有当这个链接在当前section还未计数时才更新当前section的计数
        if section_name not in link_tracker["link_sections"].get(link_id, []):
            if section_name in link_tracker["stats"]["sections"]:
                link_tracker["stats"]["sections"][section_name]["total_links"] += 1
                if is_table_link:
                    link_tracker["stats"]["sections"][section_name]["table_links"] += 1
                if link_data["is_pdf"]:
                    link_tracker["stats"]["sections"][section_name]["pdf_links"] += 1

            # 记录此链接已在当前section计数
            link_tracker["link_sections"][link_id].append(section_name)
    else:
        # 新链接：更新全局计数和当前section的计数
        link_tracker["counted_links"].add(link_id)
        link_tracker["stats"]["total_links"] += 1
        if link_data["is_pdf"]:
            link_tracker["stats"]["pdf_links"] += 1

        # 更新此section的计数
        if section_name in link_tracker["stats"]["sections"]:
            link_tracker["stats"]["sections"][section_name]["total_links"] += 1
            if is_table_link:
                link_tracker["stats"]["sections"][section_name]["table_links"] += 1
            if link_data["is_pdf"]:
                link_tracker["stats"]["sections"][section_name]["pdf_links"] += 1

        # 初始化此链接的section列表
        link_tracker["link_sections"][link_id] = [section_name]


# 创建或获取内容部分
def get_or_create_section(structured_data, path, link_tracker):
    current = structured_data
    for i, section in enumerate(path):
        if section not in current:
            current[section] = {
                "paragraphs": [],
                "links": [],
                "tables": [],
                "subsections": {}
            }

            # 初始化链接统计
            full_path = " > ".join(path[:i + 1])
            link_tracker["stats"]["sections"][full_path] = {
                "total_links": 0,
                "pdf_links": 0,
                "table_links": 0
            }

        if i < len(path) - 1:
            if "subsections" not in current[section]:
                current[section]["subsections"] = {}
            current = current[section]["subsections"]
        else:
            return current[section], " > ".join(path)

    return None, None


# 主函数：结构化提取网页内容
def extract_structured_content(url, headers=None):
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')

    structured_data = {}

    # 创建一个链接跟踪器，用于减少重复计数
    link_tracker = {
        "stats": {
            "total_links": 0,
            "pdf_links": 0,
            "sections": {}
        },
        "counted_links": set(),  # 用集合存储已计数的链接URL
        "link_sections": {}  # 记录每个链接已被计数的sections
    }

    # 查找所有标题标签 (h1, h2, h3, h4, h5, h6)
    headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])

    # 如果没有任何标题标签，则处理整个页面内容
    if not headings:
        structured_data["Main Content"] = {
            "paragraphs": [],
            "links": [],
            "tables": [],
            "subsections": {}
        }
        link_tracker["stats"]["sections"]["Main Content"] = {
            "total_links": 0,
            "pdf_links": 0,
            "table_links": 0
        }

        # 处理整个页面内容
        for element in soup.body.children:
            if isinstance(element, Tag):
                process_element(element, structured_data["Main Content"], link_tracker,
                                "Main Content", headers, url)

        return structured_data, link_tracker["stats"]

    # 处理第一个标题之前的内容
    first_heading = headings[0]
    if first_heading:
        structured_data["Page Header"] = {
            "paragraphs": [],
            "links": [],
            "tables": [],
            "subsections": {}
        }
        link_tracker["stats"]["sections"]["Page Header"] = {
            "total_links": 0,
            "pdf_links": 0,
            "table_links": 0
        }

        # 获取body元素
        body = soup.body
        if body:
            # 收集在第一个标题之前的内容
            for element in body.children:
                # 如果到达第一个标题，则停止
                if element is first_heading or (
                        isinstance(element, Tag) and element.find(first_heading.name) is not None):
                    break
                if isinstance(element, Tag):
                    process_element(element, structured_data["Page Header"], link_tracker,
                                    "Page Header", headers, url)

    # 跟踪当前的标题路径和级别
    current_path = []
    current_levels = []  # 用于存储每个标题对应的级别

    # 处理每个标题及其内容
    for i, heading in enumerate(headings):
        heading_level = get_heading_level(heading)
        heading_text = heading.text.strip()

        # 根据标题级别更新路径
        if current_levels and heading_level <= current_levels[-1]:
            # 回退到适当的级别
            while current_levels and heading_level <= current_levels[-1]:
                current_path.pop()
                current_levels.pop()

        # 添加当前标题到路径
        current_path.append(heading_text)
        current_levels.append(heading_level)

        # 获取或创建此标题对应的部分
        section, full_path = get_or_create_section(structured_data, current_path, link_tracker)

        # 收集此标题后、下一个同级或更高级标题前的所有内容
        next_element = heading.next_sibling

        # 找到下一个同级或更高级的标题
        next_heading = None
        if i + 1 < len(headings):
            next_heading = headings[i + 1]
            next_heading_level = get_heading_level(next_heading)

            # 只有当下一个标题级别小于或等于当前标题时，才停止收集
            if next_heading_level > heading_level:
                next_heading = None

        # 收集内容元素
        while next_element and next_element != next_heading:
            if isinstance(next_element, Tag) and not (next_element.name and next_element.name.startswith('h') and int(
                    next_element.name[1]) <= heading_level):
                process_element(next_element, section, link_tracker, full_path, headers, url)
            next_element = next_element.next_sibling

    return structured_data, link_tracker["stats"]


# 执行并将结果保存为结构化数据
def main():
    target_url = 'https://www.nyserda.ny.gov/All-Programs/Offshore-Wind/Focus-Areas/Offshore-Wind-Solicitations/2018-Solicitation'

    result, link_stats = extract_structured_content(target_url, headers)

    # 打印链接统计
    print("==== 链接统计 ====")
    print(f"总链接数: {link_stats['total_links']}")
    print(f"PDF链接数: {link_stats['pdf_links']}")
    print("\n各区块链接统计:")
    for section_name, stats in link_stats["sections"].items():
        print(f"  {section_name}:")
        print(f"    总链接数: {stats['total_links']}")
        print(f"    PDF链接数: {stats['pdf_links']}")
        print(f"    表格内链接数: {stats.get('table_links', 0)}")

    # 将结果保存为JSON文件
    with open('structured_content_test_2018.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # 将链接统计保存为JSON文件
    with open('link_stats.json', 'w', encoding='utf-8') as f:
        json.dump(link_stats, f, ensure_ascii=False, indent=2)

    print("\n结构化内容已保存到 structured_content.json")
    print("链接统计已保存到 link_stats.json")

    # 打印提取的结构化数据
    print_structured_data(result)


# 递归打印结构化数据
def print_structured_data(data, indent=0):
    for section_name, section_data in data.items():
        print(f"{' ' * indent}{'#' * (indent // 2 + 1)} {section_name}")

        # 打印段落
        if section_data["paragraphs"]:
            print(f"{' ' * indent}段落数: {len(section_data['paragraphs'])}")

        # 打印链接
        if section_data["links"]:
            print(f"{' ' * indent}链接数: {len(section_data['links'])}")
            for link in section_data["links"][:3]:  # 仅打印前3个链接作为示例
                pdf_info = f"(PDF)" if link.get("is_pdf") else ""
                print(f"{' ' * indent}- {link['text']} {pdf_info}")
            if len(section_data["links"]) > 3:
                print(f"{' ' * indent}  ... 等{len(section_data['links']) - 3}个更多链接")

        # 打印表格
        if section_data["tables"]:
            print(f"{' ' * indent}表格数: {len(section_data['tables'])}")

        # 递归打印子区块
        if "subsections" in section_data and section_data["subsections"]:
            print_structured_data(section_data["subsections"], indent + 2)


if __name__ == "__main__":
    main()