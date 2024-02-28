import os
import yaml
import json
from collections import defaultdict
import argparse

def load_yaml_files(directory_path):
    data = []
    for file_name in os.listdir(directory_path):
        if file_name.endswith('.yaml'):
            pubmed_id = os.path.splitext(file_name)[0]
            file_path = os.path.join(directory_path, file_name)
            with open(file_path, 'r') as f:
                content = yaml.safe_load(f)
                content['pubmed_id'] = pubmed_id  # Add PubMed ID to the article data
                data.append(content)
    return data

def extract_triplets(data):
    triplets = []
    named_entities = {}

    def add_triplets(section, pubmed_id):
        for triplet in article.get('extracted_object', {}).get(section, []):
            for obj in triplet['object']:
                triplets.append((triplet['subject'], triplet['predicate'], obj, triplet.get('object_qualifier'), pubmed_id))

    for article in data:
        pubmed_id = article['pubmed_id']
        add_triplets('action_to_disease', pubmed_id)
        add_triplets('action_to_symptom', pubmed_id)
        named_entities[pubmed_id] = article['named_entities']

    return triplets, named_entities

def count_triplets(triplets):
    triplet_counts = defaultdict(lambda: {'count': 0, 'pubmed_ids': set()})
    for triplet in triplets:
        key = triplet[:-1]  # Exclude the PubMed ID from the key
        pubmed_id = triplet[-1]
        triplet_counts[key]['count'] += 1
        triplet_counts[key]['pubmed_ids'].add(pubmed_id)
    return triplet_counts

def rank_triplets(triplet_counts):
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

"""