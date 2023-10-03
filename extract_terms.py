import pandas as pd
import numpy as np
from wordcloud import WordCloud
import json
from keybert import KeyBERT
from keyphrase_vectorizers import KeyphraseCountVectorizer
import os


pd.set_option('display.max_columns', None)

kw_model = KeyBERT()

# df=pd.DataFrame(columns=["id","doi","title","display_name","publication_year","publication_date","language","authors","concepts","abstract"])
#
# for filename in os.listdir("./data"):
#     with open("./data/"+filename) as jfile:
#         works = json.load(jfile)
#
#     dft = pd.DataFrame.from_records(works)
#     dft["abstract"]=dft["abstract"].fillna("")
#     df=df.append(dft,ignore_index = True)
#
# #print (df)
#
# #df.to_csv('battery_all.csv')


df=pd.read_csv("battery_all.csv")
print(len(df))


keyterms_T=[]
keyterms_A=[]


for idx in df.index:
    print(idx)
    if df["title"][idx]=="":
        keyterms_T.append([])
    else:
        try:
            keyterms_T.append(kw_model.extract_keywords(docs=df["title"][idx] ,vectorizer=KeyphraseCountVectorizer()))
        except:
            keyterms_T.append([])

    if df["abstract"][idx]=="":
        keyterms_A.append([])
    else:
        try:
            keyterms_A.append(kw_model.extract_keywords(docs=df["abstract"][idx] ,vectorizer=KeyphraseCountVectorizer(),top_n=5))
        except:
            keyterms_A.append([])


df["keyterms_T"]=keyterms_T

df["keyterms_A"]=keyterms_A

print(len(keyterms_T))
print(len(keyterms_A))


print(len(df))

df.to_csv('battery_all_KT.csv')





