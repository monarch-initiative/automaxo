import csv
import json
import os
from collections import defaultdict
from typing import DefaultDict, List, Tuple

import click
import pandas as pd
import yaml
from fuzzywuzzy import process
from oaklib import get_adapter
from tqdm import tqdm

from automaxo.vector_search import ground_ontology_text

tqdm.pandas()


def load_yaml_files(directory_path: str) -> list:
    """
    Load YAML files from a specified directory and return their contents along with PubMed IDs.

    Args:
        directory_path (str): Path to the directory containing YAML files.

    Returns:
        list: A list of dictionaries, each containing the contents of a YAML file and its corresponding PubMed ID.
    """
    yaml_files = [f for f in os.listdir(directory_path) if f.endswith(".yaml")]
    data = []

    for file_name in tqdm(yaml_files, desc="Loading YAML files", total=len(yaml_files)):
        with open(os.path.join(directory_path, file_name), "r") as f:
            content = yaml.safe_load(f)
            if content:
                pubmed_id = os.path.splitext(file_name)[0]
                content["pubmed_id"] = pubmed_id
                data.append(content)

    return data


def extract_triplets(data: list) -> list:
    triplets = []
    named_entities = {}

    for article in data:
        pubmed_id = article["pubmed_id"]
        named_entities_dict = {
            ne["id"]: ne["label"] for ne in article.get("named_entities", [])
        }
        named_entities[pubmed_id] = named_entities_dict

        for triplet in article.get("extracted_object", {}).get(
            "action_annotation_relationships", []
        ):
            # Ensure each component is a string and handle non-string types gracefully
            def clean_string(value):
                if isinstance(value, str):
                    return (
                        value.strip("<>")
                        .replace("None", "")
                        .replace("Not applicable", "")
                    )
                elif value is None:
                    return ""
                else:
                    return (
                        str(value)
                        .strip("<>")
                        .replace("None", "")
                        .replace("Not applicable", "")
                    )

            subject = clean_string(triplet.get("subject"))
            predicate = clean_string(triplet.get("predicate"))
            object_ = clean_string(triplet.get("object"))
            qualifier = clean_string(triplet.get("qualifier"))
            subject_qualifier = clean_string(triplet.get("subject_qualifier"))
            object_qualifier = clean_string(triplet.get("object_qualifier"))
            subject_extension = clean_string(triplet.get("subject_extension"))
            object_extension = clean_string(triplet.get("object_extension"))

            if not (subject and predicate and object_):
                continue  # Skip if any of subject, predicate, or object is missing

            subject_label = named_entities_dict.get(subject, "")
            object_label = named_entities_dict.get(object_, "")
            qualifier_label = named_entities_dict.get(
                qualifier, ""
            )  # Extract the label for the qualifier

            triplets.append(
                {
                    "subject": {subject: subject_label},
                    "predicate": predicate,
                    "object": {object_: object_label},
                    "qualifier": {qualifier: qualifier_label},
                    "subject_qualifier": subject_qualifier,
                    "object_qualifier": object_qualifier,
                    "subject_extension": subject_extension,
                    "object_extension": object_extension,
                    "pubmed_id": pubmed_id,
                }
            )

    return triplets


def count_triplets(triplets: list) -> defaultdict:
    """
    Count the frequency of each triplet and track the PubMed IDs associated with each triplet.

    Args:
        triplets (list): A list of extracted triplets.

    Returns:
        defaultdict: A dictionary with triplets as keys and their count and associated PubMed IDs as values.
    """
    triplet_counts = defaultdict(lambda: {"count": 0, "pubmed_ids": set()})
    for triplet in triplets:
        subject_str = f"{list(triplet['subject'].keys())[0]}: {list(triplet['subject'].values())[0]}".lower()
        object_str = f"{list(triplet['object'].keys())[0]}: {list(triplet['object'].values())[0]}".lower()
        predicate = triplet["predicate"].lower()
        qualifier_str = (
            f"{list(triplet['qualifier'].keys())[0]}: {list(triplet['qualifier'].values())[0]}".lower()
            if triplet["qualifier"]
            else ""
        )
        subject_qualifier = triplet["subject_qualifier"].lower()
        object_qualifier = triplet["object_qualifier"].lower()
        subject_extension = triplet["subject_extension"].lower()
        object_extension = triplet["object_extension"].lower()
        pubmed_id = triplet["pubmed_id"]

        key = (
            subject_str,
            predicate,
            object_str,
            qualifier_str,
            subject_qualifier,
            object_qualifier,
            subject_extension,
            object_extension,
        )

        triplet_counts[key]["count"] += 1
        triplet_counts[key]["pubmed_ids"].add(pubmed_id)

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
    ranked_triplets = sorted(
        triplet_counts.items(), key=lambda x: x[1]["count"], reverse=True
    )
    return ranked_triplets


