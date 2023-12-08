import argparse
import json
import os
from pathlib import Path

import pyalex
from dotenv import load_dotenv
from pyalex import Concepts
from tqdm import tqdm

from concepts_visualisation.openalex.aggregate_authors import GENERIC_CONCEPTS_BATTERY

load_dotenv(verbose=True, override=True)

pyalex.config.email = os.environ['OPENALEX_CONFIG_EMAIL']
pyalex.config.api_key = os.environ['OPENALEX_API_KEY']


def cleanup_concepts(data):
    for record in tqdm(data, desc="Cleanup"):
        # Remove concepts related to battery (including their ancestors)
        raw_concepts_without_batteries_related = list(
            filter(lambda x: x['display_name'] not in GENERIC_CONCEPTS_BATTERY or x['score'] == 0.0,
                   record['concepts']))

        # Filter ancestors recursively
        # filtered_concepts = cleanup_recursive(raw_concepts_without_batteries_related, [])
        record['concepts'] = raw_concepts_without_batteries_related

    return data


def cleanup_recursive(concepts, cleaned_concepts, cache=".tmp"):
    os.makedirs(cache, exist_ok=True)

    if len(concepts) == 0:
        return cleaned_concepts

    sorted_raw_concepts = list(sorted(concepts, key=lambda k: k['level'], reverse=True))

    current_concept = sorted_raw_concepts[0]
    id = current_concept['id']
    # level = current_concept['level']

    cache_file_path = get_cache_path(id, cache)
    if os.path.exists(cache_file_path) and os.path.getsize(cache_file_path) > 0:
        with open(cache_file_path, 'r') as fc:
            remote_data_concept = json.load(fc)
    else:
        remote_data_concept = Concepts()[id]
        with open(cache_file_path, 'w') as fc:
            json.dump(remote_data_concept, fc)

    cleaned_concepts.append(current_concept)
    ancestors_ids = [ancestor['id'] for ancestor in remote_data_concept['ancestors']]

    new_concepts_list = [c for c in concepts if c['id'] not in ancestors_ids and c['id'] != id]

    return cleanup_recursive(new_concepts_list, cleaned_concepts)


def get_cache_path(id, cache=".tmp"):
    os.makedirs(cache, exist_ok=True)
    cache_file_name = id.replace("https://openalex.org/", "") + ".json"
    os.makedirs(os.path.join(cache, cache_file_name[0:2]), exist_ok=True)
    cache_file_path = os.path.join(cache, cache_file_name[0:2], cache_file_name)
    return cache_file_path


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Cleanup concepts from battery_data_topics")

    parser.add_argument("--input-corpus",
                        help="Input corpus, normally in a directly starting with 'dump'",
                        required=True,
                        type=Path)
    parser.add_argument("--from-year",
                        help="Filter from year (included)",
                        default=1990,
                        required=False)
    parser.add_argument("--cache-concepts",
                        required=False,
                        default=False,
                        action="store_true")
    parser.add_argument("--output",
                        help="Output directory",
                        required=True,
                        type=Path)

    args = parser.parse_args()

    input_corpus = args.input_corpus
    cache_concepts = args.cache_concepts
    output_dir = args.output
    from_year = args.from_year

    os.makedirs(output_dir, exist_ok=True)

    # if cache_concepts:
    #     for page in tqdm(Concepts().paginate(per_page=200, n_max=70000), desc="concept page"):
    #         for concept in page:
    #             id = concept['id']
    #             cache_file_path = get_cache_path(id)
    #             if not os.path.exists(cache_file_path):
    #                 with open(cache_file_path, 'w') as fc:
    #                     json.dump(concept, fc)

    for filename in tqdm(os.listdir(input_corpus)):
        with open(os.path.join(input_corpus, filename)) as dump_file:
            works = json.load(dump_file)

        filtered_works = list(filter(lambda w: 'publication_year' in w and w['publication_year'] >= from_year, works))

        processed_works = cleanup_concepts(filtered_works)

        with(open(os.path.join(output_dir, Path(filename).stem + ".json"), 'w')) as fo:
            json.dump(processed_works, fo)
