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


def perform_curategpt_grounding(
    input_text: str,
    path: str = "stagedb/",
    collection: str = "ont_maxo",
    database_type: str = "chromadb",
    limit: int = 1,
    relevance_factor: float = 1000000.0,
    verbose: bool = False,
) -> List[Tuple[str, str]]:
    """
    Use curategpt to perform grounding for a given text when initial attempts fail.

    Parameters:
    - input_text: The text to ground.
    - path: The path to the database. You'll need to create an index of the target ontology using curategpt in this db
    - collection: The collection to search within curategpt. Name of target ontology collection in the db
    NB: You can make this collection by running curategpt thusly (e.g., for MONDO):
    `curategpt ontology index --index-fields label,definition,relationships -p stagedb -c ont_mondo -m openai: sqlite:obo:mondo`
    - database_type: The type of database used for grounding (e.g., chromadb, duckdb).
    - limit: The number of search results to return.
    - relevance_factor: The distance threshold for relevance filtering.
    - verbose: Whether to print verbose output for debugging.

    Returns:
    - List of tuples: [(CURIE, Label), ...]
    """
    # Initialize the database store
    # TODO: just initialize this once so we can re-use it
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
    limited_results = results[:limit]

    # Extract CURIEs and labels
    pred_ids = []
    pred_labels = []

    for obj, distance, _meta in limited_results:
        disease_mondo_id = obj.get(
            "original_id"
        )  # Use the 'original_id' field for Mondo ID
        disease_label = obj.get("label")

        if disease_mondo_id and disease_label:
            pred_ids.append(disease_mondo_id)
            pred_labels.append(disease_label)

    # Return as a list of tuples (ID, Label)
    if len(pred_ids) == 0:
        if verbose:
            print(f"No grounded IDs found for {input_text}")
        return None

    return list(zip(pred_ids, pred_labels))


# Perform grounding on the text to target ontology and return the result
def perform_oak_grounding(
    annotator: TextAnnotatorInterface,
    diagnosis: str,
    exact_match: bool = True,
    verbose: bool = False,
    include_list: List[str] = [""],
) -> List[Tuple[str, str]]:
    """
    Perform grounding for a diagnosis. The 'exact_match' flag controls whether exact or inexact
    (partial) matching is used. Filter results to include only CURIEs that match the 'include_list',
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
            if any(ann.object_id.startswith(prefix) for prefix in include_list)
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
    include_list: List[str] = [""],
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
        include_list=include_list,
    )

    # Try grounding with curategpt if no grounding is found
    if use_ontogpt_grounding and not grounded:
        grounded = perform_curategpt_grounding(
            input_text=input_text,
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


# Main function to run ground_diagnosis_text_to_maxo
# if __name__ == "__main__":
#     output = ground_diagnosis_text_to_maxo(
#         annotator=get_adapter("sqlite:obo:maxo"),
#         differential_diagnosis="allogeneic bmt",
#         verbose=True,
#         include_list=["MAXO:"],
#         use_ontogpt_grounding=True,
#         curategpt_path="../../stagedb/",
#         curategpt_collection="ont_maxo",
#         curategpt_database_type="chromadb"
#     )
