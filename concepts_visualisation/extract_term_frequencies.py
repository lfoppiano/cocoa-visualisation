import argparse
import json
import os

from concepts_visualisation.utils import process_key

CONCEPT_EXCLUDE_LIST = ["power (physics)"]

KEYWORD_EXCLUDE_LIST = [
    "<document analysi", "comma", "keyword", "topic", "information", "keywords",
    "extract", "document", "text", "based on the information above", "<document",
    "text>", "based on the information provided", "keywords: document", "topic>",
    "text.", "<document analysis",
    "the keywords that best describe the topic of the text are:\n\ndocument",
    "<information",
    "the keywords that best describe the topic of the text are:\n\ninformation",
    "1",
    "the keywords that best describe the topic of the text are:\n\n<keywords>",
    "topic>.", "3", "n", "i'm sorry", "battery", "batteries"
]


def extract_frequencies(input_corpus):
    concepts = {}
    keywords = {}

    for filename in os.listdir(input_corpus):
        if not filename.endswith(".json"):
            continue
        print(filename)
        with open(os.path.join(input_corpus, filename)) as jfile:
            works = json.load(jfile)

        for work in works:
            for con in work["concepts"]:
                if con["display_name"] != "":
                    con_name = process_key(con["display_name"])
                    con_lvl = con["level"]
                    if con_lvl not in (0, 1) and con_name not in CONCEPT_EXCLUDE_LIST:
                        concepts[con_name] = concepts.get(con_name, 0) + 1

            for kwdt in work["keyterms_T"]:
                if kwdt != "":
                    kwdt_l = process_key(kwdt)
                    if kwdt_l not in KEYWORD_EXCLUDE_LIST:
                        keywords[kwdt_l] = keywords.get(kwdt_l, 0) + 1

            for kwda in work["keyterms_A"]:
                if kwda != "":
                    kwda_l = process_key(kwda)
                    if kwda_l not in KEYWORD_EXCLUDE_LIST:
                        keywords[kwda_l] = keywords.get(kwda_l, 0) + 1

    return concepts, keywords


def build_outputs(concepts, keywords, top_n):
    sor_concepts = dict(sorted(concepts.items(), key=lambda item: item[1], reverse=True))
    sor_concepts_select = {k: sor_concepts[k] for k in list(sor_concepts)[:top_n]}

    sor_keywords = dict(sorted(keywords.items(), key=lambda item: item[1], reverse=True))
    sor_keywords_select = {k: sor_keywords[k] for k in list(sor_keywords)[:top_n]}

    merged = {
        k: sor_concepts_select.get(k, 0) + sor_keywords_select.get(k, 0)
        for k in set(sor_concepts_select) | set(sor_keywords_select)
    }
    sor_merge = dict(sorted(merged.items(), key=lambda item: item[1], reverse=True))

    print(f"Concepts: {len(sor_concepts)} total, {len(sor_concepts_select)} selected")
    print(f"Keywords: {len(sor_keywords)} total, {len(sor_keywords_select)} selected")
    print(f"Merged terms: {len(sor_merge)}")

    term_frequencies = {
        "metadata": {
            "top_n": top_n,
            "total_concepts": len(sor_concepts),
            "total_keywords": len(sor_keywords)
        },
        "concepts_all": sor_concepts,
        "concepts_selected": sor_concepts_select,
        "keywords_all": sor_keywords,
        "keywords_selected": sor_keywords_select,
        "merged": sor_merge
    }

    merged_terms = {
        "terms": list(sor_merge.keys()),
        "frequencies": sor_merge
    }

    return term_frequencies, merged_terms


def main():
    parser = argparse.ArgumentParser(
        description="Extract concept and keyword frequencies from works corpus"
    )
    parser.add_argument("--input-corpus", required=True,
                        help="Input directory containing JSON work files")
    parser.add_argument("--output-dir", required=True,
                        help="Output directory for frequency JSON files")
    parser.add_argument("--top-n", type=int, default=1000,
                        help="Number of top terms to select (default: 1000)")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    concepts, keywords = extract_frequencies(args.input_corpus)
    term_frequencies, merged_terms = build_outputs(concepts, keywords, args.top_n)

    tf_path = os.path.join(args.output_dir, "term_frequencies.json")
    with open(tf_path, "w") as f:
        json.dump(term_frequencies, f, indent=2)
    print(f"Wrote {tf_path}")

    mt_path = os.path.join(args.output_dir, "merged_terms.json")
    with open(mt_path, "w") as f:
        json.dump(merged_terms, f, indent=2)
    print(f"Wrote {mt_path}")


if __name__ == "__main__":
    main()
