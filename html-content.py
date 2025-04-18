import os

from utils.http_utils import extract_text_from_url
from config.config import headers
from utils.text_utils import clean_text_preserve_paragraphs



def save_html_content(url, output_path):
    text = extract_text_from_url(url, headers)
    cleaned_text = clean_text_preserve_paragraphs(text)
    print(cleaned_text)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(cleaned_text)


def main():

    years = [2018, 2020, 2022, 2023, 2024]

    base_url = 'https://www.nyserda.ny.gov/All-Programs/Offshore-Wind/Focus-Areas/Offshore-Wind-Solicitations/'

    urls = [f"{base_url}{year}-Solicitation" for year in years]

    for year in years:
        url = f"{base_url}{year}-Solicitation"
        output_path = f"data/html_content/{year}.txt"
        save_html_content(url, output_path)


if __name__ == "__main__":
    main()

