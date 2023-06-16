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

            if str(author_id+"___"+author_name) not in aggregated.keys():
                aggregated[str(author_id+"___"+author_name)] = {tag['text']: 1 for tag in tags}
            else:
                existing_info = aggregated[str(author_id+"___"+author_name)]
                for tag in tags:
                    tag_text = tag['text'].lower()
                    if tag_text in existing_info.keys():
                        existing_info[tag_text] += 1
                    else:
                        existing_info[tag_text] = 1

    return aggregated


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Converter TSV to XML (Grobid training data based on TEI)")

    parser.add_argument("--input", help="Input file or directory", required=True, type=Path)

    args = parser.parse_args()

    input = args.input


    with open(input) as f:
        df = pd.read_csv(f)

    output = []
    for row in range(0, len(df)):
        item = {
            "id": df.loc[row]['id'],
            "authors": [{"id": author['id'], "name": author['display_name']} for author in ast.literal_eval(df.loc[row]['authors'])],
            "tags": [{"text": concept['display_name'].lower()} for concept in ast.literal_eval(df.loc[row]['concepts'])],
        }
        item['tags'].extend([{"text": keyterm[0]} for keyterm in ast.literal_eval(df.loc[row]['keyterms'])])
        output.append(item)


    aggregated = aggregate(output)

    with open("output.json", 'w') as fo:
        json.dump(aggregated, fo)



