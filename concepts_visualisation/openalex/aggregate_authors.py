import argparse
import json
import os
from pathlib import Path

from tqdm import tqdm

GENERIC_CONCEPTS_BATTERY = ["Battery (electricity)", "Power (physics)", "Physics", "Thermodynamics",
                            "Quantum mechanics"]


def get_author_uniq_key(author):
    author_id = author["id"].lower()
    author_name = author["display_name"].lower().replace(" ", "_") if author["display_name"] is not None else ""
    author_uniq_key = author_id + "###" + author_name
    return author_uniq_key


def get_author_directory(author):
    return get_author_uniq_key(author).replace("https://openalex.org/", "")


def get_work_directory(work):
    return work['id'].replace("https://openalex.org/", "")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Aggregate publications by authors")

    parser.add_argument("--input-corpus", help="Directory of the dump corpus", required=True, type=Path)
    parser.add_argument("--input-authors", help="Authors file in JSON dictionary", required=True, type=Path)
    parser.add_argument("--output", help="Output directory", required=True, type=Path)

    args = parser.parse_args()

    input_corpus = args.input_corpus
    input_authors = args.input_authors
    output = args.output

    with open(input_authors, 'r') as ia:
        author_list = json.load(ia)

    output_authors_files_dir = os.path.join(output, "authors")

    if not os.path.exists(output_authors_files_dir):
        for filename in tqdm(os.listdir(input_corpus)):
            with open(os.path.join(input_corpus, filename)) as dump_file:
                works = json.load(dump_file)

            for work in works:
                for author in work['authors']:
                    author_uniq_key = get_author_uniq_key(author)
                    author_dir_name = get_author_directory(author)
                    if author_uniq_key in author_list.keys():
                        author_dir = os.path.join(output_authors_files_dir, author_dir_name)
                        os.makedirs(author_dir, exist_ok=True)
                        work_output_file = os.path.join(author_dir, get_work_directory(work)) + ".json"
                        with open(work_output_file, 'w') as wo:
                            json.dump(work, wo)

    authors = {}

    for author_dir in tqdm(os.listdir(output_authors_files_dir)):
        works_1990_1999 = []
        works_2000_2009 = []
        works_2010_2023 = []

        works = {
            "1990-1999": works_1990_1999,
            "2000-2009": works_2000_2009,
            "2010-2023": works_2010_2023
        }
        author_id = "https://openalex.org/" + author_dir
        author_openalex_id = "https://openalex.org/" + str.capitalize(author_dir).split("###")[0]
        author = {
            "id": author_dir,
            "openalex_id": author_openalex_id,
            "publications": author_list[author_id],
            "publications_first_author": 0,
            "works": works
        }
        authors[author_id] = author
        author_abs_dir = os.path.join(output_authors_files_dir, author_dir)
        for work_file in os.listdir(author_abs_dir):
            if not work_file.endswith(".json"):
                continue

            work_abs_dir = os.path.join(author_abs_dir, work_file)

            with open(work_abs_dir, 'r') as fo:
                work = json.load(fo)

            author_obj = list(filter(lambda w: w['id'] == author_openalex_id, work['authors']))[0]
            author['orcid'] = author_obj['orcid']

            publication_year = work['publication_year'] if 'publication_year' in work else 0

            if 1990 <= publication_year <= 1999:
                works_1990_1999.append(work)
            elif 2000 <= publication_year <= 2009:
                works_2000_2009.append(work)
            elif 2010 <= publication_year <= 2023:
                works_2010_2023.append(work)

    with open(os.path.join(output, "authors.json"), 'w') as fo:
        json.dump(authors, fo)
