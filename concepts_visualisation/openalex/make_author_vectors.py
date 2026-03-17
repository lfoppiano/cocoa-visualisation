import argparse
import json
import re

import numpy as np
from tqdm import tqdm

from concepts_visualisation.openalex.utils import process_key

PERIOD_ORDER = ["2010-2023", "2000-2009", "1990-1999"]


def make_sec_vec(sec, no_pub, term_lst, concept_weight, keyword_weight):
    vec = [0.0] * len(term_lst)
    concepts = sec["concepts"]
    keywords = sec["keywords"]

    for con in concepts:
        if con != "":
            p_con = process_key(con)
            if p_con in term_lst:
                con_idx = term_lst.index(p_con)
                con_score = ((concepts[con]["freq"] / no_pub) * concepts[con]["avg_score"]) * concept_weight
                vec[con_idx] = con_score

    for key in keywords:
        if key != "":
            p_key = process_key(key)
            if p_key in term_lst:
                key_idx = term_lst.index(p_key)
                key_score = (keywords[key]["freq"] / no_pub) * keyword_weight
                if vec[key_idx] == 0:
                    vec[key_idx] = key_score
                else:
                    vec[key_idx] = (vec[key_idx] + key_score) / 2

    return vec


def make_period_vec(period, term_lst, concept_weight, keyword_weight,
                    first_author_weight, non_first_author_weight):
    f_auth_vec = [
        x * first_author_weight
        for x in make_sec_vec(period["first_author"],
                              period["nb_publications_first_author"],
                              term_lst, concept_weight, keyword_weight)
    ]
    nf_auth_vec = [
        x * non_first_author_weight
        for x in make_sec_vec(period["non_first_author"],
                              period["nb_publications_not_first_author"],
                              term_lst, concept_weight, keyword_weight)
    ]
    return [sum(x) for x in zip(f_auth_vec, nf_auth_vec)]


def make_auth_vec(auth, term_lst, concept_weight, keyword_weight,
                  first_author_weight, non_first_author_weight, period_weights):
    period_vecs = {}
    for period_name in auth["periods"]:
        pvec = make_period_vec(auth["periods"][period_name], term_lst,
                               concept_weight, keyword_weight,
                               first_author_weight, non_first_author_weight)
        period_vecs[period_name] = pvec

    # Apply period weights: index 0 = most recent (2010-2023), etc.
    weighted_vecs = []
    for i, period_name in enumerate(PERIOD_ORDER):
        if period_name in period_vecs:
            w = period_weights[i] if i < len(period_weights) else period_weights[-1]
            weighted_vecs.append([x * w for x in period_vecs[period_name]])
        else:
            weighted_vecs.append([0.0] * len(term_lst))

    result = weighted_vecs[0]
    for v in weighted_vecs[1:]:
        result = [sum(x) for x in zip(result, v)]

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Generate author vectors from merged terms and author data"
    )
    parser.add_argument("--input-terms", required=True,
                        help="Input merged_terms.json file")
    parser.add_argument("--input-authors", required=True,
                        help="Input authors JSON file (from aggregate_authors)")
    parser.add_argument("--output-json", required=True,
                        help="Output author_vectors.json file")
    parser.add_argument("--concept-weight", type=float, default=1.0)
    parser.add_argument("--keyword-weight", type=float, default=1.0)
    parser.add_argument("--first-author-weight", type=float, default=1.0)
    parser.add_argument("--non-first-author-weight", type=float, default=0.6)
    parser.add_argument("--period-weights", type=float, nargs=3,
                        default=[1.0, 0.8, 0.6],
                        help="Weights for periods: 2010-2023, 2000-2009, 1990-1999")
    args = parser.parse_args()

    with open(args.input_terms) as f:
        terms_data = json.load(f)
    term_lst = terms_data["terms"]
    print(f"Loaded {len(term_lst)} terms")

    with open(args.input_authors) as f:
        authors = json.load(f)
    print(f"Loaded {len(authors)} authors")

    author_records = []
    for author_key, auth in tqdm(authors.items(), desc="Building author vectors"):
        auth_vec = make_auth_vec(auth, term_lst,
                                 args.concept_weight, args.keyword_weight,
                                 args.first_author_weight,
                                 args.non_first_author_weight,
                                 args.period_weights)

        top_terms_idx = np.argsort(np.array(auth_vec))[::-1][:20]
        top_terms = {term_lst[i]: auth_vec[i] for i in top_terms_idx if auth_vec[i] > 0}

        pub_lst = []
        for period in auth["periods"]:
            pub_lst.extend(auth["periods"][period]["publications"])

        author_records.append({
            "openalex_id": auth["openalex_id"],
            "name": re.split("###", auth["id"])[1],
            "total_publications": auth["nb_publications"],
            "first_author_publications": auth["nb_publications_first_author"],
            "orcid": auth.get("orcid", ""),
            "publications": pub_lst,
            "vector": auth_vec,
            "top_terms": top_terms
        })

    output = {
        "metadata": {
            "term_count": len(term_lst),
            "author_count": len(author_records),
            "weights": {
                "concept": args.concept_weight,
                "keyword": args.keyword_weight,
                "first_author": args.first_author_weight,
                "non_first_author": args.non_first_author_weight,
                "periods": args.period_weights
            }
        },
        "terms": term_lst,
        "authors": author_records
    }

    with open(args.output_json, "w") as f:
        json.dump(output, f)
    print(f"Wrote {args.output_json} ({len(author_records)} authors, {len(term_lst)} terms)")


if __name__ == "__main__":
    main()
