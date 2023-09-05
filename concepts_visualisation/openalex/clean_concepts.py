import argparse
import json
import os
from pathlib import Path

import pyalex
from dotenv import load_dotenv
from pyalex import Concepts
from tqdm import tqdm

from concepts_visualisation.openalex.aggregate_topics import GENERIC_CONCEPTS

load_dotenv(verbose=True, override=True)

pyalex.config.email = os.environ['OPENALEX_CONFIG_EMAIL']
pyalex.config.api_key = os.environ['OPENALEX_API_KEY']


def cleanup_concepts(data):
    aggregated = {}

    for record in tqdm(data, desc="Cleanup"):
        ## Remove concepts related to battery and ancestors
        raw_concepts = list(filter(lambda x: x['display_name'] not in GENERIC_CONCEPTS, record['concepts']))

        ## Filter ancestors recursively
        filtered_concepts = cleanup_recursive(raw_concepts, [])
        record['concepts_filtered'] = filtered_concepts

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
    if os.path.exists(cache_file_path):
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

    parser.add_argument("--input", help="Input file", required=True, type=Path)
    parser.add_argument("--output", help="Output directory", required=True, type=Path)

    args = parser.parse_args()

    input = args.input
    output = args.output



    # for concept in Concepts().get(per_page=200):
    for page in tqdm(Concepts().paginate(per_page=200, n_max=70000), desc="concept page"):
        for concept in tqdm(page, desc="Downloading concepts"):
            id = concept['id']
            cache_file_path = get_cache_path(id)
            if not os.path.exists(cache_file_path):
                with open(cache_file_path, 'w') as fc:
                    json.dump(concept, fc)



    with open(input, 'r') as fp:
        data = json.load(fp)

    processed_records = cleanup_concepts(data)

    with open(output, 'w') as fo:
        json.dump(processed_records, fo)
