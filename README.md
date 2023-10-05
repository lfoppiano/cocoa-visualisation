# Concept-CoAuthors (COCOA) visualisation

## Workflow

### Fetch the data from OpenAlex

- Run `fetch.py`
    - output in `resources/data/openalex/data`

### Convert CSV from Dieb-san with KeyBERT extracted information

- Run `csv_to_json.py`
    - input: `battery_all-KT.csv`
    - output: `battery_data_topics_original.json`

### Cleanup data by removing "ancestors concepts"

- Run `clean_concepts.py`
    - input: `battery_data_topics_original.json`
    - output: `battery_data_topics_with_filtered_concepts.json`

### Run keybert

- Run `extract_keywords.py`
    - input: `data/openalex/dump`
    - output: `data/openalex/dump_with_keybert`

### Evaluate keywords

Compute an evaluation between different extraction methods with the keywords extracted from the PDF document. We use https://github.com/kermitt2/article_dataset_builder to download and process documents with grobid. We provide article_dataset_builder with the list of deduplicated DOIS: [dois_openalex.sorted.uniqe.txt](resources%2Fdata%2Fopenalex%2Fdata_contamination%2Fdois_openalex.sorted.uniqe.txt)

We collect the data from the structure created by article_dataset_builder:

> find data -type f -name "*.xml" -exec grep -q '<keywords>' {} \; -exec dirname {} \; | sort -u | xargs -I {} cp -r {} /Users/lfoppiano/development/projects/concepts-visualisation/resources/data/openalex/sample_with_keywords/

We extracted the list of <keywords><term></term><.... from the tei.xml files from Grobid.

> command to be added

We process the abstracts using the three methods:

> for file in resources/data/openalex/sample_with_keywords/
*/*.abstract.txt; do echo ${file}; python concepts_visualisation/openalex/extract_keywords.py --input $file --output "${file%.abstract.txt}.keybert.json" ; done

> for file in resources/data/openalex/sample_with_keywords/
*/*.abstract.txt; do echo ${file}; python concepts_visualisation/openalex/extract_keywords.py --input $file --output "${file%.abstract.txt}.batteryonlybert.json" --transformer ../embeddings/pre-trained-embeddings/batteryonlybert-cased/ ; done

> for file in resources/data/openalex/sample_with_keywords/
*/*.abstract.txt; do echo ${file}; python concepts_visualisation/openalex/extract_keywords_llm.py --input $file --output "${file%.abstract.txt}.chatgpt.json"; done


The structure of the sample is as follow:

- corpus
    + file1
        + file1.abstract.txt: Abtract
        + file1.batteryonlybert.json:: keywords extracted by batteryonlybert-cased
        + file1.keybert.json: keywords extracted by keybert
        + file1.chatgpt.json: keywords extracted by chatgpt
        + file1.keywords.txt: the expected keywords
        + file1......
    + file2
        + ....

We finally process the metrics

> python concepts_visualisation/openalex/evaluate_keywords.py --input resources/data/openalex/sample_with_keywords

Algorithm:

1. Read the 3 files + the expected file
2. Remove the confidence scores when needed and trim each list to the minimum length between the three extracting methods (e.g. if keybert extracted only 5 and the other extracted 10 keywords, we limit all to the 5 most important keywords)
3. For each document,
    - for each method:
      - sort the keywords - search for the most similar one in the expected list (basd on sentence BERT)
      - sum the similarity score - continue, ignoring the matching expected keyword
    - calculate average for in the same method
    - sum each average similarity by method
4. average by the number of documents (100)

Results:

| method                 | avg. similarity |
|------------------------|-----------------|
| keybert                | 0.3806          |
| batteryonlybert        | 0.2904          |
| chatgpt                | 0.3798          |
| batteryscibert_cased   | 0.2978          |
| batteryscibert_uncased | 0.2382          |

[....]

### Aggregate topics

- Run `aggregate_topics.py`
    - input: `battery_data_topics_with_filtered_concepts.json`
    - output: `resources/data/openalex/authors_years`
