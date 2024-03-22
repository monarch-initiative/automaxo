import os
import yaml
import json
from collections import defaultdict
import click
from typing import List, Tuple, DefaultDict
from tqdm import tqdm
from pymongo import MongoClient


def load_yaml_data_from_collection(db_name: str, collection_name: str) -> list:
    """
    Load YAML data from a specified MongoDB collection and return their contents along with PubMed IDs.
    
    Args:
        db_name (str): Name of the MongoDB database.
        collection_name (str): Name of the MongoDB collection containing YAML data.
    
    Returns:
        list: A list of dictionaries, each containing the contents of a YAML entry and its corresponding PubMed ID.
    """
    client = MongoClient('mongodb://localhost:27017/')
    db = client[db_name]
    collection = db[collection_name]

    data = []
    for document in tqdm(collection.find(), desc="Loading YAML data from collection", total=collection.count_documents({})):
        yaml_content = yaml.safe_load(document["results"])  # Assuming the YAML content is stored as a string in the "results" field
        yaml_content['pubmed_id'] = document["pubmed_id"]
        data.append(yaml_content)

    client.close()
    return data

def load_mesh_info_from_collection(db_name: str, collection_name: str) -> dict:
    """
    Load mesh info from a specified MongoDB collection.

    Args:
        db_name (str): Name of the MongoDB database.
        collection_name (str): Name of the MongoDB collection.

    Returns:
        dict: A dictionary where keys are PubMed IDs and values are dictionaries of mesh info.
    """
    client = MongoClient('mongodb://localhost:27017/')
    db = client[db_name]
    collection = db[collection_name]

    mesh_info = {}
    for document in tqdm(collection.find(), desc="Loading mesh info from collection"):
        pubmed_id = document["_id"]
        mesh_info[pubmed_id] = document["mesh_info"]

    client.close()
    return mesh_info


def extract_triplets(data: list) -> tuple:
    triplets = []
    named_entities = {}

    for article in tqdm(data, desc="Extracting triplets", total=len(data)):
        pubmed_id = article['pubmed_id']
        named_entities_dict = {ne['id']: ne['label'] for ne in article.get('named_entities', [])}
        named_entities[pubmed_id] = named_entities_dict

        for section in ['action_to_disease', 'action_to_symptom']:
            for triplet in article.get('extracted_object', {}).get(section, []):
                if 'object' in triplet:
                    for obj in triplet['object']:
                        subject_label = named_entities_dict.get(triplet['subject'], '')
                        object_label = named_entities_dict.get(obj, '')
                        triplets.append(({triplet['subject']: subject_label}, triplet['predicate'], {obj: object_label}, pubmed_id))
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
    for subject, predicate, obj, pubmed_id in triplets:
        subject_str = f"{list(subject.keys())[0]}: {list(subject.values())[0]}"
        object_str = f"{list(obj.keys())[0]}: {list(obj.values())[0]}"
        triplet_counts[(subject_str, predicate, object_str)]['count'] += 1
        triplet_counts[(subject_str, predicate, object_str)]['pubmed_ids'].add(pubmed_id)

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
@click.option('-b','--db_name', required=True, help="Name of the MongoDB database.")
@click.option('-i','--input_collection_name', required=True, help="Name of the MongoDB collection for input.")
@click.option('-c','--info_collection_name', required=True, help="Name of the MongoDB collection for mesh info.")
@click.option('-o','--output_path', required=True, help='Path to the output JSON file')

def main(db_name, input_collection_name, info_collection_name, output_path):
    data = load_yaml_data_from_collection(db_name, input_collection_name)
    triplets = extract_triplets(data)
    triplet_counts = count_triplets(triplets)
    ranked_triplets = rank_triplets(triplet_counts)

    mesh_info = load_mesh_info_from_collection(db_name, info_collection_name)
    combined_data = combine_triplets_with_mesh(ranked_triplets, mesh_info)

    with open(output_path, 'w') as f:
        json.dump({'ranked_triplets': combined_data}, f, indent=4)

def run_in_notebook(db_name, input_collection_name, info_collection_name, output_path):
    main.main(standalone_mode=False, args=[
        '--db_name', db_name,
        '--input_collection_name', input_collection_name,
        '--info_collection_name', info_collection_name,
        '--output_path', output_path
    ])

if __name__ == '__main__':
    main()


"""
python triplet_ranking_and_mesh_combiner.py -i path/to/yaml/directory -s path/to/mesh/info/file -o path/to/output.json

"""
