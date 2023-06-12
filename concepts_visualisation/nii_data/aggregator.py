import argparse
import json
import os
import sys
from pathlib import Path

import languagecodes
from bs4 import BeautifulSoup
from googletrans import Translator
from ftlangdetect import detect
from tqdm import tqdm
import argostranslate.package
import argostranslate.translate

argostranslate.package.update_package_index()
available_packages = argostranslate.package.get_available_packages()

for package in (filter(lambda x: x.to_code == "en" and x not in argostranslate.package.get_installed_packages(), available_packages)):
    print("Download and install", package)
    package.install()

from_langs = list(set([x.from_code for x in argostranslate.package.get_installed_packages()]))

print(argostranslate.package.get_installed_packages())

def translate_bulk(inputs: list, dest="en"):
    translator = Translator()
    try:
        translated_list = translator.translate(inputs, dest=dest).text
    except:
        try:
            translated_list = translator.translate(inputs, dest=dest).text
        except:
            print("Second failure, skip. ")
            translated_list = None

    return translated_list


def translate_offline(input, source="ja", dest="en"):
    translated = argostranslate.translate.translate(input, from_code=source, to_code=dest)
    return translated


def translate(input, dest="en"):
    translator = Translator()
    try:
        translated = translator.translate(input, dest=dest).text
    except:
        try:
            translated = translator.translate(input, dest=dest).text
        except:
            print("Second failure, skip. ")
            translated = None

    return translated


def aggregate_metadata(input_list):
    aggregated = {}
    for file in tqdm(input_list):
        metadata = []
        with open(file, 'r') as fp:
            metadata = json.load(fp)

        for record in metadata:
            authors = record['authors']
            tags = record['tags']
            for author in authors:
                from_lang = "en"
                if 'en' in author:
                    from_lang = 'en'
                    author_name_ = author[from_lang]
                elif 'jp' in author:
                    from_lang = 'jp'
                    author_name_ = author[from_lang]
                else:
                    from_lang = list(author.keys())[0]
                    author_name_ = author[from_lang]

                author_name = author_name_
                if from_lang in ['jp', 'zh', 'kr']:
                    author_name = translate_offline(author_name_, source="ja", dest='en')

                author_name = author_name.lower()

                if author_name not in aggregated.keys():
                    aggregated[author_name] = {tag['text']: 1 for tag in tags}
                else:
                    existing_info = aggregated[author_name]
                    for tag in tags:
                        tag_text = tag['text']
                        if tag_text in existing_info.keys():
                            existing_info[tag_text] += 1
                        else:
                            existing_info[tag_text] = 1

    return aggregated


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
                    if not file_.lower().endswith(".json"):
                        continue

                    abs_path = os.path.join(root, file_)
                    output_filename = Path(abs_path).stem
                    parent_dir = Path(abs_path).parent
                    if os.path.isdir(str(output)):
                        output_ = Path(str(parent_dir).replace(str(input), str(output)))
                        output_filename_with_extension = str(output_filename) + ".json"
                        output_path = os.path.join(output_, output_filename_with_extension)
                    else:
                        output_path = os.path.join(parent_dir, output_filename + ".aggregated.json")

                    path_list.append(abs_path)

        else:

            for abs_path in Path(input).glob('*.json'):
                abs_path_ = str(abs_path).replace(".tei", "")
                output_filename = Path(abs_path_).stem
                parent_dir = Path(abs_path_).parent
                if os.path.isdir(str(output)):
                    output_ = Path(str(parent_dir).replace(str(input), str(output)))
                    output_filename_with_extension = str(output_filename) + ".aggregated.json"
                    output_path = os.path.join(output_, output_filename_with_extension)
                else:
                    output_path = Path(output)

                path_list.append(abs_path)


        aggregation = aggregate_metadata(path_list)
        with open(output_path, 'w') as fp:
            json.dump(aggregation, fp)

    else:
        print("input should be a directory")
        sys.exit(-1)