import argparse
import json

import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import TruncatedSVD
from sklearn.metrics.pairwise import cosine_similarity
from scipy.sparse import csr_matrix


def match_terms(auth1_vec, auth2_vec, term_lst):
    best_idx = -1
    best_score = 0
    for i in range(len(auth1_vec)):
        if auth1_vec[i] != 0 and auth2_vec[i] != 0:
            score = (auth1_vec[i] + auth2_vec[i]) / 2
            if score > best_score:
                best_score = score
                best_idx = i

    if best_idx >= 0 and best_idx < len(term_lst):
        return term_lst[best_idx]
    return None


def compute_similarity_matrix(author_vecs, svd_components):
    auth_arr = np.array(author_vecs)
    X = StandardScaler().fit_transform(auth_arr)
    X_sparse = csr_matrix(X)

    tsvd = TruncatedSVD(n_components=svd_components)
    X_sparse_tsvd = tsvd.fit_transform(X_sparse)
    print(f"SVD reduced to shape: {X_sparse_tsvd.shape}")

    sim_val_arr = cosine_similarity(X_sparse_tsvd, X_sparse_tsvd)
    return sim_val_arr


def main():
    parser = argparse.ArgumentParser(
        description="Compute author similarity from author vectors"
    )
    parser.add_argument("--input-author-vectors", required=True,
                        help="Input author_vectors.json file")
    parser.add_argument("--output-json", required=True,
                        help="Output complete_authors.json file")
    parser.add_argument("--top-n", type=int, default=10,
                        help="Number of top similar authors per author (default: 10)")
    parser.add_argument("--svd-components", type=int, default=200,
                        help="Number of SVD components for dimensionality reduction (default: 200)")
    parser.add_argument("--input-similarity-matrix", default=None,
                        help="Load precomputed similarity matrix (.npy)")
    parser.add_argument("--output-similarity-matrix", default=None,
                        help="Save computed similarity matrix (.npy)")
    args = parser.parse_args()

    with open(args.input_author_vectors) as f:
        data = json.load(f)

    term_lst = data["terms"]
    authors = data["authors"]
    author_vecs = [a["vector"] for a in authors]
    print(f"Loaded {len(authors)} authors, {len(term_lst)} terms")

    if args.input_similarity_matrix:
        print(f"Loading precomputed similarity matrix from {args.input_similarity_matrix}")
        sim_val_arr = np.load(args.input_similarity_matrix)
    else:
        print("Computing similarity matrix...")
        sim_val_arr = compute_similarity_matrix(author_vecs, args.svd_components)

    if args.output_similarity_matrix:
        np.save(args.output_similarity_matrix, sim_val_arr)
        print(f"Saved similarity matrix to {args.output_similarity_matrix}")

    print("Finding top similar authors...")
    for i in range(len(authors)):
        if i % 1000 == 0:
            print(f"  Processing author {i}/{len(authors)}")

        idxs = list(np.argsort(sim_val_arr[i, :])[::-1][:args.top_n + 1])
        if i in idxs:
            idxs.remove(i)
        else:
            del idxs[-1]

        sim_vals = sim_val_arr[i, :][idxs]
        auth1_vec = author_vecs[i]

        similar_authors = []
        for j in range(len(idxs)):
            auth2_vec = author_vecs[idxs[j]]
            mt = match_terms(auth1_vec, auth2_vec, term_lst)

            similar_authors.append({
                "rank": j + 1,
                "openalex_id": authors[idxs[j]]["openalex_id"],
                "similarity_score": float(sim_vals[j]),
                "matching_term": mt
            })

        authors[i]["similar_authors"] = similar_authors

    output = {
        "metadata": {
            "author_count": len(authors),
            "top_n_similar": args.top_n,
            "svd_components": args.svd_components
        },
        "terms": term_lst,
        "authors": authors
    }

    with open(args.output_json, "w") as f:
        json.dump(output, f)
    print(f"Wrote {args.output_json}")


if __name__ == "__main__":
    main()
