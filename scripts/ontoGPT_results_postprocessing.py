import os
import yaml
import json
from collections import defaultdict
import argparse

def load_yaml_files(directory_path: str):
    """
    Load YAML files from a specified directory.

    Args:
        directory_path (str): The path to the directory containing YAML files.

    Returns:
        list: A list of dictionaries, each representing the content of a YAML file,
              with the PubMed ID added as a key.

    """
    data = []
    for file_name in os.listdir(directory_path):
        if file_name.endswith('.yaml'):
            pubmed_id = os.path.splitext(file_name)[0]
            file_path = os.path.join(directory_path, file_name)
            with open(file_path, 'r') as f:
                content = yaml.safe_load(f)
                if content is not None:  # Check if content is not None
                    content['pubmed_id'] = pubmed_id  # Add PubMed ID to the article data
                    data.append(content)
    return data


def extract_triplets(data: list):
    """
    Extract triplets from the loaded YAML data.

    Args:
        data (list): A list of dictionaries, each representing the content of a YAML file.

    Returns:
        tuple: A tuple containing two elements:
               - A list of tuples, each representing a triplet (subject, predicate, object, object_qualifier, PubMed ID).
               - A dictionary mapping PubMed IDs to their corresponding named entities.

    """
    triplets = []
    named_entities = {}

    def add_triplets(section, pubmed_id):
        for triplet in article.get('extracted_object', {}).get(section, []):
            if 'object' in triplet:  # Check if 'object' key exists in the triplet
                for obj in triplet['object']:
                    triplets.append((triplet['subject'], triplet['predicate'], obj, triplet.get('object_qualifier'), pubmed_id))

    for article in data:
        pubmed_id = article['pubmed_id']
        add_triplets('action_to_disease', pubmed_id)
        add_triplets('action_to_symptom', pubmed_id)
        named_entities[pubmed_id] = article['named_entities']

    return triplets, named_entities


def count_triplets(triplets: list):
    """
    Count the frequency of each triplet and track the PubMed IDs associated with each triplet.

    Args:
        triplets (list): A list of tuples, each representing a triplet (subject, predicate, object, object_qualifier, PubMed ID).

    Returns:
        defaultdict: A dictionary where each key is a triplet (excluding the PubMed ID) and each value is a dictionary
                     containing the count of the triplet and a set of PubMed IDs associated with the triplet.

    """
    triplet_counts = defaultdict(lambda: {'count': 0, 'pubmed_ids': set()})
    for triplet in triplets:
        key = triplet[:-1]  # Exclude the PubMed ID from the key
        pubmed_id = triplet[-1]
        triplet_counts[key]['count'] += 1
        triplet_counts[key]['pubmed_ids'].add(pubmed_id)
    return triplet_counts

def rank_triplets(triplet_counts: defaultdict):
    """
    Rank triplets based on their frequency.

    Args:
        triplet_counts (defaultdict): A dictionary where each key is a triplet (excluding the PubMed ID) and each value
                                      is a dictionary containing the count of the triplet and a set of PubMed IDs associated with the triplet.

    Returns:
        list: A list of tuples, each representing a triplet and its associated count and PubMed IDs, sorted by count in descending order.

    """
    ranked_triplets = sorted(triplet_counts.items(), key=lambda x: x[1]['count'], reverse=True)
    return ranked_triplets

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process YAML files and output results in JSON format.')
    parser.add_argument('directory_path', help='Path to the directory containing YAML files')
    parser.add_argument('json_output_path', help='Path to the output JSON file')
    args = parser.parse_args()

    data = load_yaml_files(args.directory_path)
    triplets, named_entities = extract_triplets(data)
    triplet_counts = count_triplets(triplets)
    ranked_triplets = rank_triplets(triplet_counts)

    # Save results to JSON file
    results = {
        'ranked_triplets': [{'triplet': triplet, 'count': info['count'], 'pubmed_ids': list(info['pubmed_ids'])} for triplet, info in ranked_triplets],
        'named_entities': named_entities
    }
    with open(args.json_output_path, 'w') as f:
        json.dump(results, f, indent=4)


"""

python ontoGPT_results_postprocessing.py ../test_case/test_ontogpt_result_non_replaced output.json

python ontoGPT_results_postprocessing.py .../dump/ontoGPT_yaml_files/ontoGPT_cystic_fibrosis  ../data/post_ontoGPT_cystic_fibrosis.json


"""