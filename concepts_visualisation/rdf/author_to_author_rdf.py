import argparse
import json
import os
from pathlib import Path

from rdflib import Graph, Namespace, Literal, URIRef, RDFS
from rdflib.namespace import RDF


def main():
    parser = argparse.ArgumentParser(
        description="Generate RDF/Turtle for author-to-author similarity from pipeline data"
    )
    parser.add_argument("--input-json", required=True, type=Path,
                        help="Input complete_authors.json file")
    parser.add_argument("--output", required=True, type=Path,
                        help="Output TTL file")
    parser.add_argument("--top-n", type=int, default=5,
                        help="Number of similar authors to include per author (default: 5)")
    args = parser.parse_args()

    with open(args.input_json) as f:
        data = json.load(f)

    authors = data["authors"]
    print(f"Loaded {len(authors)} authors")

    # Build custom ID mapping for all authors
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

    # Define Top-N and concept properties
    for i in range(1, args.top_n + 1):
        for label in [f"Top{i}", f"Top{i}Concept"]:
            prop = ex.authorID if "Concept" not in label else ex.conceptID
            g.add((prop, RDF.type, RDF.Property))
            g.add((prop, RDFS.domain, ex.Author))
            g.add((prop, RDFS.range, RDFS.Literal))
            g.add((prop, RDFS.label, Literal(label)))

    for author in authors:
        oa_id = author["openalex_id"].split("https://openalex.org/")[-1]
        custom_id = openalex_to_custom_id[oa_id]
        row_uri = URIRef(f"Author_{custom_id}")

        g.add((row_uri, ex["AuthorID"], Literal(custom_id)))

        similar = author.get("similar_authors", [])
        for i in range(args.top_n):
            if i < len(similar):
                sim_oa_id = similar[i]["openalex_id"].split("https://openalex.org/")[-1]
                sim_custom_id = openalex_to_custom_id.get(sim_oa_id, sim_oa_id)
                matching_term = similar[i].get("matching_term", "") or ""
            else:
                sim_custom_id = ""
                matching_term = ""

            g.add((row_uri, ex[f"Top{i + 1}"], Literal(sim_custom_id)))
            g.add((row_uri, ex[f"Top{i + 1}Concept"], Literal(matching_term)))

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    g.serialize(destination=str(args.output), format="turtle")
    print(f"Graph serialized and saved to {args.output}")


if __name__ == "__main__":
    main()
