import argparse
import json
import os
from collections import OrderedDict
from pathlib import Path

from tqdm import tqdm


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
            if 'id' not in author or not author['id']:
                continue
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
        description="Aggregate by authors and sort by number of publications, filter the first 10000 and incluse possible authors from a list")

    parser.add_argument("--input-corpus", help="Input directory containing the dumps", required=True, type=Path)
    parser.add_argument("--output", help="Output directory where the aggregation will be saved", required=True,
                        type=Path)
    parser.add_argument("--author-list", help="File containing a list of authors to be kept in the final output",
                        required=False,
                        type=Path, default=None)

    args = parser.parse_args()

    input_corpus = args.input_corpus
    output_dir = args.output
    author_list_file = args.author_list
    os.makedirs(output_dir, exist_ok=True)

    author_list = None
    if author_list_file:
        with open(author_list_file, 'r') as alf:
            author_list = [author.strip() for author in alf]

    excluded = []
    aggregated = {}
    for filename in tqdm(os.listdir(input_corpus)):
        with open(os.path.join(input_corpus, filename)) as dump_file:
            works = json.load(dump_file)

        aggregated = aggregate(works, aggregated)
        aggregated_sorted = OrderedDict(sorted(aggregated.items(), key=lambda item: item[1], reverse=True))
        aggregated_top_10000 = dict(list(aggregated_sorted.items())[:10000])

    if author_list:
        for author_id in author_list:
            if author_id not in excluded:
                if len(list(filter(lambda item: item[0].startswith(str.lower(author_id)),
                                   aggregated_top_10000.items()))) == 0:
                    item_to_be_added = list(
                        filter(lambda item: item[0].startswith(str.lower(author_id)), aggregated_sorted.items()))
                    if len(item_to_be_added) > 0:
                        aggregated_top_10000[item_to_be_added[0][0]] = item_to_be_added[0][1]
                        excluded.append(author_id)
                    else:
                        print("Item {} is not found.".format(author_id))

    with(open(os.path.join(output_dir, "authors_aggregated_top10000_by_publications.json"), 'w')) as fo:
        json.dump(aggregated_top_10000, fo)
