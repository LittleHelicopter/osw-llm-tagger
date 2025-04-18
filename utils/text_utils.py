import re


def clean_text(text):
    """
    Clean text by removing NBSPs and all normalizing whitespace.
    :param text: str
    :return: cleaned text，str
    """
    if not text:
        return ""

    # Replace non-breaking space (various representations) with regular space
    text = text.replace('\xa0', ' ')  # Unicode NBSP
    text = text.replace('&nbsp;', ' ')  # HTML entity

    # Replace multiple spaces with a single space
    text = re.sub(r'\s+', ' ', text)

    # Strip leading and trailing whitespace
    text = text.strip()

    return text


def clean_text_preserve_paragraphs(text):
    """
    Combine whitespace and preserve paragraphs
    :param text: str
    :return: cleaned text with paragraphs structure，str
    """
    if not text:
        return ""

    # 替换常见的NBSP空格
    text = text.replace('\xa0', ' ')
    text = text.replace('&nbsp;', ' ')

    # 用两个及以上换行分段
    paragraphs = re.split(r'\n{2,}', text)

    cleaned_paragraphs = []

    for para in paragraphs:
        # 段落内部：将多个空格合并成一个（保留换行）
        para = re.sub(r'[ \t\r\f\v]+', ' ', para)

        # 去除段落开头结尾的空格和换行
        para = para.strip()

        # 忽略空段落
        if para:
            cleaned_paragraphs.append(para)

    # 重新用两个换行拼接成段落
    return '\n\n'.join(cleaned_paragraphs)
