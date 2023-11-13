import argparse
import json
import os
from pathlib import Path

from keybert import KeyBERT
from keyphrase_vectorizers import KeyphraseCountVectorizer
from tqdm import tqdm

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Extract keywords from a tree of txt files. "
                    "In the output directory the same input tree is reproduced. "
                    "The output files are stored as JSON. ")

    parser.add_argument("--input-dir",
                        help="Input directory of text file",
                        required=True)
    parser.add_argument("--output-dir",
                        required=True,
                        help="Output directory")

    args = parser.parse_args()

    input_dir = args.input_dir
    output_dir = args.output_dir

    kw_model = KeyBERT()
    vectorizer = KeyphraseCountVectorizer()

    counter = 0
    path_list = []
    path_list_grouped = []
    for root, dirs, files in tqdm(os.walk(input_dir), desc="Scanning filesystem"):
        # Manage to create the directories
        for dir in dirs:
            abs_path_dir = os.path.join(root, dir)
            output_path = abs_path_dir.replace(str(input_dir), str(output_dir))
            if not os.path.exists(output_path):
                os.makedirs(output_path)

        for file_ in files:
            if not file_.lower().endswith(".txt"):
                continue

            abs_path = os.path.join(root, file_)
            output_filename = Path(abs_path).stem
            parent_dir = Path(abs_path).parent
            output_ = Path(str(parent_dir).replace(str(input_dir), str(output_dir)))
            output_filename_with_extension = str(output_filename) + ".json"
            output_path = os.path.join(output_, output_filename_with_extension)

            path_list.append((abs_path, output_path))

            counter += 1
            if counter % 1000 == 0:
                path_list_grouped.append(path_list)
                path_list = []

    if len(path_list) > 0:
        path_list_grouped.append(path_list)

    accumulated_files = []
    for group in tqdm(path_list_grouped, desc="Extracting keywords"):
        batch_output_file = []
        batch_content = []
        for input_path, output_path in group:
            accumulated_file = ""
            with open(input_path, 'r') as fi:
                title = fi.readline()
                accumulated_file += title.strip()
                abstract = fi.readline()
                if "abstract" == str.lower(abstract.strip()):
                    abstract = fi.readline()
                accumulated_file += abstract.strip()

                batch_output_file.append(output_path)
                batch_content.append(accumulated_file)

        keywords = kw_model.extract_keywords(batch_content, vectorizer=vectorizer, top_n=5)
        for idk, keyword in enumerate(keywords):
            print(idk)
            with open(batch_output_file[idk], 'w') as fo:
                json.dump(keyword, fo)
