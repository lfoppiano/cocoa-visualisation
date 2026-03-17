import argparse
import json
import os
from pathlib import Path

from flair.embeddings import TransformerDocumentEmbeddings
from keybert import KeyBERT
from keyphrase_vectorizers import KeyphraseCountVectorizer
from tqdm import tqdm

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
    parser.add_argument("--transformer", help="Set a custom transformer using the flair platform",
                        required=False)

    args = parser.parse_args()

    input_corpus = args.input_corpus
    output_dir = args.output_dir
    input_file = args.input
    output_file = args.output
    transformer_name = args.transformer

    if transformer_name:
        custom_transformer = TransformerDocumentEmbeddings(transformer_name,
                                                           layer_mean=True,
                                                           cls_pooling="cls",
                                                           layers="all")
        kw_model = KeyBERT(model=custom_transformer)
    else:
        kw_model = KeyBERT()

    vectorizer = KeyphraseCountVectorizer()

    if input_corpus and output_dir:
        for filename in tqdm(os.listdir(input_corpus)):
            with open(os.path.join(input_corpus, filename)) as dump_file:
                works = json.load(dump_file)

                abstracts = [work['abstract'] if 'abstract' in work and work['abstract'] is not None else "" for work in
                             works]

                keywords_abstracts = kw_model.extract_keywords(abstracts, vectorizer=vectorizer, top_n=10)

                titles = [work['title'] if 'title' in work and work['title'] is not None else "" for work in works]
                keywords_titles = kw_model.extract_keywords(titles, vectorizer=vectorizer)

                for idx, keywords_abstract in enumerate(keywords_abstracts):
                    keyword_title = keywords_titles[idx]

                    works[idx]["keyterms_T"] = keyword_title
                    works[idx]["keyterms_A"] = keywords_abstract

                with(open(os.path.join(output_dir, Path(filename).stem + ".keybert.json"), 'w')) as fo:
                    json.dump(works, fo)
    elif input_file and output_file:
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
