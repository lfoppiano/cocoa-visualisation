import argparse
import json
import os
from pathlib import Path

from rdflib import Graph, Namespace, Literal, URIRef, RDFS
from rdflib.namespace import RDF

MAX_TERMS = 20


def main():
    parser = argparse.ArgumentParser(
        description="Generate RDF/Turtle for author-term relationships from pipeline data"
    )
    parser.add_argument("--input-json", required=True, type=Path,
                        help="Input complete_authors.json or author_vectors.json file")
    parser.add_argument("--output", required=True, type=Path,
                        help="Output TTL file")
    args = parser.parse_args()

    with open(args.input_json) as f:
        data = json.load(f)

    authors = data["authors"]
    print(f"Loaded {len(authors)} authors")

    # Build custom ID mapping
    openalex_to_custom_id = {}
    counter = 1
    for author in authors:
        oa_id = author["openalex_id"].split("https://openalex.org/")[-1]
        if oa_id not in openalex_to_custom_id:
            openalex_to_custom_id[oa_id] = f"BKGA{counter:05d}"
            counter += 1

    g = Graph()
    ex = Namespace("http://example.org/")

    g.add((ex.Author, RDF.type, RDFS.Class))
    g.add((ex.Author, RDFS.label, Literal("Author")))

    g.bind("ex", ex)

    # Define AuthorID property
    g.add((ex.authorID, RDF.type, RDF.Property))
    g.add((ex.authorID, RDFS.domain, ex.Author))
    g.add((ex.authorID, RDFS.range, RDFS.Literal))
    g.add((ex.authorID, RDFS.label, Literal("AuthorID")))

    # Define Term1..Term20 properties
    for i in range(1, MAX_TERMS + 1):
        g.add((ex.conceptID, RDF.type, RDF.Property))
        g.add((ex.conceptID, RDFS.domain, ex.Author))
        g.add((ex.conceptID, RDFS.range, RDFS.Literal))
        g.add((ex.conceptID, RDFS.label, Literal(f"Term{i}")))

    for author in authors:
        oa_id = author["openalex_id"].split("https://openalex.org/")[-1]
        custom_id = openalex_to_custom_id[oa_id]
        row_uri = URIRef(f"Author_{custom_id}")

        g.add((row_uri, ex["AuthorID"], Literal(custom_id)))

        # Sort top_terms by score descending, take up to MAX_TERMS
        top_terms = author.get("top_terms", {})
        sorted_terms = sorted(top_terms.items(), key=lambda x: x[1], reverse=True)[:MAX_TERMS]

        for i in range(MAX_TERMS):
            term_name = sorted_terms[i][0] if i < len(sorted_terms) else ""
            g.add((row_uri, ex[f"Term{i + 1}"], Literal(term_name)))

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    g.serialize(destination=str(args.output), format="turtle")
    print(f"Graph serialized and saved to {args.output}")


if __name__ == "__main__":
    main()
