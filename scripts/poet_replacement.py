import subprocess
import re
import requests
import pandas as pd
import csv
import sys
import logging
import argparse


# Increase the field size limit
csv.field_size_limit(sys.maxsize)


logger = logging.basicConfig(filename='poet_replacement.log',
                    level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


def map_mesh_to_poet(ontology_database_name:str):
    api_url = f"https://ontology.jax.org/api/{ontology_database_name}/terms/"
    response = requests.get(api_url)
    data = response.json()

    # Initialize an empty dictionary to store the MESH to MONDO mappings
    mesh_to_poet= {}

    # Iterate through each item in the response
    for item in data:
        # Extract the ID and xrefs for each item
        map_id = item.get('id')
        xrefs = item.get('xrefs')

        # Iterate through each xref and add the MESH to MONDO mapping to the dictionary
        for xref in xrefs:
            if xref.startswith(('MESH:', 'MSH:', 'MeSH:')):
                mesh_code = xref.split(':')[1] 
                mesh_to_poet[mesh_code] = map_id
    
    logging.info(f'The lenth of MeSH to {ontology_database_name} mapping is : {len(mesh_to_poet)}')
    
    return mesh_to_poet

def map_mesh(mesh_id:str):
    if mesh_id in mesh_to_mondo_dict:
        return mesh_to_mondo_dict.get(mesh_id)
    elif mesh_id in mesh_to_hp_dict:
        return mesh_to_hp_dict.get(mesh_id)
    elif mesh_id in mesh_to_maxo_dict:
        return mesh_to_maxo_dict.get(mesh_id)
    
    # If neither command returns a result
    logging.info(f'No mapping found for MESH : {mesh_id}')
    return None


def replace_disease_in_text(text:str):
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

def process_tsv_and_replace_disease(input_tsv_path:str, output_tsv_path:str):
    with open(input_tsv_path, mode='r', encoding='utf-8') as infile, \
        open(output_tsv_path, mode='w', encoding='utf-8', newline='') as outfile:
        
        reader = csv.reader(infile, delimiter='\t')
        writer = csv.writer(outfile, delimiter='\t')
        
        for row in reader:
            if not row or len(row) < 2:
                continue
            
            pmc_id = row[0]
            relationships = row[1]
            original_text = row[2]
            updated_relationships = replace_disease_in_text(relationships)
            updated_text = replace_disease_in_text(original_text)
            
            writer.writerow([pmc_id, updated_relationships, updated_text])
        
        print(f"Processed and saved updated texts to: {output_tsv_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input_tsv_path", required=True, help="Path to mesh replaced tsv.")
    parser.add_argument("-o", "--output_tsv_path", required=True, help="Path to where POET Replacemnt will be stored")
    
    args = parser.parse_args()

    mesh_to_mondo_dict = map_mesh_to_poet('mondo')
    mesh_to_hp_dict = map_mesh_to_poet('hp')
    mesh_to_maxo_dict = map_mesh_to_poet('maxo')

    process_tsv_and_replace_disease(args.input_tsv_path,args.output_tsv_path)


    



"""

# Sample way of running the code:
python poet_replacement.py  -i ../dump/mesh_replaced.tsv -o ../dump/poet_replaced.tsv 

python poet_replacement.py  -i ../data/sickle_cell_mesh_replaced.tsv -o ../data/sickle_cell_poet_replaced.tsv 



* sickle cell
* morphine 
* cystic fibrosis

"""