def create_pmid_mesh_info_dict(tsv_file_path: str, json_file_path: str) -> dict:
    """
    Create a dictionary with PubMed ID as the key, and a dictionary containing title, abstract,
    and MeSH information as the value.

    Args:
        tsv_file_path (str): The path to the TSV file, which is expected to contain columns for PMID, Title, and Abstract.
        json_file_path (str): The path to the JSON file containing MeSH information.

    Returns:
        dict: A dictionary with PubMed IDs as keys and dictionaries containing title, abstract,
              and MeSH information as values.
    """
    # Read the JSON file containing MeSH information
    with open(json_file_path, "r") as json_file:
        mesh_info = json.load(json_file)

    # Read the TSV file and create the dictionary
    pmid_info_dict = {}
    with open(tsv_file_path, "r") as tsv_file:
        reader = csv.reader(tsv_file, delimiter="\t")
        next(reader)  # Skip the header row
        for row in reader:
            if len(row) < 3:
                continue  # Skip rows that do not have enough columns
            pmid, title, abstract = row
            pmid_info_dict[pmid] = {
                "title": title,
                "abstract": abstract,
                "mesh_info": mesh_info.get(
                    pmid, {}
                ),  # Get MeSH info for the PMID if it exists
            }

    return pmid_info_dict


def combine_triplets_with_mesh_pmid_info_and_create_df(
    ranked_triplets: List[dict], pmid_info_dictionary: dict
):
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
        pubmed_ids_mesh_info = {
            pmid: pmid_info_dictionary.get(pmid, {}) for pmid in info["pubmed_ids"]
        }
        combined_data.append(
            {
                "triplet": triplet,
                "count": info["count"],
                "pubmed_ids_mesh_info": pubmed_ids_mesh_info,
            }
        )

    rows = []
    for entry in combined_data:
        triplet = entry["triplet"]
        count = entry["count"]
        if len(triplet) >= 3:
            subject_with_label, predicate, object_with_label = triplet[:3]
            qualifier = triplet[3] if len(triplet) > 3 else ""
            subject_qualifier = triplet[4] if len(triplet) > 4 else ""
            subject_extension = triplet[6] if len(triplet) > 6 else ""
            object_extension = triplet[7] if len(triplet) > 7 else ""

            subject, subject_label = (
                subject_with_label.split(": ", 1)
                if ": " in subject_with_label
                else (subject_with_label, "")
            )
            object_, object_label = (
                object_with_label.split(": ", 1)
                if ": " in object_with_label
                else (object_with_label, "")
            )
            qualifier, qualifier_label = (
                qualifier.split(": ", 1) if ": " in qualifier else (qualifier, "")
            )

            for pubmed_id in entry["pubmed_ids_mesh_info"].keys():
                rows.append(
                    [
                        pubmed_id,
                        subject,
                        subject_label,
                        predicate,
                        object_,
                        object_label,
                        qualifier,
                        qualifier_label,
                        subject_qualifier,
                        subject_extension,
                        object_extension,
                        count,
                    ]
                )

    return pd.DataFrame(
        rows,
        columns=[
            "citation",
            "maxo",
            "maxo_label",
            "relationship",
            "hpo",
            "hpo_label",
            "mondo",
            "mondo_label",
            "maxo_qualifier",
            "chebi",
            "hpo_extension",
            "count",
        ],
    )


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
        non_grounded_col = (
            f"non_grounded_{col}"  # Ensure naming consistency with underscores
        )
        # Identify non-grounded rows
        non_grounded_mask = df[label_col].isna() | (df[label_col] == "")

        # Move non-grounded terms to new column
        df[non_grounded_col] = df[col].where(non_grounded_mask)

        # Clear original column entries where non-grounded
        df[col] = df[col].where(~non_grounded_mask)

    return df


