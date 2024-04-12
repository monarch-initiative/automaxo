import os
import yaml
import json
import pandas as pd
import csv
from collections import defaultdict
import click
from typing import List, Tuple, DefaultDict
from oaklib import get_adapter
from fuzzywuzzy import process

from tqdm import tqdm
tqdm.pandas()

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
            qualifier_label = named_entities_dict.get(qualifier, '')  # Extract the label for the qualifier

            triplets.append({
                'subject': {subject: subject_label},
                'predicate': predicate,
                'object': {object_: object_label},
                'qualifier': {qualifier: qualifier_label},  # Include the qualifier label
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
        subject_str = f"{list(triplet['subject'].keys())[0]}: {list(triplet['subject'].values())[0]}".lower()
        object_str = f"{list(triplet['object'].keys())[0]}: {list(triplet['object'].values())[0]}".lower()
        predicate = triplet['predicate'].lower()
        qualifier_str = f"{list(triplet['qualifier'].keys())[0]}: {list(triplet['qualifier'].values())[0]}".lower() if triplet['qualifier'] else ''
        subject_qualifier = triplet['subject_qualifier'].lower()
        object_qualifier = triplet['object_qualifier'].lower()
        subject_extension = triplet['subject_extension'].lower()
        object_extension = triplet['object_extension'].lower()
        pubmed_id = triplet['pubmed_id']

        key = (subject_str, predicate, object_str, qualifier_str, subject_qualifier, object_qualifier, subject_extension, object_extension)

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

def combine_triplets_with_pmid_info_and_create_df(ranked_triplets: List[dict], pmid_info_dictionary: dict, output_json_path: str):
    """
    Combine ranked triplets with their corresponding text and MeSH information from pmid_info_dictionary,
    create a DataFrame, and save the combined data as a JSON file.

    Args:
        ranked_triplets: A list of dictionaries, each representing a ranked triplet.
        pmid_info_dictionary: A dictionary with PubMed IDs as keys and a dictionary containing text and MeSH information as values.
        output_json_path: Path to the output JSON file.
    
    Returns:
        DataFrame: A DataFrame containing combined triplet and PubMed information.
    """
    combined_data = []
    for triplet, info in ranked_triplets:
        pubmed_ids_mesh_info = {pmid: pmid_info_dictionary.get(pmid, {}) for pmid in info['pubmed_ids']}
        combined_data.append({'triplet': triplet, 'count': info['count'], 'pubmed_ids_mesh_info': pubmed_ids_mesh_info})

    # Save the combined data to a JSON file
    with open(output_json_path, 'w') as f:
        json.dump({'ranked_triplets': combined_data}, f, indent=4)

    rows = []
    for entry in combined_data:
        triplet = entry['triplet']
        count = entry['count']
        if len(triplet) >= 3:
            subject_with_label, predicate, object_with_label = triplet[:3]
            qualifier = triplet[3] if len(triplet) > 3 else ''
            subject_qualifier = triplet[4] if len(triplet) > 4 else ''
            subject_extension = triplet[6] if len(triplet) > 6 else ''
            object_extension = triplet[7] if len(triplet) > 7 else ''

            subject, subject_label = subject_with_label.split(': ', 1) if ': ' in subject_with_label else (subject_with_label, '')
            object_, object_label = object_with_label.split(': ', 1) if ': ' in object_with_label else (object_with_label, '')
            qualifier, qualifier_label = qualifier.split(': ', 1) if ': ' in qualifier else (qualifier, '')

            for pubmed_id in entry['pubmed_ids_mesh_info'].keys():
                rows.append([
                    pubmed_id,
                    subject, subject_label, predicate, object_, object_label,
                    qualifier, qualifier_label, subject_qualifier, subject_extension, object_extension,
                    count
                ])

    return pd.DataFrame(rows, columns=[
        'Citation',
        'Subject', 'Subject Label', 'Predicate', 'Object', 'Object Label',
        'Qualifier', 'Qualifier Label', 'Subject Qualifier', 'Subject Extension', 'Object Extension',
        'Count'
    ])

def move_and_clean_columns(df, columns):
    """
    Moves non-grounded terms to separate columns and cleans original columns.

    Parameters:
    - df: DataFrame to modify.
    - columns: A list of tuples where each tuple contains the column to be cleaned
      and the corresponding label column.

    Returns:
    - DataFrame with updated columns.
    """
    for col, label_col in columns:
        non_grounded_col = f'Non grounded {col}'
        df[non_grounded_col] = df.apply(lambda row: row[col] if pd.isna(row[label_col]) or row[label_col] == '' else None, axis=1)
        df[col] = df.apply(lambda row: None if pd.isna(row[label_col]) or row[label_col] == '' else row[col], axis=1)
    return df

def annotate_text_with_ontology(df, adapter, ontology_prefix, text_column, new_column):
    """
    Annotates text in a DataFrame column with ontology information.
    
    Parameters:
    - df: DataFrame containing the text to be annotated.
    - adapter: Adapter object to use for annotation.
    - ontology_prefix: Prefix of the ontology IDs to filter annotations.
    - text_column: The name of the column containing text to be annotated.
    - new_column: The name of the column to store the annotation results.
    
    Returns:
    - DataFrame with a new column containing the annotation results.
    """
    def get_potential_annotations(text):
        annotation_results = []
        if isinstance(text, str):
            annotations = adapter.annotate_text(text)
            choices = [(annotation.object_id, annotation.object_label) for annotation in annotations if annotation.object_id.startswith(ontology_prefix)]
            choices_results = process.extract(text, [label for _, label in choices])
            combined_results = [(choices[i][0], label, score) for i, (label, score) in enumerate(choices_results)]
            sorted_results = sorted(combined_results, key=lambda x: x[2], reverse=True)
            top_two_choices = [(mondo_id, label) for mondo_id, label, _ in sorted_results[:2]]
            annotation_results.extend(top_two_choices)
        return annotation_results

    df[new_column] = df[text_column].progress_apply(get_potential_annotations)
    return df



def process_dataframe(initial_df):
    """
    Processes a DataFrame to clean and annotate data using specified ontologies.
    
    Parameters:
    - initial_df: The DataFrame to process.
    
    Returns:
    - A new, processed DataFrame.
    """
    columns_to_check = [('Subject', 'Subject Label'), ('Object', 'Object Label'), ('Qualifier', 'Qualifier Label')]
    annotated_df = move_and_clean_columns(initial_df.copy(), columns_to_check)

    # Annotate with different ontologies
    annotated_df = annotate_text_with_ontology(annotated_df, get_adapter("sqlite:obo:maxo"), "MAXO", 'Non grounded Subject', 'Potential MAXO')
    annotated_df = annotate_text_with_ontology(annotated_df, get_adapter("sqlite:obo:hp"), "HP", 'Non grounded Object', 'Potential HP')
    annotated_df = annotate_text_with_ontology(annotated_df, get_adapter("sqlite:obo:mondo"), "MONDO", 'Non grounded Qualifier', 'Potential MONDO')

    # Reorder columns
    annotated_df = annotated_df[['Citation', 'Subject', 'Subject Label', 'Non grounded Subject', 'Potential MAXO', 'Predicate', 'Object',
                     'Object Label', 'Non grounded Object', 'Potential HP', 'Qualifier', 'Qualifier Label', 'Non grounded Qualifier',
                     'Potential MONDO', 'Subject Qualifier', 'Subject Extension', 'Object Extension', 'Count']]
    
    return annotated_df


@click.command()
@click.option('-i', '--yaml_directory_path', required=True, help='Path to the directory containing YAML files')
@click.option('-s', '--mesh_info_file_path', required=True, help='Path to the file with selected PMID and MeSH info')
@click.option('-n', '--no_replaced_file_path', required=True, help='Path to no_replaced tsv file with raw text')
@click.option('-o', '--output_json_path', required=True, help='Path to the output JSON file')
@click.option('-t', '--output_tsv_path', required=True, help='Path to the output TSV file')

def main(yaml_directory_path: str, mesh_info_file_path: str, no_replaced_file_path: str, output_json_path: str, output_tsv_path: str):
    """
    Main function to process YAML files, extract triplets, count them, rank them, combine with MeSH info, and save to JSON and TSV.

    Args:
        yaml_directory_path (str): Path to the directory containing YAML files.
        mesh_info_file_path (str): Path to the file with selected PMID and MeSH info.
        no_replaced_file_path (str): Path to no_replaced tsv file with raw text.
        output_json_path (str): Path to the output JSON file.
        output_tsv_path (str): Path to the output TSV file.
    """
    data = load_yaml_files(yaml_directory_path)
    triplets = extract_triplets(data)
    triplet_counts = count_triplets(triplets)
    ranked_triplets = rank_triplets(triplet_counts)

    pmid_info_dictionary = create_pmid_info_dict(no_replaced_file_path, mesh_info_file_path)
    
    # Create the initial DataFrame and save the combined data as a JSON file
    initial_df = combine_triplets_with_pmid_info_and_create_df(ranked_triplets, pmid_info_dictionary, output_json_path)

    # Process the DataFrame
    annotated_df = process_dataframe(initial_df)

    # Save the annotated DataFrame to a TSV file
    annotated_df.to_csv(output_tsv_path, sep='\t', index=False)



def run_in_notebook(yaml_directory_path, mesh_info_file_path, no_replaced_file_path, output_json_path, output_tsv_path):
    main.main(standalone_mode=False, args=[
        '--yaml_directory_path', yaml_directory_path,
        '--mesh_info_file_path', mesh_info_file_path,
        '--no_replaced_file_path', no_replaced_file_path,
        '--output_json_path', output_json_path,
        '--output_tsv_path', output_tsv_path,
    ])

if __name__ == '__main__':
    main()


"""
python triplet_ranking_and_mesh_combiner.py -i path/to/yaml/directory -s path/to/mesh/info/file -o path/to/output.json
python triplet_ranking_and_mesh_combiner.py -i ../../data/melas/ontoGPT_yaml/ -s ../../data/melas/selected_pmid_mesh_info.json -n ../../data/melas/melas_no_replaced.tsv -o ../../data/melas/detailed_post_ontoGPT.json -t ../../data/melas/summary_post_ontoGPT.tsv 

python triplet_ranking_and_mesh_combiner.py -i ../../evaluation/evaluation_ontoGPT_yaml/ -s ../../evaluation/evaluation_selected_pmid_mesh_info.json -n ../../evaluation/evaluation_no_replaced.tsv -o ../../evaluation/results/evaluation_detailed_post_ontoGPT.json -t ../../evaluation/results/evaluation_summary_post_ontoGPT.tsv 

"""
