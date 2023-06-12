import json
import os

import pyalex
from pyalex import Works
from tqdm import tqdm

pyalex.config.email = "luca@foppiano.org"
pyalex.config.api_key = "iniWr65e5XQkiufqVWJVc9"

pager = Works().filter(concept={"id": "https://openalex.org/C555008776"}).paginate(per_page=200, n_max=200000)

id = 0
for page in tqdm(pager):
    work_page = []
    with open("openalex/data_dump" + str(id) + ".json", 'w') as fw:
        for work in page:
            output_work = {}

            for key in ['id', 'doi', 'title', 'display_name', 'publication_year', 'publication_date', 'language']:
                if key in work:
                    output_work[key] = work[key]

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
