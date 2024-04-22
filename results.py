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

pmed_dict = {}

for i in pmids:
    pmid_out = out_key[out_key[outkey_def[0]].isin([i])]
    
    out_maxo = pmid_out[outkey_def[1]].dropna().unique() # maxo ids
    out_hp = pmid_out[outkey_def[2]].dropna().unique() # hpo ids
    out_mon = pmid_out[outkey_def[3]].dropna().unique() # mondoids
    
    grounded_maxo = np.array([])
    grounded_hp = np.array([])
    grounded_mon = np.array([])    
    for j in range(pmid_out.shape[0]):        
        match_maxo = np.array(re.findall(r"MAXO:\d{7}", pmid_out[outkey_def[2]].iloc[j]))
        grounded_maxo = np.append(grounded_maxo, match_maxo)
        
        match_hp = np.array(re.findall(r"HP:\d{7}", pmid_out[outkey_def[4]].iloc[j]))
        grounded_hp = np.append(grounded_hp, match_hp)

        match_mon = np.array(re.findall(r"MONDO:\d{7}", pmid_out[outkey_def[6]].iloc[j]))
        grounded_mon = np.append(grounded_mon, match_mon)
        
    out_maxo = np.append(out_maxo, grounded_maxo)
    out_maxo = out_maxo.astype('U') # make numpy array into unicode, so char.lower() works
    out_maxo = np.char.lower(out_maxo)

    out_hp = np.append(out_hp, grounded_hp)
    out_hp = out_hp.astype('U') # make numpy array into unicode, so char.lower() works
    out_hp = np.char.lower(out_hp)

    out_mon = np.append(out_mon, grounded_mon)
    out_mon = out_mon.astype('U') # make numpy array into unicode, so char.lower() works
    out_mon = np.char.lower(out_mon)

    pmed_dict[i] = {'maxo': out_maxo, 'hpo': out_hp, 'mondo': out_mon}

count_unnorm_max = 0
count_precision_max = 0

count_unnorm_hp = 0
count_precision_hp = 0

count_unnorm_mon = 0
count_precision_mon = 0

for i in range(len(gold_key)):
    pid = gold_key.loc[i, goldkey_def[0]]

    maxocode = gold_key.loc[i, goldkey_def[1]].lower()
    if len(pmed_dict[pid]['maxo'])>0:
        count_precision_max += 1
    if maxocode in pmed_dict[pid]['maxo']:
        count_unnorm_max += 1

    hpocode = gold_key.loc[i, goldkey_def[2]].lower()
    if len(pmed_dict[pid]['hpo'])>0:
        count_precision_hp += 1
    if hpocode in pmed_dict[pid]['hpo']:
        count_unnorm_hp += 1

    mondocode = gold_key.loc[i, goldkey_def[3]].lower()
    if len(pmed_dict[pid]['mondo'])>0:
        count_precision_mon += 1
    if mondocode in pmed_dict[pid]['mondo']:
        count_unnorm_mon += 1

#=========================================
# MAXO RESULTS
print(f"The number of MAxO IDs automatically retrieved are {count_unnorm_max}, out of {gold_key.shape[0]},")
# result 14/67
freq_match_max = count_unnorm_max/gold_key.shape[0]
print(f"corresponding to {freq_match_max:.0%} of correctly generated MAxO terms.")
# result 21%
precision_max = count_unnorm_max/count_precision_max
print(f"The precision, i.e. the number of correctly retrieved MAxO ID terms divided by the total number of predictions is {precision_max:.0%}.\n")
# result 36%

#=========================================
# HPO RESULTS
print(f"The number of HPO IDs automatically retrieved are {count_unnorm_hp}, out of {gold_key.shape[0]},")
# result 7/67
freq_match_hp = count_unnorm_hp/gold_key.shape[0]
print(f"corresponding to {freq_match_hp:.0%} of correctly generated HPO terms.")
# result 10%
precision_hp = count_unnorm_hp/count_precision_hp
print(f"The precision, i.e. the number of correctly retrieved HPO ID terms divided by the total number of predictions is {precision_hp:.0%}.\n")
# result 11%

#=========================================
# MONDO RESULTS
print(f"The number of MONDO IDs automatically retrieved are {count_unnorm_mon}, out of {gold_key.shape[0]},")
# result 9/67
freq_match_mon = count_unnorm_mon/gold_key.shape[0]
print(f"corresponding to {freq_match_mon:.0%} of correctly generated MONDO terms.")
# result 13%
precision_mon = count_unnorm_mon/count_precision_mon
print(f"The precision, i.e. the number of correctly retrieved MONDO ID terms divided by the total number of predictions is {precision_mon:.0%}.\n")
# result 18%
