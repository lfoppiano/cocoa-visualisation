import argparse
import json
import os
from pathlib import Path

from tqdm import tqdm


def dump_files(works_list, output, name, batch_size=500):
    tmp_work = []
    seq = 1
    counter = 1
    for work in works_list:
        tmp_work.append(work)
        if counter % batch_size == 0:
            with open(os.path.join(output, f"{name}.{seq}.json"), 'w') as fo:
                json.dump(tmp_work, fo)
            seq += 1
            counter = 0
            tmp_work = []
        counter +=1

    if len(tmp_work) > 0:
        with open(os.path.join(output, f"{name}.{seq}.json"), 'w') as fo:
            json.dump(tmp_work, fo)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Aggregate publications by authors")

    parser.add_argument("--input-corpus", help="Directory of the dump corpus", required=True, type=Path)
    parser.add_argument("--batch-size", help="Number of works for output file.", required=False, default=500, type=int)
    parser.add_argument("--output", help="Output directory", required=True, type=Path)

    args = parser.parse_args()

    input_corpus = args.input_corpus
    output = args.output
    batch_size = args.batch_size

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

    dump_files(works_1990_1999, output, "works_1990_1999", batch_size=batch_size)
    dump_files(works_2000_2009, output, "works_2000_2009", batch_size=batch_size)
    dump_files(works_2010_2023, output, "works_2010_2023", batch_size=batch_size)
    dump_files(works_other, output, "works_other", batch_size=batch_size)
