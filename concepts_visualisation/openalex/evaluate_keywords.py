import argparse
import json
import os

from sentence_transformers import SentenceTransformer
from sentence_transformers import util
from tqdm import tqdm


def print_markdown(result_table):
    # Write table headers
    markdown = "|" + "|".join(result_table[0]) + "|" + "\n"
    markdown += "|" + "|".join(["---"] * len(result_table[0])) + "|" + "\n"

    # Write table rows
    for row in result_table[1:]:
        formatted_row = [f"{cell:.4f}" if isinstance(cell, (int, float)) else str(cell) for cell in row]
        markdown += "|" + "|".join(formatted_row) + "|" + "\n"

    return markdown


def compute_average_similarity(expected_keywords_lower_sorted, predicted_keywords_by_method_lower_sorted):
    ignored_expected = []
    average_similarity_document = 0
    for idp, predicted_keyword in enumerate(predicted_keywords_by_method_lower_sorted):
        max_cosine = 0
        max_cosine_expected_id = -1
        for ide, expected_keyword in enumerate(expected_keywords_lower_sorted):
            if ide in ignored_expected:
                continue

            embeddings_e = model.encode(str.lower(expected_keyword), convert_to_tensor=True,
                                        show_progress_bar=False)
            embeddings_p = model.encode(str.lower(predicted_keyword), convert_to_tensor=True,
                                        show_progress_bar=False)
            cosine_scores = util.cos_sim(embeddings_e, embeddings_p)
            if cosine_scores.item() > max_cosine:
                max_cosine = cosine_scores.item()
                max_cosine_expected_id = ide

        ignored_expected.append(max_cosine_expected_id)
        average_similarity_document += max_cosine
    average_similarity_document /= len(ignored_expected)

    return average_similarity_document


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Evaluate keywords extracted by different methods with the one from the pdf documents")

    parser.add_argument("--input-corpus",
                        help="Sample directory",
                        required=True)
    # parser.add_argument("--output-dir",
    #                     required=False,
    #                     help="Output directory")

    args = parser.parse_args()

    input_corpus = args.input_corpus
    # output_dir = args.output_dir

    model = SentenceTransformer('all-MiniLM-L6-v2')

    document_count = 0

    similarities_keybert = []
    similarities_batteryonlybert = []
    similarities_chatgpt = []
    similarities_batteryscibert_cased = []
    similarities_batteryscibert_uncased = []

    for directory in tqdm(os.listdir(input_corpus)):
        if document_count >= 100:
            break

        expected_file = os.path.join(input_corpus, directory, directory + ".keywords.txt")
        if not os.path.exists(expected_file):
            continue
        with open(expected_file, 'r') as fi:
            expected_keywords = [str.strip(line) for line in fi]

        file_keybert = os.path.join(input_corpus, directory, directory + ".keybert.json")
        if not os.path.exists(file_keybert):
            continue
        raw_keywords_keybert = json.load(open(file_keybert))
        if len(raw_keywords_keybert) == 0:
            continue

        file_batteryonlybert = os.path.join(input_corpus, directory, directory + ".batteryonlybert.json")
        if not os.path.exists(file_batteryonlybert):
            continue
        raw_keywords_batteryonlybert = json.load(open(file_batteryonlybert))
        if len(raw_keywords_batteryonlybert) == 0:
            continue

        file_batteryscibert_cased = os.path.join(input_corpus, directory, directory + ".batteryscibert.json")
        if not os.path.exists(file_batteryscibert_cased):
            continue
        raw_keywords_batteryscibert_cased = json.load(open(file_batteryscibert_cased))
        if len(raw_keywords_batteryscibert_cased) == 0:
            continue

        file_batteryscibert_uncased = os.path.join(input_corpus, directory, directory + ".batteryscibert_uncased.json")
        if not os.path.exists(file_batteryscibert_uncased):
            continue
        raw_keywords_batteryscibert_uncased = json.load(open(file_batteryscibert_uncased))
        if len(raw_keywords_batteryscibert_uncased) == 0:
            continue

        file_chatgpt = os.path.join(input_corpus, directory, directory + ".chatgpt.json")
        if not os.path.exists(file_chatgpt):
            continue
        raw_keywords_chatgpt = json.load(open(file_chatgpt))
        if len(raw_keywords_chatgpt) == 0 or 'sorry' in raw_keywords_chatgpt:
            continue

        keywords_collection = [raw_keywords_keybert, raw_keywords_batteryonlybert, raw_keywords_chatgpt,
                               raw_keywords_batteryscibert_cased, raw_keywords_batteryscibert_uncased]
        keywords_collection_simple = [[item[0] for item in sublist] if isinstance(sublist[0], list) else sublist for sublist in keywords_collection[:2]] + [keywords_collection[2]] + [[item[0] for item in sublist] if isinstance(sublist[0], list) else sublist for
            sublist in keywords_collection[3:]]

        max_length = min([len(i) for i in keywords_collection_simple] + [10])
        predicted_keywords = [i[0:max_length] for i in keywords_collection_simple]

        similarities_by_method_document = []
        expected_keywords_lower_sorted = sorted([str.lower(item) for item in expected_keywords])
        for idp, predicted_keywords_by_method in enumerate(predicted_keywords):
            predicted_keywords_by_method_lower_sorted = sorted(
                [str.lower(item) for item in predicted_keywords_by_method])

            avg_similarity = compute_average_similarity(expected_keywords_lower_sorted,
                                                        predicted_keywords_by_method_lower_sorted)
            similarities_by_method_document.append(avg_similarity)

        similarities_keybert.append(similarities_by_method_document[0])
        similarities_batteryonlybert.append(similarities_by_method_document[1])
        similarities_chatgpt.append(similarities_by_method_document[2])
        similarities_batteryscibert_cased.append(similarities_by_method_document[3])
        similarities_batteryscibert_uncased.append(similarities_by_method_document[4])
        document_count += 1

    scores = [["method", "avg. similarity"]]
    scores.append(["keybert", sum(similarities_keybert) / document_count])
    scores.append(["batteryonlybert", sum(similarities_batteryonlybert) / document_count])
    scores.append(["chatgpt", sum(similarities_chatgpt) / document_count])
    scores.append(["batteryscibert_cased", sum(similarities_batteryscibert_cased) / document_count])
    scores.append(["batteryscibert_uncased", sum(similarities_batteryscibert_uncased) / document_count])

    print(print_markdown(scores))
