# Data contamination 

Data contamination between Openalex Battery topic and Batterybert corpus used for pre-training

- Extract dois from dumped data
    
    > jq '.[].doi' resources/data/openalex/data/*.json > dois.txt

- Sort
    > gsort dois_openalex.txt > dois_openalex.sorted.txt
    
    > gsort dois_batterybert.txt > dois_batterybert.sorted.txt


- Compare and count
    > comm -12 dois_batterybert.sorted.txt dois_openalex.sorted.txt  | wc -l 