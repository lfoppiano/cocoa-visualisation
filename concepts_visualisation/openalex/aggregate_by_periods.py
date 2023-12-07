import argparse
import json
import os
from pathlib import Path

from tqdm import tqdm

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Aggregate publications by authors")

    parser.add_argument("--input-corpus", help="Directory of the dump corpus", required=True, type=Path)
    parser.add_argument("--output", help="Output directory", required=True, type=Path)

    args = parser.parse_args()

    input_corpus = args.input_corpus
    output = args.output

    works_1990_1999 = []
    works_2000_2009 = []
    works_2010_2023 = []
    works_other = []

    for filename in tqdm(os.listdir(input_corpus)):
        with open(os.path.join(input_corpus, filename)) as dump_file:
            works = json.load(dump_file)

        for work in works:
            publication_year = work['publication_year'] if 'publication_year' in work else 0

            if 1990 <= publication_year <= 1999:
                works_1990_1999.append(work)
            elif 2000 <= publication_year <= 2009:
                works_2000_2009.append(work)
            elif 2010 <= publication_year <= 2023:
                works_2010_2023.append(work)
            else:
                works_other.append(work)

    with open(os.path.join(output, "works_1990_1999.json"), 'w') as fo:
        json.dump(works_1990_1999, fo)

    with open(os.path.join(output, "works_2000_2009.json"), 'w') as fo:
        json.dump(works_2000_2009, fo)

    with open(os.path.join(output, "works_2010_2023.json"), 'w') as fo:
        json.dump(works_2010_2023, fo)

    with open(os.path.join(output, "works_other.json"), 'w') as fo:
        json.dump(works_other, fo)
