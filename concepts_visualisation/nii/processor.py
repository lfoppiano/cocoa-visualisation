import argparse
import json
import os
import sys
from pathlib import Path

import languagecodes
from bs4 import BeautifulSoup
from ftlangdetect import detect
from tqdm import tqdm


def extract_metadata(input_path):
    with open(input_path, encoding='utf-8') as fp:
        doc = fp.read()

    soup = BeautifulSoup(doc, 'xml')

    records = soup.find_all("record")

    metadata_list = []
    for record in records:
        authors_output = []
        tags_output = []
        header = record.find("header")

        identifier = header.find('identifier').text

        record_information = {
            "id": identifier,
            "authors": authors_output,
            "tags": tags_output
        }

        meta = record.find("metadata")

        if not meta:
            continue

        language = meta.find("dc:language")
        if language:
            language_text = language.text
            article_default_lang = languagecodes.iso_639_alpha2(language_text)

        author_blocks = meta.find_all("creator")
        if author_blocks and len(author_blocks) > 0:
            for author_block in author_blocks:
                authors = author_block.find_all("creatorName")
                author_forms = {}
                if authors and len(authors) > 0:
                    for author in authors:
                        if author.has_attr('xml:lang'):
                            author_lang = author['xml:lang']
                        else:
                            author_lang = detect(author.text.replace("\n", " "), low_memory=True)['lang']
                        author_forms[author_lang] = author.text

                    authors_output.append(author_forms)

        else:
            continue

        tags = meta.find_all("subject")
        if tags and len(tags) > 0:
            for tag in tags:

                subject_scheme = ""
                if tag.has_attr('subjectScheme'):
                    subject_scheme = tag['subjectScheme']

                tag_text = tag.text.replace("\r\n", " ").replace("\n", " ")

                tag_block = {
                    "type": subject_scheme,
                    "text": tag_text,
                }

                if subject_scheme == "Other":
                    detected_lang = detect(text=tag_text, low_memory=True)['lang']
                    tag_block["lang"] = detected_lang

                tags_output.append(tag_block)

        else:
            continue

        metadata_list.append(record_information)

    return metadata_list


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Converter TSV to XML (Grobid training data based on TEI)")

    parser.add_argument("--input", help="Input file or directory", required=True, type=Path)
    parser.add_argument("--output",
                        help="Output directory (if omitted, the output will be the same directory/file with different extension)",
                        required=False, type=Path, default=None)
    parser.add_argument("--recursive", action="store_true", default=False,
                        help="Process input directory recursively. If input is a file, this parameter is ignored. ")
    parser.add_argument("--offline", help="", action="store_true", required=False, default=False)

    args = parser.parse_args()

    input = args.input
    output = args.output
    recursive = args.recursive
    offline = args.offline

    if os.path.isdir(input):
        path_list = []

        if recursive:
            for root, dirs, files in os.walk(input):
                # Manage to create the directories
                for dir in dirs:
                    abs_path_dir = os.path.join(root, dir)
                    output_path = abs_path_dir.replace(str(input), str(output))
                    if not os.path.exists(output_path):
                        os.makedirs(output_path)

                for file_ in files:
                    if not file_.lower().endswith(".xml"):
                        continue

                    abs_path = os.path.join(root, file_)
                    output_filename = Path(abs_path).stem
                    parent_dir = Path(abs_path).parent
                    if os.path.isdir(str(output)):
                        output_ = Path(str(parent_dir).replace(str(input), str(output)))
                        output_filename_with_extension = str(output_filename) + ".xml"
                        output_path = os.path.join(output_, output_filename_with_extension)
                    else:
                        output_path = os.path.join(parent_dir, output_filename + ".output.xml")

                    path_list.append((abs_path, output_path))

        else:

            for abs_path in Path(input).glob('*.xml'):
                abs_path_ = str(abs_path).replace(".tei", "")
                output_filename = Path(abs_path_).stem
                parent_dir = Path(abs_path_).parent
                if os.path.isdir(str(output)):
                    output_ = Path(str(parent_dir).replace(str(input), str(output)))
                    output_filename_with_extension = str(output_filename) + ".metadata.json"
                    output_path = os.path.join(output_, output_filename_with_extension)
                else:
                    output_path = os.path.join(output_, output_filename + ".metadata.json")

                path_list.append((abs_path, Path(output_path)))

        for input_path, output_path in tqdm(path_list):
            if os.path.exists(output_path):
                continue
            # print("Processing: ", input_path)
            metadata = extract_metadata(input_path)
            with open(output_path, 'w') as fp:
                json.dump(metadata, fp)


    elif os.path.isfile(input):
        input_path = Path(input)
        if os.path.isdir(str(output)):
            output_filename = Path(input).stem
            output_filename_with_extension = str(output_filename) + ".metadata.json"
            output_path = os.path.join(output, output_filename_with_extension)
        else:
            print("The --output should be a directory.")
            sys.exit(-1)

        metadata = extract_metadata(input_path)
        with open(output_path, 'w') as fp:
            json.dump(metadata, fp)
