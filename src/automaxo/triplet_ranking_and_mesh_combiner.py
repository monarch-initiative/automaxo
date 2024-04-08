import os
import yaml
import json
import csv
from collections import defaultdict
import click
from typing import List, Tuple, DefaultDict
from tqdm import tqdm

def load_yaml_files(directory_path: str) -> list:
    """
    Load YAML files from a specified directory and return their contents along with PubMed IDs.
    
    Args:
        directory_path (str): Path to the directory containing YAML files.
    
    Returns:
        list: A list of dictionaries, each containing the contents of a YAML file and its corresponding PubMed ID.
    """
    yaml_files = [f for f in os.listdir(directory_path) if f.endswith('.yaml')]
    data = []

    for file_name in tqdm(yaml_files, desc="Loading YAML files", total=len(yaml_files)):
        with open(os.path.join(directory_path, file_name), 'r') as f:
            content = yaml.safe_load(f)
            if content:
                pubmed_id = os.path.splitext(file_name)[0]
                content['pubmed_id'] = pubmed_id
                data.append(content)

    return data


def extract_triplets(data: list) -> list:
    triplets = []
    named_entities = {}

    for article in data:
        pubmed_id = article['pubmed_id']
        named_entities_dict = {ne['id']: ne['label'] for ne in article.get('named_entities', [])}
        named_entities[pubmed_id] = named_entities_dict

        for triplet in article.get('extracted_object', {}).get('action_annotation_relationships', []):
            subject = triplet.get('subject', '').strip('<>')
            predicate = triplet.get('predicate', '').strip('<>')
            object_ = triplet.get('object', '').strip('<>')
            qualifier = triplet.get('qualifier', '').strip('<>').replace('None', '').replace('Not applicable', '')
            subject_qualifier = triplet.get('subject_qualifier', '').strip('<>').replace('None', '').replace('Not applicable', '')
            object_qualifier = triplet.get('object_qualifier', '').strip('<>').replace('None', '').replace('Not applicable', '')
            subject_extension = triplet.get('subject_extension', '').strip('<>').replace('None', '').replace('Not applicable', '')
            object_extension = triplet.get('object_extension', '').strip('<>').replace('None', '').replace('Not applicable', '')

            if not (subject and predicate and object_):
                continue  # Skip if any of subject, predicate, or object is missing

            subject_label = named_entities_dict.get(subject, '')
            object_label = named_entities_dict.get(object_, '')

            triplets.append({
                'subject': {subject: subject_label},
                'predicate': predicate,
                'object': {object_: object_label},
                'qualifier': qualifier,
                'subject_qualifier': subject_qualifier,
                'object_qualifier': object_qualifier,
                'subject_extension': subject_extension,
                'object_extension': object_extension,
                'pubmed_id': pubmed_id
            })

    return triplets


def count_triplets(triplets: list) -> defaultdict:
    """
    Count the frequency of each triplet and track the PubMed IDs associated with each triplet.
    
    Args:
        triplets (list): A list of extracted triplets.
    
    Returns:
        defaultdict: A dictionary with triplets as keys and their count and associated PubMed IDs as values.
    """
    triplet_counts = defaultdict(lambda: {'count': 0, 'pubmed_ids': set()})
    for triplet in triplets:
        subject_str = f"{list(triplet['subject'].keys())[0]}: {list(triplet['subject'].values())[0]}"
        object_str = f"{list(triplet['object'].keys())[0]}: {list(triplet['object'].values())[0]}"
        predicate = triplet['predicate']
        qualifier = triplet['qualifier']
        subject_qualifier = triplet['subject_qualifier']
        object_qualifier = triplet['object_qualifier']
        subject_extension = triplet['subject_extension']
        object_extension = triplet['object_extension']
        pubmed_id = triplet['pubmed_id']

        key = (subject_str, predicate, object_str, qualifier, subject_qualifier, object_qualifier, subject_extension, object_extension)

        triplet_counts[key]['count'] += 1
        triplet_counts[key]['pubmed_ids'].add(pubmed_id)

    return triplet_counts


def rank_triplets(triplet_counts: DefaultDict) -> List[Tuple]:
    """
    Rank triplets based on their frequency.

    Args:
        triplet_counts: A dictionary where each key is a triplet (excluding the PubMed ID) and each value
                        is a dictionary containing the count of the triplet and a set of PubMed IDs associated with the triplet.

    Returns:
        A list of tuples, each representing a triplet and its associated count and PubMed IDs, sorted by count in descending order.
    """
    ranked_triplets = sorted(triplet_counts.items(), key=lambda x: x[1]['count'], reverse=True)
    return ranked_triplets