def get_potential_ontologies(df, adapter, ontology_prefix, text_column, new_column):
    """
    Annotates text in a DataFrame column with ontology information. This function uses an adapter
    to fetch annotations for text, then filters these annotations based on a specified prefix.

    Parameters:
    - df (DataFrame): The DataFrame containing the text to be annotated.
    - adapter: The adapter object used for fetching annotations. This should be pre-configured to
               communicate with a specific ontology database.
    - ontology_prefix (str): The prefix of the ontology IDs to include in the results. This prefix
                             helps filter relevant annotations from the adapter's output.
    - text_column (str): The name of the DataFrame column that contains the text to annotate.
    - new_column (str): The name of the new column where the annotation results will be stored.

    Raises:
    - ValueError: If the specified text_column does not exist in the DataFrame.

    Returns:
    - DataFrame: The original DataFrame augmented with a new column containing lists of tuples. Each tuple
                 contains an ontology ID and the corresponding label from the annotations that match the prefix.
    """

    # Check if the text column exists in the DataFrame; raise an error if it does not.
    if text_column not in df.columns:
        raise ValueError(f"Column {text_column} does not exist in DataFrame.")

    # Initialize the new column with missing values if it does not already exist in the DataFrame.
    if new_column not in df.columns:
        df[new_column] = pd.NA

    # Internal function to get annotations for a single piece of text.
    def get_potential_annotations(text):
        try:
            annotation_results = []
            # Process only if text is a string; skip otherwise.
            if isinstance(text, str):
                # Fetch all annotations for the text using the adapter.
                annotations = adapter.annotate_text(text)
                # Filter the annotations to include only those that start with the specified prefix.
                filtered_annotations = [
                    (annotation.object_id, annotation.object_label)
                    for annotation in annotations
                    if annotation.object_id.startswith(ontology_prefix)
                ]

                # Use fuzzy matching to get potential matches for the text.
                # choices_results = process.extract(
                #     text, [label for _, label in filtered_annotations]
                # )
                choices_results = ground_ontology_text(
                    annotator=adapter,
                    input_text=text,
                    verbose=True,
                    include_list=[ontology_prefix + ":"],
                    use_ontogpt_grounding=True,
                    curategpt_path="../../stagedb/",  # Needs adjustment
                    curategpt_collection="ont_maxo",  # Change based on ontology_prefix
                    curategpt_database_type="chromadb",
                )
                # Combine the results with their corresponding IDs.
                combined_results = [
                    (filtered_annotations[i][0], label, score)
                    for i, (label, score) in enumerate(choices_results)
                ]
                # Sort the combined results by their fuzzy matching score in descending order.
                sorted_results = sorted(
                    combined_results, key=lambda x: x[2], reverse=True
                )
                # Select the top two choices.
                top_two_choices = [
                    (identifier, label) for identifier, label, _ in sorted_results[:2]
                ]
                annotation_results.extend(top_two_choices)
            return annotation_results
        except Exception as e:
            # Print an error message if there's an issue during the annotation process.
            print(f"Error processing text {text}: {e}")
            # Return an empty list if an error occurs.
            return []

    # Apply the internal function to each entry in the specified text column.
    df[new_column] = df[text_column].apply(get_potential_annotations)

    # Return the DataFrame with the new column added.
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
    columns_to_check = [
        ("maxo", "maxo_label"),
        ("hpo", "hpo_label"),
        ("mondo", "mondo_label"),
    ]
    # Separate non-grounded terms
    annotated_df = separate_non_grounding_terms(initial_df.copy(), columns_to_check)

    # Annotate with different ontologies
    annotated_df = get_potential_ontologies(
        annotated_df,
        get_adapter("sqlite:obo:maxo"),
        "MAXO",
        "non_grounded_maxo",
        "potential_maxo",
    )
    annotated_df = get_potential_ontologies(
        annotated_df,
        get_adapter("sqlite:obo:hp"),
        "HP",
        "non_grounded_hpo",
        "potential_hpo",
    )
    annotated_df = get_potential_ontologies(
        annotated_df,
        get_adapter("sqlite:obo:mondo"),
        "MONDO",
        "non_grounded_mondo",
        "potential_mondo",
    )

    # Reorder columns to ensure consistency and clarity
    processed_annotated_df = annotated_df[
        [
            "citation",
            "maxo",
            "maxo_label",
            "non_grounded_maxo",
            "potential_maxo",
            "relationship",
            "hpo",
            "hpo_label",
            "non_grounded_hpo",
            "potential_hpo",
            "mondo",
            "mondo_label",
            "non_grounded_mondo",
            "potential_mondo",
            "maxo_qualifier",
            "chebi",
            "hpo_extension",
            "count",
        ]
    ]

    return processed_annotated_df


