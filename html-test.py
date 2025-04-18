import requests
import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup, Tag
import json


# 判断是否是 PDF 文件并处理重定向
def is_pdf_file(url, headers=None, base_url=None):
    try:
        # 如果 URL 是相对路径，拼接成完整 URL
        if base_url:
            url = urljoin(base_url, url)

        # 发送请求获取内容
        response = requests.get(url, headers=headers, timeout=20, stream=True)
        response.raise_for_status()
        content = response.content

        # 首先检查是否是 PDF 文件
        if content[:5] == b'%PDF-':
            return url

        # 如果不是 PDF，尝试查找重定向 URL
        match = re.search(r"window\.parent\.location\.href='(.*?)';", content.decode("utf-8", errors="ignore"))
        if match:
            redirected_pdf_url = urljoin(url, match.group(1))  # 拼接完整的 URL
            with requests.get(redirected_pdf_url, headers=headers, stream=True, timeout=20) as pdf_resp:
                pdf_resp.raise_for_status()
                content = pdf_resp.content
                if content[:5] == b'%PDF-':
                    return redirected_pdf_url
                else:
                    raise ValueError("重定向后仍不是有效 PDF")
        else:
            raise ValueError("不是 PDF 且未检测到跳转链接")

    except Exception as e:
        print(f"Error while fetching PDF: {e}")
        return None


# 处理链接，检测是否为PDF
def process_link(link_url, link_text, headers=None, base_url=None):
    if not link_url:
        return {"text": link_text, "url": None, "is_pdf": False}

    full_url = urljoin(base_url, link_url) if base_url else link_url
    pdf_url = is_pdf_file(full_url, headers, base_url)

    return {
        "text": link_text,
        "url": full_url,
        "is_pdf": bool(pdf_url),
        "pdf_url": pdf_url if pdf_url else None
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
def process_element(element, section_data, link_stats, section_name, headers, url):
    # 提取段落文本
    if element.name == 'p':
        text = element.text.strip()
        if text:
            section_data["paragraphs"].append(text)

    # 提取链接
    links = element.find_all('a', href=True) if hasattr(element, 'find_all') else []
    for link in links:
        if link.text.strip():
            link_data = process_link(link["href"], link.text.strip(), headers, url)
            section_data["links"].append(link_data)

            # 更新链接统计
            link_stats["total_links"] += 1
            if section_name in link_stats["sections"]:
                link_stats["sections"][section_name]["total_links"] += 1

                if link_data["is_pdf"]:
                    link_stats["pdf_links"] += 1
                    link_stats["sections"][section_name]["pdf_links"] += 1

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

                            # 更新链接统计
                            link_stats["total_links"] += 1
                            if section_name in link_stats["sections"]:
                                link_stats["sections"][section_name]["total_links"] += 1
                                link_stats["sections"][section_name]["table_links"] += 1

                                if link_data["is_pdf"]:
                                    link_stats["pdf_links"] += 1
                                    link_stats["sections"][section_name]["pdf_links"] += 1

                    if cell_links:
                        header_name = table_headers[idx] if idx < len(table_headers) else f"Column {idx + 1}"
                        row_data[f"{header_name}_links"] = cell_links

            table_data.append(row_data)

        if table_data:
            section_data["tables"].append(table_data)


# 创建或获取内容部分
def get_or_create_section(structured_data, path, link_stats):
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
            link_stats["sections"][full_path] = {
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
    link_stats = {
        "total_links": 0,
        "pdf_links": 0,
        "sections": {}
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
        link_stats["sections"]["Main Content"] = {
            "total_links": 0,
            "pdf_links": 0,
            "table_links": 0
        }

        # 处理整个页面内容
        for element in soup.body.children:
            if isinstance(element, Tag):
                process_element(element, structured_data["Main Content"], link_stats,
                                "Main Content", headers, url)

        return structured_data, link_stats

    # 处理第一个标题之前的内容
    first_heading = headings[0]
    if first_heading:
        structured_data["Page Header"] = {
            "paragraphs": [],
            "links": [],
            "tables": [],
            "subsections": {}
        }
        link_stats["sections"]["Page Header"] = {
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
                    process_element(element, structured_data["Page Header"], link_stats,
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
        section, full_path = get_or_create_section(structured_data, current_path, link_stats)

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
                process_element(next_element, section, link_stats, full_path, headers, url)
            next_element = next_element.next_sibling

    return structured_data, link_stats

# 执行并将结果保存为结构化数据
def main():
    target_url = 'https://www.nyserda.ny.gov/All-Programs/Offshore-Wind/Focus-Areas/Offshore-Wind-Solicitations/2022-Solicitation'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

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
    with open('structured_content_2022.json', 'w', encoding='utf-8') as f:
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