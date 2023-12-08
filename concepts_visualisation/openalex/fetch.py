import argparse
import json
import os
import sys
from pathlib import Path

import pyalex
from dotenv import load_dotenv
from pyalex import Works
from tqdm import tqdm

load_dotenv()

pyalex.config.email = os.environ['OPENALEX_CONFIG_EMAIL']
pyalex.config.api_key = os.environ['OPENALEX_API_KEY']


def fetch_openalex_works(concept_id, output_path, per_page=200, n_max=2000000, original=False):
    pager = Works().filter(concept={"id": "https://openalex.org/" + concept_id}).paginate(per_page=per_page,
                                                                                          n_max=n_max)
    id = 0
    for page in tqdm(pager):
        work_page = []
        with open(os.path.join(output_path, "data_dump" + str(id) + ".json"), 'w') as fw:
            for work in page:
                if original:
                    output_work = work
                else:
                    output_work = get_work(work)
                work_page.append(output_work)

            json.dump(work_page, fw)
            id += 1


def get_work(input_work):
    output_work = {}
    for key in ['id', 'doi', 'title', 'display_name', 'publication_year', 'publication_date', 'language']:
        if key in input_work:
            output_work[key] = input_work[key]
    authorships = input_work['authorships'] if 'authorships' in input_work else []
    output_work['authors'] = []
    for author in authorships:
        output_author = {}

        if 'id' in author['author']:
            output_author["id"] = author['author']['id']
        if 'position' in author['author']:
            output_author["position"] = author['author_position']
        if 'orcid' in author['author']:
            output_author["orcid"] = author['author']['orcid']
        if 'display_name' in author['author']:
            output_author["display_name"] = author['author']['display_name']

        affiliations = author['institutions'] if 'institutions' in author else []
        output_affiliations = []
        for affiliation in affiliations:
            output_affiliation = {}
            if 'id' in affiliation:
                output_affiliation["id"] = affiliation['id']
            if "country_code" in affiliation:
                output_affiliation['country'] = affiliation['country_code']
            if 'type' in affiliation:
                output_affiliation["type"] = affiliation['type']
            if 'display_name' in affiliation:
                output_affiliation['display_name'] = affiliation['display_name']

            output_affiliations.append(output_affiliation)
        output_author['institutions'] = output_affiliations
        output_work['authors'].append(output_author)
    if input_work['abstract_inverted_index'] is not None:
        output_work['abstract'] = input_work['abstract']
    if 'concepts' in input_work:
        work_concepts = []
        for concept in input_work['concepts']:
            work_concepts.append(
                {
                    "id": concept['id'],
                    "wikidata": concept['wikidata'],
                    "display_name": concept['display_name'],
                    "level": concept['level'],
                    "score": concept['score']
                }
            )

        output_work['concepts'] = work_concepts
    return output_work


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Fetch OpenAlex works")

    parser.add_argument("--base-concept",
                        required=False,
                        default="C555008776",
                        help="OpenAlex base concept. Default: C555008776 (battery)")
    parser.add_argument("--output",
                        help="Output directory. If it does not exists it will be created.",
                        required=True,
                        type=Path)
    parser.add_argument("--original",
                        help="Save the original records from openalex",
                        required=False,
                        default=False)

    args = parser.parse_args()

    base_concept = args.base_concept
    output = args.output

    if not os.path.isdir(output):
        print("--output should indicate a directory. ")
        sys.exit(-1)

    os.makedirs(output, exist_ok=True)

    fetch_openalex_works(base_concept, output, original=args.original)
