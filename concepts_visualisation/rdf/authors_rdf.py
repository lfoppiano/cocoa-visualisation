import argparse
import json
import os
from collections import Counter
from pathlib import Path

from rdflib import Graph, Namespace, Literal, URIRef, RDFS
from rdflib.namespace import RDF
from tqdm import tqdm


def load_affiliations_from_dump(dump_dir):
    """Scan dump files and return most frequent institution per author openalex_id."""
    author_institutions = {}  # openalex_id -> Counter of institution names

    for filename in tqdm(os.listdir(dump_dir), desc="Scanning dump for affiliations"):
        filepath = os.path.join(dump_dir, filename)
        if not filepath.endswith(".json"):
            continue
        with open(filepath) as f:
            works = json.load(f)

        for work in works:
            for author in work.get("authors", []):
                author_id = author.get("id", "")
                if not author_id:
                    continue
                if author_id not in author_institutions:
                    author_institutions[author_id] = Counter()
                for inst in author.get("institutions", []):
                    name = inst.get("display_name", "")
                    if name:
                        author_institutions[author_id][name] += 1

    # Return most common institution per author
    result = {}
    for author_id, counter in author_institutions.items():
        if counter:
            result[author_id] = counter.most_common(1)[0][0]
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Generate RDF/Turtle for authors from pipeline data"
    )
    parser.add_argument("--input-json", required=True, type=Path,
                        help="Input complete_authors.json file")
    parser.add_argument("--input-corpus", required=False, type=Path, default=None,
                        help="Dump directory for affiliation data (optional)")
    parser.add_argument("--output", required=True, type=Path,
                        help="Output TTL file")
    args = parser.parse_args()

    with open(args.input_json) as f:
        data = json.load(f)

    authors = data["authors"]
    print(f"Loaded {len(authors)} authors")

    # Load affiliations from dump if provided
    affiliations = {}
    if args.input_corpus:
        affiliations = load_affiliations_from_dump(str(args.input_corpus))
        print(f"Found affiliations for {len(affiliations)} authors")

    # First pass: build custom ID mapping
    openalex_to_custom_id = {}
    counter = 1
    for author in authors:
        oa_id = author["openalex_id"].split("https://openalex.org/")[-1]
        if oa_id not in openalex_to_custom_id:
            openalex_to_custom_id[oa_id] = f"BKGA{counter:05d}"
            counter += 1

    # Second pass: build RDF graph
    g = Graph()
    ex = Namespace("http://example.org/")
    OA = Namespace("https://openalex.org/")
    ORCID = Namespace("https://orcid.org/")

    g.add((ex.Author, RDF.type, RDFS.Class))
    g.add((ex.Author, RDFS.label, Literal("Author")))

    g.bind("ex", ex)
    g.bind("oa", OA)
    g.bind("orcid", ORCID)
    g.bind("rdf", RDF)
    g.bind("rdfs", RDFS)

    # Define properties
    for prop, label in [
        (ex.customID, "AuthorID"),
        (OA.openAlexID, "OpenAlex ID"),
        (ORCID.ORCID, "ORCID"),
        (ex.total_no_publications, "total_no_publications"),
        (ex.no_publications_first_author, "no_publications_first_author"),
        (ex.affiliation, "affiliation"),
    ]:
        g.add((prop, RDF.type, RDF.Property))
        g.add((prop, RDFS.domain, ex.Author))
        g.add((prop, RDFS.range, RDFS.Literal))
        g.add((prop, RDFS.label, Literal(label)))

    for author in authors:
        oa_url = author["openalex_id"]
        oa_id = oa_url.split("https://openalex.org/")[-1]
        custom_id = openalex_to_custom_id[oa_id]

        name = author.get("name", "")
        orcid = author.get("orcid", "") or ""
        orc_id = orcid.split("https://orcid.org/")[-1] if orcid else ""
        total_pubs = str(author.get("total_publications", ""))
        first_author_pubs = str(author.get("first_author_publications", ""))
        affiliation = affiliations.get(oa_url, "")

        row_uri = URIRef(f"Author_{custom_id}")

        g.add((row_uri, ex["AuthorName"], Literal(name)))
        g.add((row_uri, ex["AuthorID"], Literal(custom_id)))
        g.add((row_uri, OA["OpenAlex_ID"], Literal(oa_id)))
        g.add((row_uri, ORCID["ORCID"], Literal(orc_id)))
        g.add((row_uri, ex["total_no_publications"], Literal(total_pubs)))
        g.add((row_uri, ex["no_publications_first_author"], Literal(first_author_pubs)))
        g.add((row_uri, ex["affiliation"], Literal(affiliation)))

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    g.serialize(destination=str(args.output), format="turtle")
    print(f"Graph serialized and saved to {args.output}")


if __name__ == "__main__":
    main()
