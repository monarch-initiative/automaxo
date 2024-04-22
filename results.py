#===============================================================
# Leonardo Chimirri - BIH Charité
#
# Analysis of the results of AutoMAxO. Inputs are
#   (1) A subset of the "golden standard" of manually curated
#       MAxO terms; we have 67.
#   (2) The terms automatically genereated by AutoMAxO by  
#       running the same 67 aforementioned Pubmed IDs.
# 
# We show how many of the:
#       [1] MAxO terms of (1) also present in (2), with grounding
#       [2] percentage representation of [1]
#       [3] TP of MAxO terms/# of predictions
#       [4] HPO terms of (1) also present in (2), with grounding
#       [5] percentage representation of [4]
#       [6] TP of HPO terms/# of predictions
#       [7] MONDO terms of (1) also present in (2), with grounding
#       [8] percentage representation of [7]
#       [9] TP of MONDO terms/# of predictions

#===============================================================
import numpy as np
import scipy as sp
import pandas as pd
import re
import os
import collections

#===============================================================
# Naming: "out" related to output of automaxo, "gold" to manually curated
gold_std_file = "/more_grounding/retrived_maxo_annotations_df.xlsx"
output_file = "/more_grounding/fuzy_oak_evaluation_summary_post_ontoGPT_df.xlsx"
which_gold_clmn = [0, 1, 3, 5] 
which_output_clmn = [0, 1, 4, 6, 9, 10, 13] # depends on the structure of the above files, of course
# Ungrounded also possible:
# "/more_grounding/oak_evaluation_summary_post_ontoGPT_df.xlsx"

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
pmed_dict = collections.defaultdict(list)

regmatch = [r"MAXO:\d{7}", r"HP:\d{7}", r"MONDO:\d{7}"]
dict_entr = ['maxo', 'hpo', 'mondo']

for i in pmids:
    pmid_out = out_key[out_key[outkey_def[0]].isin([i])]

    for k in [0,1,2]:
        outs = pmid_out[outkey_def[k+1]].dropna().unique() # ids
        grounded = np.array([])
        for j in range(pmid_out.shape[0]):        
            matches = np.array(re.findall(regmatch[k], pmid_out[outkey_def[2*(k+1)]].iloc[j]))
            grounded = np.append(grounded, matches)
        outs = np.append(outs, grounded)
        outs = outs.astype('U') # make numpy array into unicode, so char.lower() works
        outs = np.char.lower(outs)
        pmed_dict[i].append({dict_entr[k]: outs})

count_unnorm = [0, 0, 0]
count_precision =  [0, 0, 0]
for i in range(len(gold_key)):
    pid = gold_key.loc[i, goldkey_def[0]]
    for k in [1,2,3]:
        code = gold_key.loc[i, goldkey_def[k]].lower()
        if len(pmed_dict[pid][k-1][dict_entr[k-1]])>0:
            count_precision[k-1] += 1
        if code in pmed_dict[pid][k-1][dict_entr[k-1]]:
            count_unnorm[k-1] += 1

print(f"The number of MAXO, HPO, and MONDO IDs automatically retrieved are {count_unnorm}, out of {gold_key.shape[0]},")

freq_match = [x/gold_key.shape[0] for x in count_unnorm]
print(f"corresponding to correctly generated terms (percentage):")
print(freq_match)

precision = []
print(f"The precision, i.e. the number of correctly retrieved ID terms divided by the total number of predictions is:\n")
for i in [0,1,2]:
    precision.append(count_unnorm[i]/count_precision[i])
    print(f"{precision[i]:.0%}\n")
#precision = count_unnorm/count_precision
#print(f"The precision, i.e. the number of correctly retrieved ID terms divided by the total number of predictions is {precision:.0%}.\n")
