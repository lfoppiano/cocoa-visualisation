import argparse
import ast
import json
from pathlib import Path

import pandas as pd
from tqdm import tqdm


def aggregate(data):
    aggregated = {}

    for record in tqdm(data):
        authors = record['authors']
        tags = record['tags']
        for author in authors:
            author_id = author["id"].lower()
            author_name = author["name"].lower() if author["name"] is not None else " "

            if str(author_id + "___" + author_name) not in aggregated.keys():
                aggregated[str(author_id + "___" + author_name)] = {tag['text']: 1 for tag in tags}
            else:
                existing_info = aggregated[str(author_id + "___" + author_name)]
                for tag in tags:
                    tag_text = tag['text'].lower()
                    if tag_text in existing_info.keys():
                        existing_info[tag_text] += 1
                    else:
                        existing_info[tag_text] = 1

    return aggregated


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Converts back from CSV to JSON")

    parser.add_argument("--input", help="Input file or directory", required=True, type=Path)

    args = parser.parse_args()

    input = args.input

    with open(input) as f:
        df = pd.read_csv(f)

    output = []
    for row in range(0, len(df)):
        if pd.isna(df.loc[row]['authors']):
            print("Authors are null, skipping!")
            continue

        item = {
            "authors": ast.literal_eval(df.loc[row]['authors']),
            "concepts": ast.literal_eval(df.loc[row]['concepts']),
            "keyterms_T": [
                {
                    "display_name": keyterm[0],
                    "score": keyterm[1]
                } for keyterm in ast.literal_eval(df.loc[row]['keyterms_T'])],
            "keyterms_A": [
                {
                    "display_name": keyterm[0],
                    "score": keyterm[1]
                } for keyterm in ast.literal_eval(df.loc[row]['keyterms_A'])]
        }

        keys = [key for key in df.loc[row].keys() if key not in list(item.keys()) + ['Unnamed: 0.1', 'Unnamed: 0']]

        for key in keys:
            item[key] = df.loc[row][key]
        output.append(item)

    # aggregated = aggregate(output)

    with open("output.json", 'w') as fo:
        json.dump(output, fo)

    print("fine")
