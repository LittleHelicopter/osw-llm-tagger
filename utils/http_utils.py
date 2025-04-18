# utils/http_utils.py
import os

import requests
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

MAGIC_NUMBERS = {
    b'%PDF-': 'pdf',
    b'\x50\x4B\x03\x04': 'zip/docx/xlsx',
    b'\xD0\xCF\x11\xE0': 'doc/xls',
    b'\x7B\x5C\x72\x74': 'rtf',
    b'\x3C\x21\x44\x4F': 'html',
    b'\x3C\x68\x74\x6D': 'html',
    b'\x3C\x3F\x78\x6D': 'xml',
    b'\x47\x49\x46\x38': 'gif',
    b'\x89\x50\x4E\x47': 'png',
    b'\xFF\xD8\xFF': 'jpg',
}

def match_magic(content: bytes) -> str:
    for magic, filetype in MAGIC_NUMBERS.items():
        if content.startswith(magic):
            return filetype
    return 'unknown'

import requests
import re
from urllib.parse import urljoin

def detect_file_type(url, headers=None, base_url=None):
    try:
        # 如果提供了base_url，则合并url
        if base_url:
            url = urljoin(base_url, url)

        try:
            # 第一次GET请求
            response = requests.get(url, headers=headers, timeout=20, stream=True)
            response.raise_for_status()

            content = response.raw.read(512)

            file_type = match_magic(content)

            if file_type != 'unknown':
                return {'type': file_type, 'url': url}

        except requests.RequestException as e:
            # 如果第一次请求失败，打印日志并继续执行后续操作
            print(f"[Warning] First request failed for {url}: {e}")

        # 第二次GET请求（如果第一次失败）
        url = urljoin("https://portal.nyserda.ny.gov", url)  # 拼接完整URL
        doc_response = requests.get(url, headers=headers, allow_redirects=True)
        print(doc_response.status_code)
        print('1')
        print(url)

        if doc_response.status_code == 200:
            print('2')
            match = re.search(r"window\.parent\.location\.href='(.*?)';", doc_response.text)
            if match:
                redirected_url = urljoin(url, match.group(1))
                print(redirected_url)

                try:
                    # 对重定向的URL再次发起请求
                    redirected_resp = requests.get(redirected_url, headers=headers, timeout=20, stream=True)
                    redirected_resp.raise_for_status()
                    redirected_content = redirected_resp.raw.read(512)
                    file_type = match_magic(redirected_content)
                    return {'type': file_type, 'url': redirected_url}

                except requests.RequestException as e:
                    # 捕获重定向请求失败的异常
                    print(f"[Error] Failed to fetch redirected URL {redirected_url}: {e}")
                    return {'type': 'unknown', 'url': redirected_url, 'error': str(e)}
            return {'type': 'unknown', 'url': url}
        return {'type': 'unknown', 'url': url}

    except Exception as e:
        print(f"[Error] Failed to detect file type from {url}: {e}")
        return {'type': 'unknown', 'url': url, 'error': str(e)}


# 处理链接，检测链接类型
def process_link(link_url, link_text, headers=None, base_url=None):
    full_url = urljoin(base_url, link_url) if base_url else link_url
    file_info = detect_file_type(full_url, headers, base_url)

    return {
        "text": link_text,
        "url": full_url,
        "is_pdf": bool(file_info['type'] == 'pdf'),
        "file_type": file_info['type'],  # 直接返回文件类型
        "file_url": file_info['url'],  # 返回文件的最终 URL
        "error": file_info.get('error', None)  # 若有错误，返回错误信息
    }


def download_snapshot(url, output_dir='./snaps', filename='snapshot.html'):
    # 设置请求头，防止被屏蔽
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        )
    }

    # 发起请求
    response = requests.get(url, headers=headers)

    # 检查响应
    if response.status_code == 200:
        # 创建文件夹（如果不存在）
        os.makedirs(output_dir, exist_ok=True)

        # 拼接完整保存路径
        file_path = os.path.join(output_dir, filename)

        # 写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(response.text)

        print(f"Snapshot saved to {file_path}")
    else:
        print(f"Failed to download page: status code {response.status_code}")


def remove_header_footer_tags(soup, keep_header_footer=True):
    """从 HTML 中移除 header 和 footer 区块（如果不保留）"""
    if not keep_header_footer:
        for selector in [
            'header', 'footer', 'nav',
            '.footer', '.header', '.site-footer', '.site-header',
            '#footer', '#header'
        ]:
            for tag in soup.select(selector):
                tag.decompose()


def extract_text_from_url(url, headers, keep_header_footer=False):
    # 发送请求获取网页内容
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        raise Exception(f"请求失败，状态码：{response.status_code}")

    # 解析 HTML
    soup = BeautifulSoup(response.text, 'html.parser')

    # 可选：移除 header/footer
    remove_header_footer_tags(soup, keep_header_footer=keep_header_footer)

    # 移除 script 和 style
    for tag in soup(['script', 'style', 'noscript']):
        tag.decompose()

    # 提取纯文本
    text = soup.get_text(separator='\n')

    # 清理多余空行和空白
    lines = [line.strip() for line in text.splitlines()]
    non_empty_lines = [line for line in lines if line]

    return '\n'.join(non_empty_lines)
