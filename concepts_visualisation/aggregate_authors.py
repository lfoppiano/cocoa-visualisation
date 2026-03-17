import argparse
import json
import os
from pathlib import Path

from tqdm import tqdm

GENERIC_CONCEPTS_BATTERY = ["Battery (electricity)"]


def get_author_uniq_key(author):
    author_id = author["id"].lower()
    author_name = author["display_name"].lower().replace(" ", "_") if author["display_name"] is not None else ""
    author_uniq_key = author_id + "###" + author_name
    return author_uniq_key


def get_author_directory(author):
    return get_author_uniq_key(author).replace("https://openalex.org/", "")


def get_work_directory(work):
    return work['id'].replace("https://openalex.org/", "")


def process_coauthors(authors, author_openalex_id, struct):
    for co_author in authors:
        if co_author['id'] == author_openalex_id:
            continue

        co_author_id = get_author_uniq_key(co_author)
        if co_author_id not in struct:
            struct[co_author_id] = 1
        else:
            struct[co_author_id] += 1


def process_keywords(keywords, struct):
    for keyword in keywords:
        if keyword in list(struct.keys()):
            struct[keyword]['freq'] += 1
        else:
            struct[keyword] = {
                'freq': 1
            }


def process_concepts(concepts, struct):
    for concept in concepts:
        concept_name = concept['display_name']
        concept_score = concept['score']
        if concept_name in list(struct.keys()):
            struct[concept_name]['freq'] += 1
            struct[concept_name]['avg_score'] += concept_score
        else:
            struct[concept_name] = {
                'freq': 1,
                'avg_score': concept_score
            }


def calculate_avg(struct):
    for concept_name, concept_obj in struct['non_first_author']['concepts'].items():
        concept_obj['avg_score'] = concept_obj['avg_score'] / concept_obj['freq']

    for concept_name, concept_obj in struct['first_author']['concepts'].items():
        concept_obj['avg_score'] = concept_obj['avg_score'] / concept_obj['freq']


def process_period(works_1990_1999, author_openalex_id):
    struct = {
        "nb_publications": 0,
        "nb_publications_corresp_author": 0,
        "nb_publications_first_author": 0,
        "nb_publications_not_first_author": 0,
        "non_first_author": {
            "concepts": {},
            "keywords": {},
            "co_authors": {}
        },
        "first_author": {
            "concepts": {},
            "keywords": {},
            "co_authors": {}
        },
        "publications": []
    }
    for work in works_1990_1999:
        struct['nb_publications'] += 1
        struct['publications'].append(work['id'])

        # First author
        if len(work['authors']) == 1 or work['authors'][0]['id'] == author_openalex_id:
            struct['nb_publications_first_author'] += 1
            process_concepts(work['concepts'], struct['first_author']['concepts'])
            if 'title' in work and work['title']:
                process_keywords(work['keyterms_T'], struct['first_author']['keywords'])
            if 'abstract' in work and work["abstract"] and work['abstract'] != "Abstract": # Workaround against ceder
                process_keywords(work['keyterms_A'], struct['first_author']['keywords'])
            process_coauthors(work['authors'], author_openalex_id, struct['first_author']['co_authors'])
        else:
            struct['nb_publications_not_first_author'] += 1
            process_concepts(work['concepts'], struct['non_first_author']['concepts'])
            if 'title' in work and work['title']:
                process_keywords(work['keyterms_T'], struct['non_first_author']['keywords'])
            if 'abstract' in work and work["abstract"] and work['abstract'] != "Abstract": # Workaround against ceder
                process_keywords(work['keyterms_A'], struct['non_first_author']['keywords'])
            process_coauthors(work['authors'], author_openalex_id, struct['non_first_author']['co_authors'])

    calculate_avg(struct)
    return struct


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
        if author_dir.startswith("."):
            continue
        works = {
            "1990-1999": {},
            "2000-2009": {},
            "2010-2023": {}
        }
        author_id = "https://openalex.org/" + author_dir
        author_openalex_id = "https://openalex.org/" + str.capitalize(author_dir).split("###")[0]
        author = {
            "id": author_dir,
            "openalex_id": author_openalex_id,
            "periods": works
        }
        authors[author_id] = author
        author_abs_dir = os.path.join(output_authors_files_dir, author_dir)

        works_1990_1999 = []
        works_2000_2009 = []
        works_2010_2023 = []

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

        works["1990-1999"] = process_period(works_1990_1999, author_openalex_id)
        works["2000-2009"] = process_period(works_2000_2009, author_openalex_id)
        works["2010-2023"] = process_period(works_2010_2023, author_openalex_id)

        author["nb_publications_corresp_author"] = sum(
            [works[key]['nb_publications_corresp_author'] for key in works.keys()])
        author["nb_publications_first_author"] = sum(
            [works[key]['nb_publications_first_author'] for key in works.keys()])
        author["nb_publications_not_first_author"] = sum(
            [works[key]['nb_publications_not_first_author'] for key in works.keys()])
        author["nb_publications"] = author["nb_publications_corresp_author"] + author["nb_publications_first_author"] + \
                                    author["nb_publications_not_first_author"]

    with open(os.path.join(output, "authors.json"), 'w') as fo:
        json.dump(authors, fo, indent=4)