def create_pmid_info_dict(tsv_file_path: str, json_file_path: str) -> dict:
    """
    Create a dictionary with PubMed ID as the key, and a dictionary containing text and MeSH information as the value.

    Args:
        tsv_file_path (str): The path to the TSV file.
        json_file_path (str): The path to the JSON file containing MeSH information.

    Returns:
        dict: A dictionary with PubMed IDs as keys and a dictionary containing text and MeSH information as values.
    """
    # Read the JSON file containing MeSH information
    with open(json_file_path, 'r') as json_file:
        mesh_info = json.load(json_file)

    # Read the TSV file and create the dictionary
    pmid_info_dict = {}
    with open(tsv_file_path, 'r') as tsv_file:
        reader = csv.reader(tsv_file, delimiter='\t')
        for row in reader:
            pmid, _, text = row  # Unpack the row, ignoring the second column (relationships)
            pmid_info_dict[pmid] = {
                'text': text,
                'mesh_info': mesh_info.get(pmid, {})  # Get MeSH info for the PMID if it exists
            }

    return pmid_info_dict

def combine_triplets_with_pmid_info(ranked_triplets: List[dict], pmid_info_dictionary: dict, output_json_path: str):
    """
    Combine ranked triplets with their corresponding text and MeSH information from pmid_info_dictionary.

    Args:
        ranked_triplets: A list of dictionaries, each representing a ranked triplet.
        pmid_info_dictionary: A dictionary with PubMed IDs as keys and a dictionary containing text and MeSH information as values.
        output_json_path: Path to the output JSON file.

    """
    combined_data = []
    for triplet, info in ranked_triplets:
        # Extract text and MeSH information for each PubMed ID in the ranked triplet
        pubmed_ids_mesh_info = {pmid: pmid_info_dictionary.get(pmid, {}) for pmid in info['pubmed_ids']}
        combined_data.append({'triplet': triplet, 'count': info['count'], 'pubmed_ids_mesh_info': pubmed_ids_mesh_info})

    # Save the combined data to a JSON file
    with open(output_json_path, 'w') as f:
        json.dump({'ranked_triplets': combined_data}, f, indent=4)


        
@click.command()
@click.option('-i', '--yaml_directory_path', required=True, help='Path to the directory containing YAML files')
@click.option('-s', '--mesh_info_file_path', required=True, help='Path to the file with selected PMID and MeSH info')
@click.option('-n', '--no_replaced_file_path', required=True, help='Path to no_replaced tsv file with raw text')
@click.option('-o', '--output_path', required=True, help='Path to the output JSON file')

def main(yaml_directory_path: str, mesh_info_file_path: str, output_path: str, no_replaced_file_path:str ):
    """
    Main function to process YAML files, extract triplets, count them, rank them, combine with MeSH info, and save to JSON.

    Args:
        yaml_directory_path (str): Path to the directory containing YAML files.
        mesh_info_file_path (str): Path to the file with selected PMID and MeSH info.
        output_path (str): Path to the output JSON file.
    """
    data = load_yaml_files(yaml_directory_path)
    triplets = extract_triplets(data)
    triplet_counts = count_triplets(triplets)
    ranked_triplets = rank_triplets(triplet_counts)

    pmid_info_dictionary = create_pmid_info_dict(no_replaced_file_path, mesh_info_file_path)

    combine_triplets_with_pmid_info(ranked_triplets, pmid_info_dictionary, output_path)



def run_in_notebook(yaml_directory_path, mesh_info_file_path, output_path, no_replaced_file_path):
    main.main(standalone_mode=False, args=[
        '--yaml_directory_path', yaml_directory_path,
        '--mesh_info_file_path', mesh_info_file_path,
        '--output_path', output_path,
        '--no_replaced_file_path', no_replaced_file_path,
    ])


if __name__ == '__main__':
    main()


"""
python triplet_ranking_and_mesh_combiner.py -i path/to/yaml/directory -s path/to/mesh/info/file -o path/to/output.json

python triplet_ranking_and_mesh_combiner.py -i ../../data/sickle_cell/ontoGPT_yaml/ -s ../../data/sickle_cell/selected_pmid_mesh_info.json  -o ../../data/sickle_cell/post_ontoGPT.json -n ../../data/sickle_cell/sickle_cell_no_replaced.tsv 
"""
