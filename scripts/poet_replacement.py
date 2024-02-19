import subprocess
import re
import requests
import pandas as pd
import csv
import sys

# Increase the field size limit
csv.field_size_limit(sys.maxsize)

def map_mesh(mesh_id):
    # Try to extract MONDO ID
    if mesh_id in mesh_to_mondo:
        return mesh_to_mondo.get(mesh_id)
    elif mesh_id in mesh_to_hp:
        return mesh_to_hp.get(mesh_id)
    elif mesh_id in mesh_to_maxo:
        return mesh_to_maxo.get(mesh_id)
    
    # If neither command returns a result
    print(f"No mapping found for MESH:{mesh_id}.")
    return None


def replace_disease_in_text(text):
    # Regular expression to find "diseaseDxxxxxx"
    pattern = re.compile(r'(disease)(D\d{6})')
    
    # Function to replace each match
    def replace_func(match):
        prefix = match.group(1)  # Extract the "disease" prefix
        mesh_id = match.group(2)  # Extract MESH ID
        mapped_id = map_mesh(mesh_id)  
        if mapped_id:
            return f"{mapped_id}"  
        else:
            return match.group(0)  # Return the original text if no corresponding mapping found
    
    # Replace all occurrences in the text
    updated_text = pattern.sub(replace_func, text)
    return updated_text

def process_tsv_and_replace_disease(input_tsv_path, output_tsv_path):
    with open(input_tsv_path, mode='r', encoding='utf-8') as infile, \
         open(output_tsv_path, mode='w', encoding='utf-8', newline='') as outfile:
        
        reader = csv.reader(infile, delimiter='\t')
        writer = csv.writer(outfile, delimiter='\t')
        
        for row in reader:
            if not row or len(row) < 2:
                continue
            
            pmc_id = row[0]
            original_text = row[1]
            updated_text = replace_disease_in_text(original_text)
            
            writer.writerow([pmc_id, updated_text])
        
        print(f"Processed and saved updated texts to: {output_tsv_path}")



### 1. Create a MESH to MONDO Dictionary 

api_url = "https://ontology.jax.org/api/mondo/terms/"
response = requests.get(api_url)
data = response.json()

# Initialize an empty dictionary to store the MESH to MONDO mappings
mesh_to_mondo = {}

# Iterate through each item in the response
for item in data:
    # Extract the ID and xrefs for each item
    mondo_id = item.get('id')
    xrefs = item.get('xrefs')

    # Iterate through each xref and add the MESH to MONDO mapping to the dictionary
    for xref in xrefs:
        if xref.startswith(('MESH:', 'MSH:', 'MeSH:')):
            mesh_code = xref.split(':')[1] 
            mesh_to_mondo[mesh_code] = mondo_id
            

print(mesh_to_mondo)

### 2. Create a MESH to HP Dictionary 

api_url = "https://ontology.jax.org/api/hp/terms/"
response = requests.get(api_url)
data = response.json()

# Initialize an empty dictionary to store the HP to MONDO mappings
mesh_to_hp = {}

# Iterate through each item in the response
for item in data:
    # Extract the ID and xrefs for each item
    hp_id = item.get('id')
    xrefs = item.get('xrefs')

    # Iterate through each xref and add the MESH to HP mapping to the dictionary
    for xref in xrefs:
        if xref.startswith(('MESH:', 'MSH:', 'MeSH:')):
            mesh_code = xref.split(':')[1] 
            mesh_to_hp[mesh_code] = hp_id

print(mesh_to_hp)

### 3. Create a MESH to MaXO Dictionary 

api_url = "https://ontology.jax.org/api/maxo/terms/"
response = requests.get(api_url)
data = response.json()

# Initialize an empty dictionary to store the MaXO to MONDO mappings
mesh_to_maxo = {}

# Iterate through each item in the response
for item in data:
    # Extract the ID and xrefs for each item
    maxo_id = item.get('id')
    xrefs = item.get('xrefs')

    # Iterate through each xref and add the MESH to MaXO mapping to the dictionary
    for xref in xrefs:
        if xref.startswith(('MESH:', 'MSH:', 'MeSH:')):
            mesh_code = xref.split(':')[1] 
            mesh_to_maxo[mesh_code] = maxo_id

print(mesh_to_maxo)




# Example usage
input_tsv_path = 'mesh_replaced.tsv'
output_tsv_path = 'poet_replaced.tsv'
process_tsv_and_replace_disease(input_tsv_path, output_tsv_path)
