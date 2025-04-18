import json


def extract_fields_from_json(input_path, output_path=None, fields=[]):
    """
    从 JSON 文件中提取指定字段，保存为新 JSON 文件。

    参数:
        input_path (str): 原始 JSON 文件路径
        output_path (str): 输出 JSON 文件路径
        fields (list): 要提取的字段名列表
    """
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    result = []

    for item in data:
        entry = {}
        for field in fields:
            if field in item:
                entry[field] = item[field]
        if entry:
            result.append(entry)
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

    return result



