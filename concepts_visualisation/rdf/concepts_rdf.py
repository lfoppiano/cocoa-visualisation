import argparse
import json
import os
from pathlib import Path

from rdflib import Graph, Namespace, Literal, URIRef, RDFS
from rdflib.namespace import RDF
from tqdm import tqdm


def main():
    parser = argparse.ArgumentParser(
        description="Generate RDF/Turtle for concepts from dump data"
    )
    parser.add_argument("--input-corpus", required=True, type=Path,
                        help="Dump directory containing work JSON files")
    parser.add_argument("--output", required=True, type=Path,
                        help="Output TTL file")
    args = parser.parse_args()

    # First pass: collect unique concepts
    concepts = {}  # openalex_id -> {display_name, wikidata}
    for filename in tqdm(os.listdir(args.input_corpus), desc="Scanning concepts"):
        filepath = os.path.join(args.input_corpus, filename)
        if not filepath.endswith(".json"):
            continue
        with open(filepath) as f:
            works = json.load(f)

        for work in works:
            for concept in work.get("concepts", []):
                concept_url = concept.get("id", "")
                if not concept_url:
                    continue
                concept_id = concept_url.split("https://openalex.org/")[-1]
                if concept_id not in concepts:
                    wikidata = concept.get("wikidata", "") or ""
                    concepts[concept_id] = {
                        "display_name": concept.get("display_name", ""),
                        "wikidata": wikidata,
                    }

    print(f"Found {len(concepts)} unique concepts")

    # Build custom ID mapping
    openalex_to_custom_id = {}
    counter = 1
    for oa_id in concepts:
        openalex_to_custom_id[oa_id] = f"BKG{counter:05d}"
        counter += 1

    # Second pass: build RDF graph
    g = Graph()
    ex = Namespace("http://example.org/")
    OA = Namespace("https://openalex.org/")
    WD = Namespace("https://wikidata.org/wiki/")

    g.add((ex.Term, RDF.type, RDFS.Class))
    g.add((ex.Term, RDFS.label, Literal("Term")))

    g.bind("ex", ex)
    g.bind("oa", OA)
    g.bind("wd", WD)
    g.bind("rdf", RDF)
    g.bind("rdfs", RDFS)

    # Define properties
    for prop, label in [
        (ex.customID, "TermID"),
        (OA.openAlexID, "OpenAlex ID"),
        (WD.wikidataID, "Wikidata ID"),
    ]:
        g.add((prop, RDF.type, RDF.Property))
        g.add((prop, RDFS.domain, ex.Term))
        g.add((prop, RDFS.range, RDFS.Literal))
        g.add((prop, RDFS.label, Literal(label)))

    for oa_id, info in concepts.items():
        custom_id = openalex_to_custom_id[oa_id]
        display_name = info["display_name"]
        wikidata_url = info["wikidata"]
        wikidata_id = wikidata_url.split("https://www.wikidata.org/wiki/")[-1] if wikidata_url else ""

        row_uri = URIRef(f"term{display_name.replace(' ', '_')}")

        g.add((row_uri, ex["TermText"], Literal(display_name)))
        g.add((row_uri, ex["TermID"], Literal(custom_id)))
        g.add((row_uri, OA["OpenAlex_ID"], Literal(oa_id)))
        g.add((row_uri, WD["Wikidata_ID"], Literal(wikidata_id)))

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    g.serialize(destination=str(args.output), format="turtle")
    print(f"Graph serialized and saved to {args.output}")


if __name__ == "__main__":
    main()
