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
            # Ensure each component is a string and handle non-string types gracefully
            def clean_string(value):
                if isinstance(value, str):
                    return value.strip('<>').replace('None', '').replace('Not applicable', '')
                elif value is None:
                    return ''
                else:
                    return str(value).strip('<>').replace('None', '').replace('Not applicable', '')

            subject = clean_string(triplet.get('subject'))
            predicate = clean_string(triplet.get('predicate'))
            object_ = clean_string(triplet.get('object'))
            qualifier = clean_string(triplet.get('qualifier'))
            subject_qualifier = clean_string(triplet.get('subject_qualifier'))
            object_qualifier = clean_string(triplet.get('object_qualifier'))
            subject_extension = clean_string(triplet.get('subject_extension'))
            object_extension = clean_string(triplet.get('object_extension'))

            if not (subject and predicate and object_):
                continue  # Skip if any of subject, predicate, or object is missing

            subject_label = named_entities_dict.get(subject, '')
            object_label = named_entities_dict.get(object_, '')
            qualifier_label = named_entities_dict.get(qualifier, '')  # Extract the label for the qualifier

            triplets.append({
                'subject': {subject: subject_label},
                'predicate': predicate,
                'object': {object_: object_label},
                'qualifier': {qualifier: qualifier_label},
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


def create_pmid_mesh_info_dict(tsv_file_path: str, json_file_path: str) -> dict:
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
            pmid, text = row  # Unpack the row, ignoring the second column (relationships)
            pmid_info_dict[pmid] = {
                'text': text,
                'mesh_info': mesh_info.get(pmid, {})  # Get MeSH info for the PMID if it exists
            }

    return pmid_info_dict

def combine_triplets_with_mesh_pmid_info_and_create_df(ranked_triplets: List[dict], pmid_info_dictionary: dict):
    """
    Combine ranked triplets with their corresponding text and MeSH information from pmid_info_dictionary,
    create a DataFrame, and save the combined data as a JSON file.

    Args:
        ranked_triplets: A list of dictionaries, each representing a ranked triplet.
        pmid_info_dictionary: A dictionary with PubMed IDs as keys and a dictionary containing text and MeSH information as values.
    
    Returns:
        DataFrame: A DataFrame containing combined triplet and PubMed information.
    """
    combined_data = []
    for triplet, info in ranked_triplets:
        pubmed_ids_mesh_info = {pmid: pmid_info_dictionary.get(pmid, {}) for pmid in info['pubmed_ids']}
        combined_data.append({'triplet': triplet, 'count': info['count'], 'pubmed_ids_mesh_info': pubmed_ids_mesh_info})

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
      'citation',
        'maxo', 'maxo_label', 'relationship', 'hpo', 'hpo_label',
        'mondo', 'mondo_label', 'maxo_qualifier', 'chebi', 'hpo_extension',
        'count'
    ])


def separate_non_grounding_terms(df, columns):
    """
    Moves non-grounded terms to separate columns and cleans original columns by nullifying entries in the original
    columns if they are not grounded (i.e., corresponding label columns are NA or empty).

    Parameters:
    - df: DataFrame to modify.
    - columns: A list of tuples where each tuple contains the column to be cleaned
      and the corresponding label column.

    Returns:
    - DataFrame with updated columns where non-grounded terms are moved to new columns named as 'non_grounded_<column>'.
    """
    for col, label_col in columns:
        non_grounded_col = f'non_grounded_{col}'  # Ensure naming consistency with underscores
        # Identify non-grounded rows
        non_grounded_mask = df[label_col].isna() | (df[label_col] == '')
        
        # Move non-grounded terms to new column
        df[non_grounded_col] = df[col].where(non_grounded_mask)

        # Clear original column entries where non-grounded
        df[col] = df[col].where(~non_grounded_mask)
        
    return df
def get_potential_ontologies(df, adapter, ontology_prefix, text_column, new_column):
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
    if text_column not in df.columns:
        raise ValueError(f"Column {text_column} does not exist in DataFrame.")
    if new_column not in df.columns:
        df[new_column] = pd.NA  # Initialize column if not exist

    def get_potential_annotations(text):
        try:
            if isinstance(text, str):
                annotations = adapter.annotate_text(text)
                choices = [(annotation.object_id, annotation.object_label) for annotation in annotations if annotation.object_id.startswith(ontology_prefix)]
                if choices:
                    choices_results = process.extract(text, [label for _, label in choices], limit=2)
                    annotation_results = [(obj_id, label) for obj_id, label, _ in choices_results]
                    return annotation_results
        except Exception as e:
            print(f"Error processing text {text}: {e}")
        return []  # Return empty list in case of error or no data

    df[new_column] = df[text_column].progress_apply(get_potential_annotations)
    return df



def annotate_and_reformat_dataframe(initial_df):
    """
    Annotates and reformats a DataFrame by separating non-grounded terms, annotating with specified ontologies,
    and reordering columns.

    Parameters:
    - initial_df (pd.DataFrame): The DataFrame to process.

    Returns:
    - pd.DataFrame: A DataFrame that has been annotated and reformatted, ready for further analysis.
    """
    columns_to_check = [('maxo', 'maxo_label'), ('hpo', 'hpo_label'), ('mondo', 'mondo_label')]
    # Separate non-grounded terms
    annotated_df = separate_non_grounding_terms(initial_df.copy(), columns_to_check)

    # Annotate with different ontologies
    annotated_df = get_potential_ontologies(annotated_df, get_adapter("sqlite:obo:maxo"), "MAXO", 'non_grounded_maxo', 'potential_maxo')
    annotated_df = get_potential_ontologies(annotated_df, get_adapter("sqlite:obo:hp"), "HP", 'non_grounded_hpo', 'potential_hpo')
    annotated_df = get_potential_ontologies(annotated_df, get_adapter("sqlite:obo:mondo"), "MONDO", 'non_grounded_mondo', 'potential_mondo')

    # Reorder columns to ensure consistency and clarity
    processed_annotated_df = annotated_df[['citation', 'maxo', 'maxo_label', 'non_grounded_maxo', 'potential_maxo', 'relationship', 'hpo',
                     'hpo_label', 'non_grounded_hpo', 'potential_hpo', 'mondo', 'mondo_label', 'non_grounded_mondo',
                     'potential_mondo', 'maxo_qualifier', 'chebi', 'hpo_extension', 'count']]
    
    return processed_annotated_df


