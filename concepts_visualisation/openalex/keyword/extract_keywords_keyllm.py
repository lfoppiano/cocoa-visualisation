import argparse
import json
import os
import sys
from pathlib import Path

import dotenv
import openai
from keybert.llm import OpenAI

dotenv.load_dotenv(override=True)

from keybert import KeyLLM
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

client = openai.OpenAI()
lc_chatgpt = OpenAI(client, model="gpt-3.5-turbo", chat=True)


# lc_chatgpt = PromptLayerChatOpenAI(model_name="gpt-3.5-turbo",
#                                    frequency_penalty=0.1,
#                                    temperature=0,
#                                    return_pl_id=True,
#                                    pl_tags=["chatgpt", "concepts"])
#
# lc_gpt4 = ChatOpenAI(model_name="gpt-4",
#                      frequency_penalty=0.1,
#                      temperature=0
#                      )

def process_single(input_file, output_file, model):
    with open(input_file) as dump_file:
        works = json.load(dump_file)

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

    with(open(output_file, 'w')) as fo:
        json.dump(works, fo)


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

    kw_model = KeyLLM(llm=lc_chatgpt)
    model = SentenceTransformer('all-MiniLM-L6-v2')

    if input_corpus and output_dir:
        for filename in tqdm(os.listdir(input_corpus)):
            input_file = os.path.join(input_corpus, filename)
            output_file = os.path.join(output_dir, Path(filename).stem + ".json")
            process_single(input_file, output_file, model)
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
