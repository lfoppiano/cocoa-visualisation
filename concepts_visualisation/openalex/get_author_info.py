import argparse
import json
import os
from collections import OrderedDict
from pathlib import Path

from tqdm import tqdm

GENERIC_CONCEPTS_BATTERY = ["Battery (electricity)", "Power (physics)", "Physics", "Thermodynamics",
                            "Quantum mechanics"]


def get_author_uniq_key(author):
    author_id = author["id"].lower()
    author_name = author["display_name"].lower().replace(" ", "_") if author["display_name"] is not None else ""
    author_uniq_key = author_id + "###" + author_name
    return author_uniq_key


def aggregate(data, aggregated={}):
    # years = set()
    # for record in tqdm(data, desc="Calculate years interval"):
    #     if 'publication_year' not in record:
    #         year = "N/A"
    #     else:
    #         year = str(int(record['publication_year']))
    #
    #     years.add(year)
    #
    # sorted_years = sorted(years)

    for record in data:
        authors = record['authors']
        # year = str(int(record['publication_year']))

        for author in authors:
            author_uniq_key = get_author_uniq_key(author)
            if str(author_uniq_key) not in aggregated.keys():
                # author_obj = 0
                aggregated[str(author_uniq_key)] = 1
                # if year not in author_obj:
                #     author_obj[year] = {}

                # for y in filter(lambda y_: y_ != year, sorted_years):
                #     author_obj[y] = {"co_authors": {}, "publications": 0}

                # author_obj[year] = {
                #     "co_authors": {get_author_uniq_key(co_author): 1 for co_author in authors if
                #                    get_author_uniq_key(co_author) != author_uniq_key},
                #     "publications": 1
                # }
                # author_obj: 1

            else:
                aggregated[str(author_uniq_key)] += 1
                # if year not in author_obj:
                #     author_obj[year] = {"co_authors": {}}
                # existing_info_author = author_obj[year]

                # for co_author in authors:
                #     if get_author_uniq_key(co_author) == author_uniq_key:
                #         continue
                #
                #     author_obj += 1

                    # if get_author_uniq_key(co_author) in existing_info_author["co_authors"].keys():
                    #     existing_info_author["co_authors"][get_author_uniq_key(co_author)] += 1
                    # else:
                    #     existing_info_author["co_authors"][get_author_uniq_key(co_author)] = 1

                    # if 'publications' in existing_info_author:
                    #     existing_info_author['publications'] += 1
                    # else:
                    #     existing_info_author['publications'] = 1
    return aggregated


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Aggregate by authors and sort by number of publications")

    parser.add_argument("--input-corpus", help="Input directory containing the dumps", required=True, type=Path)
    parser.add_argument("--output", help="Output directory where the aggregation will be saved", required=True,
                        type=Path)

    args = parser.parse_args()

    input_corpus = args.input_corpus
    output_dir = args.output
    os.makedirs(output_dir, exist_ok=True)

    aggregated = {}
    for filename in tqdm(os.listdir(input_corpus)):
        with open(os.path.join(input_corpus, filename)) as dump_file:
            works = json.load(dump_file)

        aggregated = aggregate(works, aggregated)
        aggregated_sorted = OrderedDict(sorted(aggregated.items(), key=lambda item: item[1], reverse=True))
        aggregated_top_10000 = dict(list(aggregated_sorted.items())[:10000])

    with(open(os.path.join(output_dir, "authors_aggregated_top10000_by_publications.json"), 'w')) as fo:
        json.dump(aggregated_top_10000, fo)
