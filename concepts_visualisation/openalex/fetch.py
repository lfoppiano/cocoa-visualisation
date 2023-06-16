import json
import os

import pyalex
from dotenv import load_dotenv
from pyalex import Works
from tqdm import tqdm

load_dotenv()

pyalex.config.email = os.environ['OPENALEX_CONFIG_EMAIL']
pyalex.config.api_key = os.environ['OPENALEX_API_KEY']

pager = Works().filter(concept={"id": "https://openalex.org/C555008776"}).paginate(per_page=200, n_max=200000)

id = 0
for page in tqdm(pager):
    work_page = []
    with open("resources/data/openalex/data_dump" + str(id) + ".json", 'w') as fw:
        for work in page:
            output_work = {}

            for key in ['id', 'doi', 'title', 'display_name', 'publication_year', 'publication_date', 'language']:
                if key in work:
                    output_work[key] = work[key]

            authorships = work['authorships'] if 'authorships' in work else []
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

            if work['abstract_inverted_index'] is not None:
                output_work['abstract'] = work['abstract']

            if 'concepts' in work:
                work_concepts = []
                for concept in work['concepts']:
                    work_concepts.append(
                        {
                            "id": concept['id'],
                            "wikidata": concept['wikidata'],
                            "display_name": concept['display_name'],
                            "level": concept['level']
                        }
                    )

                output_work['concepts'] = work_concepts

            work_page.append(output_work)

        json.dump(work_page, fw)
        id += 1
