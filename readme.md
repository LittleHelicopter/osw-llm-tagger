# nyserda-fetch-archiv

## File Introduction

- filename-link.py: scrap filename/text on the html and link and redirected link, and save as json
- get-filename-pair.py: get '{'text': 'Summary of Revisions [PDF]', 'filename': 'servlet_FileDownload'}' pairs from json
- html-content.py: get html content from url
- 

## TODO

- [ ] download html
- [ ] file index
- [ ] write a label filter

[//]: # (- [ ] html structure)

[//]: # (  - [ ] clean paragraphs text)

[//]: # (  - [ ] clean documents name)

[//]: # (  - [ ] check is pdf link, other files link or html link)

    ### 📦 常见可下载文件的 Magic Number（建议重点支持）

    | 文件类型 | 扩展名 | Magic Number (十六进制) | 可下载性 |
    |----------|---------|---------------------------|-----------|
    | PDF | `.pdf` | `25 50 44 46` (`%PDF`) | ✅ |
    | ZIP | `.zip` / `.docx` / `.xlsx` / `.pptx` | `50 4B 03 04` | ✅ |
    | Microsoft Word (旧格式) | `.doc` | `D0 CF 11 E0 A1 B1 1A E1` | ✅ |
    | Microsoft Excel (旧格式) | `.xls` | `D0 CF 11 E0 A1 B1 1A E1` | ✅ |
    | WordPerfect | `.wpd` | `FF 57 50 43` | ✅ |
    | RTF | `.rtf` | `7B 5C 72 74 66` | ✅ |
    | HTML | `.html` | `3C 21 44 4F 43 54` (`<!DOC`) | ✅ |
    | XML | `.xml` | `3C 3F 78 6D 6C` (`<?xml`) | ✅ |
    | PNG | `.png` | `89 50 4E 47 0D 0A 1A 0A` | 可选 |
    | JPEG | `.jpg` | `FF D8 FF` | 可选 |
    | GIF | `.gif` | `47 49 46 38` | 可选 |
    | MP3 | `.mp3` | `FF FB` / `49 44 33` | 可选 |
    | MP4 | `.mp4` | `00 00 00 18 66 74 79 70` | 可选 |
    | EXE | `.exe` | `4D 5A` | ⛔（通常不下载） |

    ---

    ### ✅ 建议作为“可下载文件”的判断标准

    建议将以下几类 **作为可下载的有效文档类文件类型识别**：

    > - `.pdf`
    > - `.doc`, `.docx`
    > - `.xls`, `.xlsx`
    > - `.ppt`, `.pptx`
    > - `.zip`
    > - `.rtf`, `.html`, `.xml`
    > - `.txt`（无 magic number，但内容判断为文本）


## Problems

- [ ] xlsx是unknown
- [ ] 2023有个文档无法下载[request for information]
  - [ ] 无法判断这个链接是pdf文档，cannot get the magic number
  - [ ] 