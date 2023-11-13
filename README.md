# Concept-CoAuthors (COCOA) visualisation

## Table of content 
- [Before starting](#before-starting)
- [Workflow](#workflow)
- [Keyword extraction evaluation](#keyword-extraction-evaluation-)
  + [Algorithm 1a](#algorithm-1a) 
  + [Algorithm 1b](#algorithm-1b)
  + [Algorithm 2](#algorithm-2)
  + [Top results](#top-results)


## Before starting

### Clone / Checkout

```bash
git lfs install 
```

### Configuration

Create a file `.env` in the root directory of the project and add any of the following environment variables:

```
OPENALEX_API_KEY=
OPENALEX_CONFIG_EMAIL=

HTTP_PROXY=
HTTPS_PROXY=
CURL_CA_BUNDLE=
REQUEST_CA_BUNDLE=
REQUESTS_CA_BUNDLE=
```

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

```bash
find data -type f -name "*.xml" -exec grep -q '<keywords>' {} \; -exec dirname {} \; | sort -u | xargs -I {} cp -r {} /Users/lfoppiano/development/projects/concepts-visualisation/resources/data/openalex/sample_with_keywords/
```

We extracted the list of `<keywords><term></term><....` from the tei.xml files from Grobid.

> command to be added

We process the abstracts using the three methods:

```bash
for file in resources/openalex/data/sample_with_keywords/*/*.abstract.openalex.txt; do echo ${file}; python concepts_visualisation/openalex/extract_keywords.py --input $file --output "${file%.abstract.openalex.txt}.keybert.json" ; done
```

```bash
for file in resources/openalex/data/sample_with_keywords/*/*.abstract.openalex.txt; do echo ${file}; python concepts_visualisation/openalex/extract_keywords.py --input $file --output "${file%.abstract.openalex.txt}.batteryonlybert.json" --transformer ../embeddings/pre-trained-embeddings/batteryonlybert-cased/ ; done
```

```bash
for file in resources/openalex/data/sample_with_keywords/*/*.abstract.openalex.txt; do echo ${file}; python concepts_visualisation/openalex/extract_keywords_llm.py --input $file --output "${file%.abstract.openalex.txt}.chatgpt.json"; done
```

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

Results are reported [here](#keyword-extraction-evaluation-).

### Aggregate topics

- Run `aggregate_topics.py`
    - input: `battery_data_topics_with_filtered_concepts.json`
    - output: `resources/data/openalex/authors_years`



## Keyword extraction evaluation 

### Algorithm 1a:

1. Read the 3 files + the expected file
2. Remove the confidence scores when needed and trim each list to the minimum length between the three extracting methods (e.g. if keybert extracted only 5 and the other extracted 10 keywords, we limit all to the 5 most important keywords)
3. For each document,
    - for each method:
        - sort the keywords 
        - search for the most similar one in the expected list (basd on sentence BERT)
        - sum the similarity score - continue, ignoring the matching expected keyword
    - calculate average for in the same method
    - sum each average similarity by method
4. average by the number of documents (100)

Results @5 keywords:

| method                 | avg. similarity |
|------------------------|-----------------|
| keybert                | 0.3806          |
| chatgpt                | 0.3798          |
| batteryscibert_cased   | 0.2978          |
| batteryonlybert        | 0.2904          |
| batteryscibert_uncased | 0.2382          |

Results @10 keywords:

N/A The algorithm was fixed because we realised that the sorting was penalising possible matches. 

### Algorithm 1b

**TLDR**: Same as Algorithm 1 but without the sorting at the beginning

1. Read the 3 files + the expected file
2. Remove the confidence scores when needed and trim each list to the minimum length between the three extracting methods (e.g. if keybert extracted only 5 and the other extracted 10 keywords, we limit all to the 5 most important keywords)
3. For each document,
    - for each method:
        - search for the most similar one in the expected list (basd on sentence BERT)
        - sum the similarity score - continue, ignoring the matching expected keyword
    - calculate average for in the same method
    - sum each average similarity by method
4. average by the number of documents (100)

Results @5 keywords:

| method                 | avg. similarity |
|------------------------|-----------------|
| chatgpt                | 0.3915          |
| keybert                | 0.3799          |
| batteryscibert_cased   | 0.2955          |
| batteryonlybert        | 0.2817          |
| batteryscibert_uncased | 0.2388          |

Results @10 keywords:

| method                 | avg. similarity |
|------------------------|-----------------|
| chatgpt                | 0.2182          |
| keybert                | 0.2102          |
| batteryscibert_cased   | 0.1674          |
| batteryonlybert        | 0.1616          |
| batteryscibert_uncased | 0.1375          |

### Algorithm 2

Goal: evaluating while expanding the keywords

1. Read the 3 files + the expected file
2. Remove the confidence scores when needed and trim each list to the minimum length between the three extracting methods (e.g. if keybert extracted only 5 and the other extracted 10 keywords, we limit all to the 5 most important keywords)
3. For each document:
    - for each expected keyword:
        - get similarity with each predicted keyword 
        - filter similarities > 0.5 
        - sum the cosine similarity 
    - calculate average for in the same method
    - sum each average similarity by method
4. average by the number of documents (100)


Results @5 keywords:

| method                 | avg. similarity |
|------------------------|-----------------|
| chatgpt                | 0.6827          |
| keybert                | 0.6340          |
| batteryscibert_cased   | 0.5625          |
| batteryonlybert        | 0.5063          |
| batteryscibert_uncased | 0.4133          |

Results @10 keywords:

| method                 | avg. similarity |
|------------------------|-----------------|
| chatgpt                | 0.6983          |
| keybert                | 0.6431          |
| batteryscibert_cased   | 0.6204          |
| batteryonlybert        | 0.6063          |
| batteryscibert_uncased | 0.5609          |

### Top results

We re-evaluated using abstracts from OpenAlex, and algorithm 2a over extraction of 10 keywords.  

| method                 | avg. similarity  |
|------------------------|------------------|
| chatgpt                | 0.6781           |
| batteryscibert_cased   | 0.6698           |
| batteryonlybert        | 0.6677           |
| keybert                | 0.6665           |
| batteryscibert_uncased | 0.5423           |

