import argparse
import json
import os
from pathlib import Path

from rdflib import Graph, Namespace, Literal, URIRef, RDFS
from rdflib.namespace import RDF
from tqdm import tqdm


def main():
    parser = argparse.ArgumentParser(
        description="Generate RDF/Turtle for papers from dump data"
    )
    parser.add_argument("--input-corpus", required=True, type=Path,
                        help="Dump directory containing work JSON files")
    parser.add_argument("--output", required=True, type=Path,
                        help="Output TTL file")
    args = parser.parse_args()

    # First pass: collect unique papers
    papers = {}  # openalex_id -> paper info dict
    for filename in tqdm(os.listdir(args.input_corpus), desc="Scanning papers"):
        filepath = os.path.join(args.input_corpus, filename)
        if not filepath.endswith(".json"):
            continue
        with open(filepath) as f:
            works = json.load(f)

        for work in works:
            work_url = work.get("id", "")
            if not work_url:
                continue
            work_id = work_url.split("https://openalex.org/")[-1]
            if work_id not in papers:
                papers[work_id] = {
                    "title": work.get("title", "") or "",
                    "doi": work.get("doi", "") or "",
                    "publication_year": str(work.get("publication_year", "") or ""),
                    "publication_date": work.get("publication_date", "") or "",
                    "oa_status": work.get("oa_status", "") or "",
                    "publisher": work.get("publisher", "") or "",
                }

    print(f"Found {len(papers)} unique papers")

    # Build custom ID mapping
    openalex_to_custom_id = {}
    counter = 1
    for oa_id in papers:
        openalex_to_custom_id[oa_id] = f"BKGP{counter:05d}"
        counter += 1

    # Second pass: build RDF graph
    g = Graph()
    ex = Namespace("http://example.org/")
    OA = Namespace("https://openalex.org/")
    DOI = Namespace("https://doi.org/")

    g.add((ex.Paper, RDF.type, RDFS.Class))
    g.add((ex.Paper, RDFS.label, Literal("Paper")))

    g.bind("ex", ex)
    g.bind("oa", OA)
    g.bind("doi", DOI)
    g.bind("rdf", RDF)
    g.bind("rdfs", RDFS)

    # Define properties
    for prop, label in [
        (ex.customID, "PaperID"),
        (OA.openAlexID, "OpenAlexID"),
        (DOI.doi, "DOI"),
        (ex.publication_year, "PublicationYear"),
        (ex.publication_date, "PublicationDate"),
        (ex.OA_status, "OpenAccessStatus"),
        (ex.publisher, "Publisher"),
    ]:
        g.add((prop, RDF.type, RDF.Property))
        g.add((prop, RDFS.domain, ex.Paper))
        g.add((prop, RDFS.range, RDFS.Literal))
        g.add((prop, RDFS.label, Literal(label)))

    for oa_id, info in papers.items():
        custom_id = openalex_to_custom_id[oa_id]
        doi_url = info["doi"]
        doi_id = doi_url.split("https://doi.org/")[-1] if doi_url else ""

        row_uri = URIRef(f"Paper_{custom_id}")

        g.add((row_uri, ex["PaperTitle"], Literal(info["title"])))
        g.add((row_uri, ex["PaperID"], Literal(custom_id)))
        g.add((row_uri, OA["OpenAlexID"], Literal(oa_id)))
        g.add((row_uri, DOI["DOI"], Literal(doi_id)))
        g.add((row_uri, ex["PublicationYear"], Literal(info["publication_year"])))
        g.add((row_uri, ex["PublicationDate"], Literal(info["publication_date"])))
        if info["oa_status"]:
            g.add((row_uri, ex["OA_Status"], Literal(info["oa_status"])))
        if info["publisher"]:
            g.add((row_uri, ex["Publisher"], Literal(info["publisher"])))

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    g.serialize(destination=str(args.output), format="turtle")
    print(f"Graph serialized and saved to {args.output}")


if __name__ == "__main__":
    main()