def transform_and_sort_triplets(triplets_list):
    """Convert potential entries in triplets to a list of dictionaries where needed."""
    new_list = []
    for triplet_dict in triplets_list:
        new_triplet_dict = {
            "triplet": {},
            "count": triplet_dict["count"],
            "source": triplet_dict["source"],
        }
        triplet = triplet_dict["triplet"]
        for key, value in triplet.items():
            if isinstance(value, (tuple, list)) and "potential" in key:
                new_triplet_dict["triplet"][key] = [
                    {"id": item[0], "label": item[1]} for item in value
                ]
            else:
                new_triplet_dict["triplet"][key] = value
        new_list.append(new_triplet_dict)

    triplets_list = new_list

    return triplets_list


def aggregate_and_annotate_triplets(processed_annotated_df, pmid_info_dictionary):
    """
    Aggregates and enriches data from a DataFrame using PubMed IDs to link with external metadata.

    Args:
        processed_annotated_df (pd.DataFrame): A DataFrame with various biomedical annotations, including PubMed IDs.
        pmid_info_dictionary (dict): Dictionary with PubMed IDs as keys and dictionaries as values,
            each containing title, abstract, and MeSH information.

    Returns:
        dict: Contains a sorted list of 'triplets', each a dictionary with aggregated data,
              maximum occurrence counts, and enriched metadata from pmid_info_dictionary.
              Each 'source' in the triplet is formatted with title, abstract, and MeSH information
              for the associated PubMed ID.

    Processes:
        - Converts 'citation' IDs to strings for dictionary matching.
        - Fills NaN values in crucial columns for grouping.
        - Converts lists to tuples in necessary columns for grouping.
        - Aggregates data by specified columns, computing unique citations and max counts.
        - Annotates each group with metadata from the pmid_info_dictionary.
        - Sorts triplets by 'count' in descending order.
    """
    # Convert the 'citation' column to string
    processed_annotated_df["citation"] = processed_annotated_df["citation"].astype(str)

    # Fill NaN values for columns crucial for grouping
    grouping_columns = [
        "maxo",
        "maxo_label",
        "non_grounded_maxo",
        "potential_maxo",
        "relationship",
        "hpo",
        "hpo_label",
        "non_grounded_hpo",
        "potential_hpo",
        "mondo",
        "mondo_label",
        "non_grounded_mondo",
        "potential_mondo",
        "maxo_qualifier",
        "chebi",
        "hpo_extension",
    ]

    processed_annotated_df[grouping_columns] = processed_annotated_df[
        grouping_columns
    ].fillna("None")

    # Convert lists to tuples in necessary columns for grouping
    for col in grouping_columns:
        if (
            processed_annotated_df[col].dtype == object
            and processed_annotated_df[col].apply(lambda x: isinstance(x, list)).any()
        ):
            processed_annotated_df[col] = processed_annotated_df[col].apply(
                lambda x: tuple(x) if isinstance(x, list) else x
            )

    # Group by the defined grouping columns
    grouped = (
        processed_annotated_df.groupby(grouping_columns)
        .agg(
            {
                "citation": lambda x: list(set(x)),  # List all unique PMIDs
                "count": "max",  # Take the maximum count from the grouped rows
            }
        )
        .reset_index()
    )

    # Build the resulting triplets list
    triplets_list = []
    for _, row in grouped.iterrows():
        pmid_list = row["citation"]
        count = row["count"]

        # Annotate each PMID with corresponding dictionary data if available
        pubmed_ids_mesh_info = {
            pmid: pmid_info_dictionary.get(pmid, {}) for pmid in pmid_list
        }

        # Constructing the source as specified
        source = {}
        for pmid, info in pubmed_ids_mesh_info.items():
            source[pmid] = {
                "title": info.get("title", "No title available"),
                "abstract": info.get("abstract", "No abstract available"),
                "mesh_info": info.get("mesh_info", {}),
            }

        # Collect triplet details and transform potential entries
        triplet_info = {
            "triplet": {key: row[key] for key in grouping_columns},
            "count": count,
            "source": source,
        }

        triplets_list.append(triplet_info)

    transform_triplets_list = transform_and_sort_triplets(triplets_list)
    triplets_list = transform_triplets_list
    # Sort the triplets list by 'count' in descending order
    triplets_list.sort(key=lambda x: x["count"], reverse=True)

    return {"triplets": triplets_list}


