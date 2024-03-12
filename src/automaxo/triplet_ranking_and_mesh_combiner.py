import os
import yaml
import json
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

def extract_triplets(data: list) -> tuple:
    """
    Extract triplets and named entities from the loaded YAML data.
    
    Args:
        data (list): A list of dictionaries, each containing the contents of a YAML file and its corresponding PubMed ID.
    
    Returns:
        tuple: A tuple containing a list of extracted triplets and a dictionary of named entities.
    """
    triplets = []
    named_entities = {}

    for article in tqdm(data, desc="Extracting triplets", total=len(data)):
        pubmed_id = article['pubmed_id']
        named_entities[pubmed_id] = article.get('named_entities', {})

        for section in ['action_to_disease', 'action_to_symptom']:
            for triplet in article.get('extracted_object', {}).get(section, []):
                if 'object' in triplet:
                    for obj in triplet['object']:
                        triplets.append((triplet['subject'], triplet['predicate'], obj, pubmed_id))

    return triplets, named_entities

def count_triplets(triplets: list) -> defaultdict:
    """
    Count the frequency of each triplet and track the PubMed IDs associated with each triplet.
    
    Args:
        triplets (list): A list of extracted triplets.
    
    Returns:
        defaultdict: A dictionary with triplets as keys and their count and associated PubMed IDs as values.
    """
    triplet_counts = defaultdict(lambda: {'count': 0, 'pubmed_ids': set()})
    for subject, predicate, obj, pubmed_id in triplets:
        triplet_counts[(subject, predicate, obj)]['count'] += 1
        triplet_counts[(subject, predicate, obj)]['pubmed_ids'].add(pubmed_id)
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

def combine_triplets_with_mesh(ranked_triplets: List[Tuple], mesh_info: dict) -> list:
    """
    Combine ranked triplets with their corresponding MeSH information.

    Args:
        ranked_triplets: A list of tuples, each representing a ranked triplet.
        mesh_info: A dictionary with PubMed IDs as keys and their associated MeSH information as values.

    Returns:
        A list of dictionaries, each containing a ranked triplet and its associated MeSH information.
    """
    combined_data = []
    for triplet, info in ranked_triplets:
        mesh_data = {pmid: mesh_info.get(pmid, {}) for pmid in info['pubmed_ids']}
        combined_data.append({'triplet': triplet, 'count': info['count'], 'pubmed_ids': mesh_data})
    return combined_data


@click.command()
@click.option('-i', '--yaml_directory_path', required=True, help='Path to the directory containing YAML files')
@click.option('-s', '--mesh_info_file_path', required=True, help='Path to the file with selected PMID and MeSH info')
@click.option('-o', '--output_path', required=True, help='Path to the output JSON file')
def main(yaml_directory_path: str, mesh_info_file_path: str, output_path: str):
    """
    Main function to process YAML files, extract triplets, count them, rank them, combine with MeSH info, and save to JSON.

    Args:
        yaml_directory_path (str): Path to the directory containing YAML files.
        mesh_info_file_path (str): Path to the file with selected PMID and MeSH info.
        output_path (str): Path to the output JSON file.
    """
    data = load_yaml_files(yaml_directory_path)
    triplets, _ = extract_triplets(data)
    triplet_counts = count_triplets(triplets)
    ranked_triplets = rank_triplets(triplet_counts)

    with open(mesh_info_file_path, 'r') as f:
        mesh_info = json.load(f)

    combined_data = combine_triplets_with_mesh(ranked_triplets, mesh_info)

    with open(output_path, 'w') as f:
        json.dump({'ranked_triplets': combined_data}, f, indent=4)

def run_in_notebook(yaml_directory_path, mesh_info_file_path, output_path):
    main.main(standalone_mode=False, args=[
        '--yaml_directory_path', yaml_directory_path,
        '--mesh_info_file_path', mesh_info_file_path,
        '--output_path', output_path
    ])


if __name__ == '__main__':
    main()


"""
python triplet_ranking_and_mesh_combiner.py -i path/to/yaml/directory -s path/to/mesh/info/file -o path/to/output.json

"""
