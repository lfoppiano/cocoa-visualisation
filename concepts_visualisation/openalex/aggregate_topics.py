import argparse
import json
import os
from pathlib import Path

from tqdm import tqdm

GENERIC_CONCEPTS = ["Battery (electricity)", "Power (physics)", "Physics", "Thermodynamics", "Quantum mechanics"]


def get_author_uniq_key(author):
    author_id = author["id"].lower()
    author_name = author["display_name"].lower().replace(" ", "_") if author["display_name"] is not None else ""
    author_uniq_key = author_id + "###" + author_name
    return author_uniq_key


def aggregate(data):
    aggregated = {}

    years = set()
    for record in tqdm(data, desc="Calculate years interval"):
        if 'publication_year' not in record:
            year = "N/A"
        else:
            year = str(int(record['publication_year']))

        years.add(year)

    sorted_years = sorted(years)

    for record in tqdm(data, desc="Aggregate"):
        authors = record['authors']
        concepts = list(filter(lambda x: x['display_name'] not in GENERIC_CONCEPTS, record['concepts']))
        keyterms_A = record['keyterms_A']
        keyterms_T = record['keyterms_T']
        year = str(int(record['publication_year']))

        for author in authors:
            author_uniq_key = get_author_uniq_key(author)
            if str(author_uniq_key) not in aggregated.keys():
                author_obj = {}
                aggregated[str(author_uniq_key)] = author_obj

                for y in filter(lambda y_: y_ != year, sorted_years):
                    author_obj[y] = {"concepts": {},
                                     "keyterms_T": {},
                                     "keyterms_A": {},
                                     "co_authors": {}
                                     }

                author_obj[year] = {
                    "concepts": {tag['display_name'].lower(): 1 for tag in concepts},
                    "keyterms_T": {tag['display_name'].lower(): 1 for tag in keyterms_T},
                    "keyterms_A": {tag['display_name'].lower(): 1 for tag in keyterms_A},
                    "co_authors": {get_author_uniq_key(co_author): 1 for co_author in authors if
                                   get_author_uniq_key(co_author) != author_uniq_key}
                }

            else:
                existing_info_author = aggregated[str(author_uniq_key)][year]
                for tag in concepts:
                    tag_text = tag['display_name'].lower()
                    if tag_text in existing_info_author['concepts'].keys():
                        existing_info_author["concepts"][tag_text] += 1
                    else:
                        existing_info_author["concepts"][tag_text] = 1

                for tag in keyterms_T:
                    tag_text = tag['display_name'].lower()
                    if tag_text in existing_info_author["keyterms_T"].keys():
                        existing_info_author["keyterms_T"][tag_text] += 1
                    else:
                        existing_info_author["keyterms_T"][tag_text] = 1

                for tag in keyterms_A:
                    tag_text = tag['display_name'].lower()
                    if tag_text in existing_info_author["keyterms_A"].keys():
                        existing_info_author["keyterms_A"][tag_text] += 1
                    else:
                        existing_info_author["keyterms_A"][tag_text] = 1

                for co_author in authors:
                    if get_author_uniq_key(co_author) == author_uniq_key:
                        continue

                    if get_author_uniq_key(co_author) in existing_info_author["co_authors"].keys():
                        existing_info_author["co_authors"][get_author_uniq_key(co_author)] += 1
                    else:
                        existing_info_author["co_authors"][get_author_uniq_key(co_author)] = 1

    return aggregated


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Aggregate keywords and concepts of authors and co-authors")

    parser.add_argument("--input", help="Input file or directory", required=True, type=Path)
    parser.add_argument("--output", help="Output directory", required=True, type=Path)

    args = parser.parse_args()

    input = args.input
    output = args.output

    with open(input, 'r') as fp:
        data = json.load(fp)

    aggregated = aggregate(data)

    for author_id, author_data in tqdm(aggregated.items(), desc="Write"):
        new_data = {author_id: author_data}
        clean_filename = author_id.replace("https://openalex.org/", "").replace("/", "$")
        child_directory_name = clean_filename.split("###")[1][:3]
        child_directory_abs = os.path.join(output, child_directory_name)
        if not os.path.exists(child_directory_abs):
            os.makedirs(child_directory_abs)
        output_file = os.path.join(child_directory_abs, clean_filename + ".json")
        if os.path.exists(output_file):
            print(output_file, "already exists. Skipping.")
        else:
            with open(output_file, 'w') as fo:
                json.dump(new_data, fo)