@click.command()
@click.option(
    "-i",
    "--yaml_directory_path",
    required=True,
    help="Path to the directory containing YAML files",
)
@click.option(
    "-s",
    "--mesh_info_file_path",
    required=True,
    help="Path to the file with selected PMID and MeSH info",
)
@click.option(
    "-n",
    "--no_replaced_file_path",
    required=True,
    help="Path to no_replaced tsv file with raw text",
)
@click.option(
    "-o", "--output_json_path", required=True, help="Path to the output JSON file"
)
def main(
    yaml_directory_path: str,
    mesh_info_file_path: str,
    no_replaced_file_path: str,
    output_json_path: str,
):
    """
    Main function to process YAML files, extract triplets, count them, rank them, combine with MeSH info, and save to JSON and TSV.

    Args:
        yaml_directory_path (str): Path to the directory containing YAML files.
        mesh_info_file_path (str): Path to the file with selected PMID and MeSH info.
        no_replaced_file_path (str): Path to no_replaced tsv file with raw text.
        output_json_path (str): Path to the output JSON file.
    """
    data = load_yaml_files(yaml_directory_path)
    triplets = extract_triplets(data)
    triplet_counts = count_triplets(triplets)
    ranked_triplets = rank_triplets(triplet_counts)

    pmid_info_dictionary = create_pmid_mesh_info_dict(
        no_replaced_file_path, mesh_info_file_path
    )

    # Create the initial DataFrame and save the combined data as a JSON file
    pre_processed_df = combine_triplets_with_mesh_pmid_info_and_create_df(
        ranked_triplets, pmid_info_dictionary
    )

    # Process the pre_processed_df with further data cleaning and annotation
    processed_annotated_df = annotate_and_reformat_dataframe(pre_processed_df)

    # Aggregate and annotate the processed data into triplets
    triplet_aggregation_results = aggregate_and_annotate_triplets(
        processed_annotated_df, pmid_info_dictionary
    )

    # Write the triplet_aggregation_result dictionary to a file in JSON format
    with open(output_json_path, "w") as f:
        json.dump(triplet_aggregation_results, f, indent=4)


def run_in_notebook(
    yaml_directory_path, mesh_info_file_path, no_replaced_file_path, output_json_path
):
    main.main(
        standalone_mode=False,
        args=[
            "--yaml_directory_path",
            yaml_directory_path,
            "--mesh_info_file_path",
            mesh_info_file_path,
            "--no_replaced_file_path",
            no_replaced_file_path,
            "--output_json_path",
            output_json_path,
        ],
    )


if __name__ == "__main__":
    main()


"""
python triplet_ranking_and_mesh_combiner.py -i path/to/yaml/directory -s path/to/mesh/info/file -o path/to/output.json

python triplet_ranking_and_mesh_combiner.py -i ../../data/sickle_cell/ontoGPT_yaml/ -s ../../data/sickle_cell/selected_pmid_mesh_info.json -n ../../data/sickle_cell/sickle_cell_no_replaced.tsv -o ../../data/sickle_cell/detailed_post_ontoGPT.json

"""
