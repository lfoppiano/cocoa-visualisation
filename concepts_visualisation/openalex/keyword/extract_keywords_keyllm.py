import argparse
import json
import os
import sys
from math import ceil
from pathlib import Path

import dotenv
import openai
from keybert.llm import OpenAI

dotenv.load_dotenv(override=True)

from keybert import KeyLLM
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

client = openai.OpenAI()
chatgpt = OpenAI(client, model="gpt-3.5-turbo", chat=True)


def process_single(input_file, output_file, model):
    with open(input_file) as dump_file:
        works = json.load(dump_file)

    works = process_works(works, model)

    with(open(output_file, 'w')) as fo:
        json.dump(works, fo)


def process_works(works, model):
    abstracts = [work['abstract'] if 'abstract' in work and work['abstract'] is not None else "" for work in
                 works]
    embeddings_abstracts = model.encode(abstracts, convert_to_tensor=True)
    keywords_abstracts = kw_model.extract_keywords(abstracts, embeddings=embeddings_abstracts, threshold=0.5)
    titles = [work['title'] if 'title' in work and work['title'] is not None else "" for work in works]
    embeddings_titles = model.encode(titles, convert_to_tensor=True)
    keywords_titles = kw_model.extract_keywords(titles, embeddings=embeddings_titles, threshold=0.5)
    for idx, keywords_abstract in enumerate(keywords_abstracts):
        keyword_title = keywords_titles[idx]

        works[idx]["keyterms_T"] = keyword_title[:2]
        works[idx]["keyterms_A"] = keywords_abstract[:10]

    return works


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Extract keywords using KeyLLM + KeyBERT. The documents are aggregated.")

    parser.add_argument("--input-corpus",
                        help="Directory containing the Openalex dump in JSON ",
                        required=False)
    parser.add_argument("--output-dir",
                        required=False,
                        help="Output directory where to store the openalex dump + keywords")

    parser.add_argument("--input-json",
                        help="Single JSON file containing a list of openalex works",
                        required=False)
    parser.add_argument("--output-json",
                        required=False,
                        help="Output JSON file where to store the input file with the added keywords.")

    parser.add_argument("--input-text",
                        help="Input file as text, with one line per document on which generate keywords",
                        required=False)
    parser.add_argument("--output-text",
                        required=False,
                        help="Output file")

    args = parser.parse_args()

    input_corpus = args.input_corpus
    output_dir = args.output_dir

    input_json = args.input_json
    output_json = args.output_json

    input_text = args.input_text
    output_text = args.output_text

    kw_model = KeyLLM(llm=chatgpt)
    model = SentenceTransformer('all-MiniLM-L6-v2')

    if input_corpus and output_dir:
        for filename in tqdm(os.listdir(input_corpus)):
            input_file = os.path.join(input_corpus, filename)
            output_file = os.path.join(output_dir, Path(filename).stem + ".json")
            if not os.path.exists(output_file):
                with open(input_file) as dump_file:
                    works = json.load(dump_file)
                try:
                    works = process_works(works, model)

                    with(open(output_file, 'w')) as fo:
                        json.dump(works, fo)
                except Exception as e:
                    print(f"File {input_file} could not be processed. Split in 2.")
                    middle = ceil(len(works)/2)
                    works_tmp = works[0:middle]
                    works1 = process_works(works_tmp, model)
                    output_file = os.path.join(output_dir, Path(filename).stem + "1.json")
                    with(open(output_file, 'w')) as fo:
                        json.dump(works1, fo)

                    works_tmp = works[middle:]
                    works2 = process_works(works_tmp, model)
                    output_file = os.path.join(output_dir, Path(filename).stem + "2.json")
                    with(open(output_file, 'w')) as fo:
                        json.dump(works2, fo)


    elif input_text and output_text:
        lines = []
        with open(input_text, 'r') as input_file_text:
            for line in input_file_text:
                if not line:
                    continue
                lines.append(line)

        keywords = kw_model.extract_keywords(" ".join(lines))
        with open(output_text, 'w') as fo:
            json.dump(keywords, fo)

    elif input_json and output_json:
        if not os.path.exists(input_json):
            print("Input file does not exits. ")
            sys.exit(-1)
        process_single(input_json, output_json, model)
    else:
        print(
            "The parameters should be --input-corpus + --output_dir or --input-text + --output-text or --input-json + --output-json")
