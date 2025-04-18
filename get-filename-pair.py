# 示例用法：提取 text 和 filename 字段
from utils.json_utils import extract_fields_from_json

result = extract_fields_from_json(
    input_path='data/document_info/extracted_links_2018.json',
    output_path='output_pairs.json',
    fields=["save_text", "filename"]
)

print(result)

# count1 = count2 = 0
#
# for item in result:
#     if item['text'] == item['filename']:
#         # print(item)
#         count1 += 1
#     else:
#         print(item)
#         count2 += 1
#
# print(count1)
# print(count2)