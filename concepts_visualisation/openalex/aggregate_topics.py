import argparse
import ast
import json
from pathlib import Path

import pandas as pd
from tqdm import tqdm

GENERIC_CONCEPTS = ["Battery (electricity)", "Power (physics)", "Physics", "Thermodynamics", "Quantum mechanics"]

def get_author_uniq_key(author):
    author_id = author["id"].lower()
    author_name = author["display_name"].lower().replace(" ", "_") if author["display_name"] is not None else ""
    author_uniq_key = author_id + "###" + author_name
    return author_uniq_key

def aggregate(data):
    aggregated = {}

    for record in tqdm(data):
        authors = record['authors']
        concepts = list(filter(lambda x: x['display_name'] not in GENERIC_CONCEPTS, record['concepts']))
        keyterms_A = record['keyterms_A']
        keyterms_T = record['keyterms_T']

        for author in authors:
            author_uniq_key = get_author_uniq_key(author)
            if str(author_uniq_key) not in aggregated.keys():
                aggregated[str(author_uniq_key)] = {
                    "concepts": {tag['display_name'].lower(): 1 for tag in concepts},
                    "keyterms_T": {tag['display_name'].lower(): 1 for tag in keyterms_T},
                    "keyterms_A": {tag['display_name'].lower(): 1 for tag in keyterms_A},
                    "co_authors": {get_author_uniq_key(co_author): 1 for co_author in authors if
                                   get_author_uniq_key(co_author) != author_uniq_key}
                }
            else:
                existing_info = aggregated[str(author_uniq_key)]
                for tag in concepts:
                    tag_text = tag['display_name'].lower()
                    if tag_text in existing_info['concepts'].keys():
                        existing_info["concepts"][tag_text] += 1
                    else:
                        existing_info["concepts"][tag_text] = 1

                for tag in keyterms_T:
                    tag_text = tag['display_name'].lower()
                    if tag_text in existing_info["keyterms_T"].keys():
                        existing_info["keyterms_T"][tag_text] += 1
                    else:
                        existing_info["keyterms_T"][tag_text] = 1

                for tag in keyterms_A:
                    tag_text = tag['display_name'].lower()
                    if tag_text in existing_info["keyterms_A"].keys():
                        existing_info["keyterms_A"][tag_text] += 1
                    else:
                        existing_info["keyterms_A"][tag_text] = 1

                for co_author in authors:
                    if get_author_uniq_key(co_author) == author_uniq_key:
                        continue

                    if get_author_uniq_key(co_author) in existing_info["co_authors"].keys():
                        existing_info["co_authors"][get_author_uniq_key(co_author)] += 1
                    else:
                        existing_info["co_authors"][get_author_uniq_key(co_author)] = 1

    return aggregated


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Aggregate keywords and concepts of authors and co-authors")

    parser.add_argument("--input", help="Input file or directory", required=True, type=Path)

    args = parser.parse_args()

    input = args.input

    with open(input, 'r') as fp:
        data = json.load(fp)

    aggregated = aggregate(data)

    with open("output.json", 'w') as fo:
        json.dump(aggregated, fo)
