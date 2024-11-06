"""Functions for performing vector search with ontology terms."""

# Uses curategpt
# Original script c/o Justin Reese
# https://github.com/monarch-initiative/malco/blob/short_letter/notebooks/process_gpt_o1_PREVIEW_and_plot.ipynb

import logging
import re
from typing import List, Tuple

from curategpt.store import get_store
from oaklib import get_adapter
import os
from oaklib.interfaces.text_annotator_interface import (
    TextAnnotationConfiguration,
    TextAnnotatorInterface,
)

# # Read in OpenAI key file (for curategpt grounding)
# key_file_path = os.path.expanduser("~/openai.key")
# # Read the key from the file and set the environment variable
# with open(key_file_path, "r") as key_file:
#     openai_api_key = key_file.read().strip()
# os.environ["OPENAI_API_KEY"] = openai_api_key

from typing import List, Tuple

def perform_curategpt_grounding(
    input_text: str,
    ontology_prefix: List[str] ,  # example: ['MONDO']
    path: str,
    collection: str,
    database_type: str,
    limit: int = 1,
    relevance_factor: float = 1000000.0,
    verbose: bool = False
) -> List[Tuple[str, str]]:
    """
    Use curategpt to perform grounding for a given text when initial attempts fail.

    Parameters:
    - input_text: The text to ground.
    - path: The path to the database. You'll need to create an index of the target ontology using curategpt in this db.
    - collection: The collection to search within curategpt. Name of target ontology collection in the db.
    - database_type: The type of database used for grounding (e.g., chromadb, duckdb).
    - limit: The number of search results to return.
    - relevance_factor: The distance threshold for relevance filtering.
    - ontology_prefix: List of exact prefixes to include in results (e.g., ['MONDO']).
    - verbose: Whether to print verbose output for debugging.

    Returns:
    - List of tuples: [(CURIE, Label), ...] if prefix matches exactly, else []
    """
    # Initialize the database store
    db = get_store(database_type, path)

    # Perform the search using the provided diagnosis
    results = db.search(input_text, collection=collection)

    # Filter results based on relevance factor (distance)
    if relevance_factor is not None:
        results = [
            (obj, distance, _meta)
            for obj, distance, _meta in results
            if distance <= relevance_factor
        ]

    # Limit the results to the specified number (limit)
    limited_results = results[:limit] if results else []
    
    if verbose and not limited_results:
        print(f"Found no results for {input_text}")

    # Extract CURIEs and labels with exact match on prefix
    pred_ids = []
    pred_labels = []
    
    for obj, distance, _meta in limited_results:
        ontology_id = obj.get("original_id")
        disease_label = obj.get("label")
        
        # Ensure ontology_id is a string and check for matching prefixes
        ontology_id = str(ontology_id)
        
        # Print for debugging to check exact matching logic
        if verbose:
            print(f"Checking ontology_id: {ontology_id} against prefixes: {ontology_prefix}")
        
        # Only include ontology IDs that start with a prefix from ontology_prefix
        for prefix in ontology_prefix:
            if ontology_id.startswith(prefix):
                if verbose:
                    print(f"Matched: {ontology_id} with prefix: {prefix}")
                
                if ontology_id and disease_label:
                    pred_ids.append(ontology_id)
                    pred_labels.append(disease_label)
                break  # Exit the loop once a matching prefix is found

    # Return as a list of tuples (ID, Label)
    if len(pred_ids) == 0:
        if verbose:
            print(f"No grounded IDs found for {input_text}")
        return []

    return list(zip(pred_ids, pred_labels))



# Perform grounding on the text to target ontology and return the result
def perform_oak_grounding(
    annotator: TextAnnotatorInterface,
    diagnosis: str,
    exact_match: bool = True,
    verbose: bool = False,
    ontology_prefix: List[str] = [""],
) -> List[Tuple[str, str]]:
    """
    Perform grounding for a diagnosis. The 'exact_match' flag controls whether exact or inexact
    (partial) matching is used. Filter results to include only CURIEs that match the 'ontology_prefix',
    and exclude results that match the 'exclude_list'.
    Remove redundant groundings from the result.
    """
    config = TextAnnotationConfiguration(matches_whole_text=exact_match)
    annotations = list(annotator.annotate_text(diagnosis, configuration=config))

    # Filter and remove duplicates, while excluding unwanted general terms
    filtered_annotations = list(
        {
            (ann.object_id, ann.object_label)
            for ann in annotations
            if any(ann.object_id.startswith(prefix) for prefix in ontology_prefix)
        }
    )

    if filtered_annotations:
        return filtered_annotations
    else:
        match_type = "exact" if exact_match else "inexact"
        if verbose:
            logging.warning(f"No {match_type} grounded IDs found for: {diagnosis}")
        return None


# Now, integrate curategpt into your ground_diagnosis_text_to_mondo function
def ground_ontology_text(
    annotator: TextAnnotatorInterface,
    input_text: str,
    verbose: bool = False,
    ontology_prefix: List[str] = [""],
    use_ontogpt_grounding: bool = True,
    curategpt_path: str = "stagedb/",
    curategpt_collection: str = "ont_maxo",
    curategpt_database_type: str = "chromadb",
) -> List[Tuple[str, List[Tuple[str, str]]]]:
    results = []

    confidence = 1

    grounded = perform_oak_grounding(
        annotator,
        input_text,
        exact_match=True,
        verbose=verbose,
        ontology_prefix=ontology_prefix,
    )

    # Try grounding with curategpt if no grounding is found
    if use_ontogpt_grounding and not grounded:
        grounded = perform_curategpt_grounding(
            input_text=input_text,
            ontology_prefix=ontology_prefix,
            path=curategpt_path,
            collection=curategpt_collection,
            database_type=curategpt_database_type,
            verbose=verbose,
        )

    # If still no grounding is found, log the final failure
    if not grounded:
        if verbose:
            print(f"Final grounding failed for: {input_text}")

    # Append the grounded results
    for match in grounded:
        results.append(match)

    return results

