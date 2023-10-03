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

    parser.add_argument("--input",
                        help="Input CSV file",
                        required=True)
    parser.add_argument("--output",
                        default=None,
                        help="Output directory")
    parser.add_argument("--transformer", help="Set a custom transformer using the flair platform",
                        required=False)

    args = parser.parse_args()

    input = args.input
    output = args.output
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

    for filename in tqdm(os.listdir(input)):
        with open(os.path.join(input, filename)) as dump_file:
            works = json.load(dump_file)

            abstracts = [work['abstract'] if 'abstract' in work and work['abstract'] is not None else "" for work in
                         works]

            keywords_abstracts = kw_model.extract_keywords(abstracts,
                                                           vectorizer=vectorizer,
                                                           top_n=5)

            titles = [work['title'] if 'title' in work and work['title'] is not None else "" for work in works]
            keywords_titles = kw_model.extract_keywords(titles,
                                                        vectorizer=vectorizer)

            for idx, keywords_abstract in enumerate(keywords_abstracts):
                keyword_title = keywords_titles[idx]

                works[idx]["keyterms_T"] = keyword_title
                works[idx]["keyterms_A"] = keywords_abstract

            with(open(os.path.join(output, Path(filename).stem + ".keybert.json"), 'w')) as fo:
                json.dump(works, fo)
