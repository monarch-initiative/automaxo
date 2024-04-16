#===============================================================
# 12-16/4/24 LC
# Analysis of the results of AutoMAxO. Inputs are
#   (1) A subset of the "golden standard" of manually curated
#       MAxO terms; we have 67.
#   (2) The terms automatically genereated by AutoMAxO by  
#       running the same 67 aforementioned Pubmed IDs.
# 
# As of now, we only show how many of the MAxO terms of (1) are
# also present in (2), i.e. only true positives.
#===============================================================
# TODO
# [a] Expand on number of keys (HPO, ...) that can be used.
# [b] Look at better perfromance metrics.
#===============================================================
import numpy as np
import scipy as sp
import pandas as pd
import re
import os

#===============================================================
# FOR NOW by hand ! Edit with care ;)
gold_std_file = "/../retrived_maxo_annotations_df.xlsx"
output_file = "/../fuzy_oak_evaluation_summary_post_ontoGPT_df.xlsx"
which_gold_clmn = [0, 1] 
which_output_clmn = [0, 1, 4] # depends on the structure of the above files, of course
# Ungrounded also possible:
# "/../oak_evaluation_summary_post_ontoGPT_df.xlsx"
#===============================================================

# import data as pandas DataFrame
DIR = os.getcwd()
df_gold = pd.read_excel(DIR + gold_std_file)
df_out  = pd.read_excel(DIR + output_file)
goldkey_def = df_gold.columns[which_gold_clmn]
outkey_def = df_out.columns[which_output_clmn]

gold_key = df_gold[goldkey_def].copy()
out_key = df_out[outkey_def].copy()

pmids = gold_key.citation.unique()

pmed_max_dict = {}
count = 0
for i in pmids:
    #pmid_out = out_key[out_key['Citation'].isin([i])]
    pmid_out = out_key[out_key[outkey_def[0]].isin([i])]
    out_maxo = pmid_out[outkey_def[1]].dropna().unique() # maxo ids
    grounded_maxo = np.array([])
    for j in range(len(pmid_out[outkey_def[2]])):
        match = np.array(re.findall(r"MAXO:\d{7}", pmid_out['Potential MAXO'].iloc[j]))
        grounded_maxo = np.append(grounded_maxo, match)
    out_maxo = np.append(out_maxo, grounded_maxo)
    out_maxo = out_maxo.astype('U') # make numpy array into unicode, so char.lower() works
    out_maxo = np.char.lower(out_maxo)
    pmed_max_dict[i] = out_maxo

for i in range(len(gold_key)):
    pid = gold_key.loc[i, goldkey_def[0]]
    maxocode = gold_key.loc[i, goldkey_def[1]].lower()
    if maxocode in pmed_max_dict[pid]:
        count += 1

print(f"The number of MAxO IDs automatically annotated are {count}, out of {gold_key.shape[0]},")
# result 14/67

freq_match = count/gold_key.shape[0]
print(f"corresponding to {freq_match:.0%} of correctly generated MAxO terms.")

# result 0.21, not bad for now :)
