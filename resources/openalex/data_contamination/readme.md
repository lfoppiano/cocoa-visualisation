# Data contamination 

Data contamination between Openalex Battery topic and Batterybert corpus used for pre-training

- Extract dois from dumped data
    
    > jq '.[].doi' resources/data/openalex/data/*.json > dois.txt

- Sort
    > gsort dois_openalex.txt > dois_openalex.sorted.txt

        - 189581 sorted values
    
    > gsort dois_batterybert.txt > dois_batterybert.sorted.txt
        
        - 400466 sorted values      
   
- Remove duplicates 

  > cat dois_openalex.sorted.txt | uniq > dois_openalex.sorted.uniqe.txt

     - 145168 uniques values

  > cat dois_openalex.sorted.txt | uniq > dois_openalex.sorted.uniqe.txt
  
     - 339240 uniques values



- Compare and count
    > comm -12 dois_batterybert.sorted.txt dois_openalex.sorted.txt  | wc -l 

        - 19310 common DOIs

    > comm -12 dois_batterybert.sorted.uniqe.txt dois_openalex.sorted.uniqe.txt  | wc -l
  
        - 19280 common DOIs