def aggregate_and_annotate_triplets(processed_annotated_df, pmid_info_dictionary):
    """
    Aggregates data from a DataFrame into triplet structures and enriches it with PubMed ID information from a provided dictionary.
    Each triplet includes details, count, and source information that links back to specific PubMed IDs and their associated metadata.

    Args:
        processed_annotated_df (pd.DataFrame): DataFrame containing annotated data with information structured into triplets.
        pmid_info_dictionary (dict): Dictionary where keys are PubMed IDs and values are detailed metadata about each PubMed ID.

    Returns:
        dict: A structured dictionary with a list of enriched triplets, each containing detailed annotations and source information.
    """
    # Define the keys that make up a triplet (excluding 'citation' and 'count')
    triplet_keys = ['maxo', 'maxo_label', 'non_grounded_maxo', 'potential_maxo', 'relationship', 'hpo',
                    'hpo_label', 'non_grounded_hpo', 'potential_hpo', 'mondo', 'mondo_label', 'non_grounded_mondo',
                    'potential_mondo', 'maxo_qualifier', 'chebi', 'hpo_extension']

    # Group by the triplet keys and aggregate the counts and list of PMIDs
    grouped = processed_annotated_df.groupby(triplet_keys).agg({
        'citation': list,  # List of PMIDs
        'count': 'sum'     # Sum of counts
    }).reset_index()

    # Convert the grouped DataFrame into the desired list format under the key "triplets"
    triplets_list = []
    for _, row in grouped.iterrows():
        pmid_list = row['citation']
        count = row['count']
        
        # Create the source information for each PMID
        pubmed_ids_mesh_info = {pmid: pmid_info_dictionary.get(pmid, {}) for pmid in pmid_list}
        source = {
            'pmid': pmid_list,
            'pubmed_ids_mesh_info': pubmed_ids_mesh_info
        }
        
        # Build the triplet dictionary
        triplet_info = {
            'triplet': {key: row[key] for key in triplet_keys},
            'count': count,
            'source': source
        }
        triplets_list.append(triplet_info)

    # Encapsulate the list in a dictionary under the key "triplets"
    triplet_aggregation_result = {'triplets': triplets_list}
    
    return triplet_aggregation_result

@click.command()
@click.option('-i', '--yaml_directory_path', required=True, help='Path to the directory containing YAML files')
@click.option('-s', '--mesh_info_file_path', required=True, help='Path to the file with selected PMID and MeSH info')
@click.option('-n', '--no_replaced_file_path', required=True, help='Path to no_replaced tsv file with raw text')
@click.option('-o', '--output_ymal_path', required=True, help='Path to the output YMAL file')

def main(yaml_directory_path: str, mesh_info_file_path: str, no_replaced_file_path: str, output_ymal_path: str):
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

    pmid_info_dictionary = create_pmid_mesh_info_dict(no_replaced_file_path, mesh_info_file_path)
    
    # Create the initial DataFrame and save the combined data as a JSON file
    pre_processed_df = combine_triplets_with_mesh_pmid_info_and_create_df(ranked_triplets, pmid_info_dictionary)

    # Process the pre_processed_df with further data cleaning and annotation
    processed_annotated_df = annotate_and_reformat_dataframe(pre_processed_df)

    # Aggregate and annotate the processed data into triplets
    triplet_aggregation_result = aggregate_and_annotate_triplets(processed_annotated_df, pmid_info_dictionary)

    with open(output_ymal_path, 'w') as file:
        yaml.dump(triplet_aggregation_result, file, allow_unicode=True, default_flow_style=False)





def run_in_notebook(yaml_directory_path, mesh_info_file_path, no_replaced_file_path, output_ymal_path):
    main.main(standalone_mode=False, args=[
        '--yaml_directory_path', yaml_directory_path,
        '--mesh_info_file_path', mesh_info_file_path,
        '--no_replaced_file_path', no_replaced_file_path,
        '--output_json_path', output_ymal_path
    ])

if __name__ == '__main__':
    main()


"""
python triplet_ranking_and_mesh_combiner.py -i path/to/yaml/directory -s path/to/mesh/info/file -o path/to/output.json

python triplet_ranking_and_mesh_combiner_1.0.py -i ../../data/donnai-barrow_syndrome/ontoGPT_yaml/ -s ../../data/donnai-barrow_syndrome/selected_pmid_mesh_info.json -n ../../data/donnai-barrow_syndrome/donnai-barrow_syndrome_no_replaced.tsv -o ../../data/donnai-barrow_syndrome/detailed_post_ontoGPT.json 

python triplet_ranking_and_mesh_combiner_1.0.py -i ../../data/donnai-barrow_syndrome/ontoGPT_yaml/ -s ../../data/donnai-barrow_syndrome/selected_pmid_mesh_info.json -n ../../data/donnai-barrow_syndrome/donnai-barrow_syndrome_no_replaced.tsv -o ../../data/donnai-barrow_syndrome/detailed_post_ontoGPT.yaml
"""