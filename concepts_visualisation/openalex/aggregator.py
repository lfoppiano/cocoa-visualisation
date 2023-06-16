import argparse
import json
import os
import sys
from pathlib import Path

from tqdm import tqdm

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
                author_id = author["id"].lower()
                author_name = author["id"].lower()

                if author_id not in [key[0] for key in aggregated.keys()]:
                    aggregated[(author_id, author_name)] = {tag['text']: 1 for tag in tags}
                else:
                    existing_info = aggregated[(author_id, author_name)]
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

    args = parser.parse_args()

    input = args.input
    output = args.output
    recursive = args.recursive

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