import argparse
import json
import os
from pathlib import Path

import dotenv
from keybert.llm import OpenAI
from keyphrase_vectorizers import KeyphraseCountVectorizer

dotenv.load_dotenv(override=True)

from keybert import KeyLLM
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

lc_chatgpt = OpenAI(model="gpt-3.5-turbo", chat=True)

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

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Extract keywords")

    parser.add_argument("--input-corpus",
                        help="Openalex dump in JSON",
                        required=False)
    parser.add_argument("--output-dir",
                        required=False,
                        help="Output directory")
    parser.add_argument("--input",
                        help="Input file as text, with one line per document on which generate keywords",
                        required=False)
    parser.add_argument("--output",
                        required=False,
                        help="Output file")

    args = parser.parse_args()

    input_corpus = args.input_corpus
    output_dir = args.output_dir
    input_file = args.input
    output_file = args.output

    kw_model = KeyLLM(llm=lc_chatgpt)

    if input_corpus and output_dir:
        model = SentenceTransformer('all-MiniLM-L6-v2')
        for filename in tqdm(os.listdir(input_corpus)):
            with open(os.path.join(input_corpus, filename)) as dump_file:
                works = json.load(dump_file)

                abstracts = [work['abstract'] if 'abstract' in work and work['abstract'] is not None else "" for work in
                             works]
                embeddings_abstracts = model.encode(abstracts, convert_to_tensor=True)
                keywords_abstracts = kw_model.extract_keywords(abstracts, embeddings=embeddings_abstracts, threshold=0.9)

                titles = [work['title'] if 'title' in work and work['title'] is not None else "" for work in works]
                embeddings_titles = model.encode(titles, convert_to_tensor=True)
                keywords_titles = kw_model.extract_keywords(titles, embeddings=embeddings_titles, threshold=0.9)

                for idx, keywords_abstract in enumerate(keywords_abstracts):
                    keyword_title = keywords_titles[idx]

                    works[idx]["keyterms_T"] = keyword_title
                    works[idx]["keyterms_A"] = keywords_abstract

                with(open(os.path.join(output_dir, Path(filename).stem + ".keybert.json"), 'w')) as fo:
                    json.dump(works, fo)
    elif input_file and output_file:
        vectorizer = KeyphraseCountVectorizer()
        lines = []
        with open(input_file, 'r') as input_file_text:
            for line in input_file_text:
                if not line:
                    continue

                lines.append(line)

        keywords = kw_model.extract_keywords(" ".join(lines), vectorizer=vectorizer, top_n=10)
        with open(output_file, 'w') as fo:
            json.dump(keywords, fo)

    else:
        print("The parameters should be --input-corpus + --output_dir or --input + --output")
