import argparse
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from tqdm import tqdm
from wordcloud import WordCloud


def main():
    parser = argparse.ArgumentParser(
        description="Generate word cloud visualizations for author vectors"
    )
    parser.add_argument("--input-author-vectors", required=True,
                        help="Input JSON file (author_vectors.json or complete_authors.json)")
    parser.add_argument("--output-dir", required=True,
                        help="Output directory for PNG files")
    parser.add_argument("--start-index", type=int, default=0,
                        help="Start index for author processing (default: 0)")
    parser.add_argument("--limit", type=int, default=None,
                        help="Max number of authors to process (default: all)")
    parser.add_argument("--dpi", type=int, default=170,
                        help="DPI for output images (default: 170)")
    parser.add_argument("--colormap", default="Dark2",
                        help="Matplotlib colormap name (default: Dark2)")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    with open(args.input_author_vectors) as f:
        data = json.load(f)

    term_lst = data["terms"]
    authors = data["authors"]

    end_index = len(authors)
    if args.limit is not None:
        end_index = min(args.start_index + args.limit, len(authors))

    selected = authors[args.start_index:end_index]
    print(f"Generating word clouds for {len(selected)} authors "
          f"(index {args.start_index} to {end_index - 1})")

    for author in tqdm(selected, desc="Generating word clouds"):
        freqs = dict(zip(term_lst, author["vector"]))
        # Filter out zero-weight terms
        freqs = {k: v for k, v in freqs.items() if v > 0}

        if not freqs:
            continue

        filename = author["openalex_id"].replace("https://openalex.org/", "")

        w = WordCloud(
            collocations=False,
            background_color="white",
            prefer_horizontal=1,
            colormap=args.colormap
        ).generate_from_frequencies(frequencies=freqs)

        plt.imshow(w, interpolation="bilinear")
        plt.axis("off")
        plt.savefig(
            os.path.join(args.output_dir, filename + ".png"),
            dpi=args.dpi,
            format="png",
            bbox_inches="tight"
        )
        plt.close()


if __name__ == "__main__":
    main()
