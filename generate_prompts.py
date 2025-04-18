import os
import json

from utils.json_utils import extract_fields_from_json


def generate_string_prompts(input_path_json, input_path_content, output_path=None):
    data = extract_fields_from_json(
        input_path=input_path_json,
        # output_path='output_pairs.json',
        fields=["safe_text", "filename"]
    )

    with open(input_path_content, 'r', encoding='utf-8') as f:
        content = f.read()  # This reads the entire file as a string

    print(data)
    print(content)

    prompt = (
        "You are given a list of documents. Each item includes a `text` field (the display title) "
        "and a `filename` field (the linked file name). Your task is to classify each document into "
        "**one of the following categories**:\n\n"
        "• Request for Proposals (RFP)\n"
        "• Contract\n"
        "• Comment\n"
        "• Memorandum of Understanding (MOU)\n"
        "• Regulatory Filing\n"
        "• Policy Guidance\n"
        "• Public Notice\n"
        "• Industry Response\n"
        "• Other\n\n"
        "Use both the `text` and `filename` fields to infer the category, and refer to the contextual information provided below. "
        "If the information is insufficient or ambiguous, choose `Other`.\n\n"
        "Return a JSON array with the same number of objects. Each object must include the original `text` and `filename`, "
        "along with an additional `category` field. Example:\n"
        "{\n"
        "  \"text\": \"Example Title\",\n"
        "  \"filename\": \"example.pdf\",\n"
        "  \"category\": \"Policy Guidance\"\n"
        "}\n\n"
        "Here is the data:\n"
        f"{data}\n\n"
        "Here is the reference context:\n"
        f"{content}"
    )

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Save the prompt to the file
    if output_path:  # Check if output_path is not None
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Save the prompt to the file
        with open(output_path, 'w', encoding='utf-8') as output_file:
            output_file.write(prompt)
        print(f"Prompt saved to {output_path}")
    else:
        print("No output path provided. Prompt not saved.")
    return prompt


def generate_json_prompt(input_path_json, input_path_content, output_path=None):
    data = extract_fields_from_json(
        input_path=input_path_json,
        fields=["safe_text", "filename"]
    )

    with open(input_path_content, 'r', encoding='utf-8') as f:
        content = f.read()

    instruction = (
        "You are given a list of documents. Each item includes a `text` field (the display title) "
        "and a `filename` field (the linked file name). Your task is to classify each document into "
        "**one of the following categories**:\n\n"
        "• Request for Proposals (RFP)\n"
        "• Contract\n"
        "• Comment\n"
        "• Memorandum of Understanding (MOU)\n"
        "• Regulatory Filing\n"
        "• Policy Guidance\n"
        "• Public Notice\n"
        "• Industry Response\n"
        "• Other\n\n"
        "Use both the `text` and `filename` fields to infer the category, and refer to the contextual information provided below. "
        "If the information is insufficient or ambiguous, choose `Other`.\n\n"
        "Return a JSON array with the same number of objects. Each object must include the original `text` and `filename`, "
        "along with an additional `category` field. Example:\n"
        "{\n"
        "  \"text\": \"Example Title\",\n"
        "  \"filename\": \"example.pdf\",\n"
        "  \"category\": \"Policy Guidance\"\n"
        "}"
    )

    json_prompt = {
        "instruction": instruction,
        "data": data,
        "reference": content
    }

    # Save to file if output path provided
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(json_prompt, f, indent=2, ensure_ascii=False)
        print(f"Prompt saved to {output_path}")
    else:
        print("No output path provided. Prompt not saved.")

    return json_prompt


def main():
    years = [2018, 2020, 2022, 2023, 2024]
    for year in years:
        input_path_json = f'data/document_info/extracted_links_{year}.json'
        input_path_content = f'data/html_content/{year}.txt'
        output_path = f"data/prompts/{year}.txt"
        generate_string_prompts(input_path_json, input_path_content, output_path=output_path)
        generate_json_prompt(input_path_json, input_path_content, output_path=f"data/prompts/{year}.json")


if __name__ == "__main__":
    main()



