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

[....]

### Aggregate topics 

- Run `aggregate_topics.py`
  - input: `battery_data_topics_with_filtered_concepts.json`
  - output: `resources/data/openalex/authors_years`
