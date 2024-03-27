import click
from Bio import Entrez
import requests
import json
import os
import time
import logging
import pandas as pd
from tqdm import tqdm

# Initialize logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.FileHandler('retrieve_pmids_evaluation.log')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

Entrez.email = "enock.niyonkuru@jax.org"



def fetch_and_save_abstracts_json(pmids_list, json_dir_path):
    """
    Fetches full texts for given PMC IDs in biocjson format and saves them as JSON files in the specified folder.
    Tracks the count of articles not found and successfully retrieved. Stops saving articles once a specified limit is reached.

    Parameters:
    - pmids_list (list of str): List of PMC IDs.
    - json_dir_path (str): The base directory path where the files will be saved.
    - max_articles_to_save (int): Maximum number of articles to save before ending the function.
    """
    not_found_count = 0
    found_count = 0

    # Check if the directory exists, if not, create it
    os.makedirs(json_dir_path, exist_ok=True)

    for pmid in tqdm(pmids_list, desc="Fetching PMIDs", total=len(pmids_list)):
        api_url = f"https://www.ncbi.nlm.nih.gov/research/pubtator3-api/publications/export/biocjson?pmids={pmid}"
        try_again = True  # Flag to control the retry mechanism
        while try_again:
            response = requests.get(api_url)
            if response.status_code == 200 and response.text.strip():
                # Check if the response is not empty
                try:
                    data = response.json()
                    if data:  # Additional check to ensure JSON is not empty
                        filename = f"{pmid}.json"
                        full_path = os.path.join(json_dir_path, filename)
                        with open(full_path, 'w', encoding='utf-8') as file:
                            json.dump(data, file, indent=4)
                        logger.info(f"Saved full text for PM ID {pmid} in '{full_path}'.")
                        found_count += 1
                    else:
                        print(f"No content for PM ID {pmid}.")
                        not_found_count += 1
                    try_again = False  # No need to retry
                except json.JSONDecodeError:
                    logger.info(f"Failed to decode JSON for PM ID {pmid}.")
                    not_found_count += 1
                    try_again = False  # No need to retry

            elif response.status_code == 429:
                # If HTTP status code is 429, wait for 3 seconds and retry once
                logger.info(f"Rate limit exceeded for PM ID {pmid}. Waiting 3 seconds before retrying...")
                time.sleep(3)  # Wait for 3 seconds
                # After waiting, the loop will try the request again
            else:
                logger.info(f"Failed to fetch full text for PM ID {pmid}: HTTP {response.status_code}")
                not_found_count += 1
                try_again = False  # No need to retry

    logger.info(f'Total articles found and saved: {found_count}')
    logger.info(f'Total articles not found: {not_found_count}')
    print(f"Total number of articles found and saved: {found_count} / {found_count + not_found_count} ")


def fetch_mesh_ids(pmid, retries=3, delay=2):
    """
    Fetch MeSH IDs and their descriptor names for a given PubMed ID.

    Parameters:
    - pmid: PubMed ID.
    - retries: Number of retries in case of an HTTP error.
    - delay: Delay in seconds before retrying.

    Returns:
    - Dictionary with MeSH IDs as keys and descriptor names as values.
    """
    for attempt in range(retries):
        try:
            handle = Entrez.efetch(db="pubmed", id=pmid, retmode="xml")
            article = Entrez.read(handle)
            handle.close()

            # Extract MeSH IDs and descriptor names from the article
            mesh_info = {}
            if 'PubmedArticle' in article:
                mesh_heading_list = article['PubmedArticle'][0].get('MedlineCitation', {}).get('MeshHeadingList', [])
                for mesh_heading in mesh_heading_list:
                    descriptor_name = mesh_heading.get('DescriptorName')
                    if descriptor_name:
                        mesh_id = descriptor_name.attributes.get('UI')
                        if mesh_id:
                            mesh_info[mesh_id] = str(descriptor_name)

            return mesh_info
        except Exception as e:
            logger.info(f"Error fetching MeSH IDs for PMID {pmid}: {e}. Attempt {attempt + 1} of {retries}. Retrying in {delay} seconds.")
            time.sleep(delay)
    logger.error(f"Failed to fetch MeSH IDs for PMID {pmid} after {retries} attempts.")
    return {}

def search_articles_with_mesh_info(maxo_annotations_path: str, mesh_list_path: str):

    # Read the list of MeSH IDs and create a set of combined MeSH IDs
    df = pd.read_csv(mesh_list_path, sep='\t', header=None)
    combined_mesh_ids = set(mesh_id for mesh_ids in df.iloc[:, 2] for mesh_id in mesh_ids.split(';'))

    # Read the Maxo annotations and extract the PubMed IDs
    maxo_annotations_df = pd.read_csv(maxo_annotations_path, delimiter='\t')
    annotated_pm_ids = maxo_annotations_df['citation']
    annotated_filtered_ids = set(id.split(':')[1] for id in annotated_pm_ids if id.startswith('PMID:'))

    # Initialize a dictionary to store PMID and their corresponding filtered MeSH information
    pmid_mesh_info = {}

    # Iterate through the filtered PubMed IDs
    for pmid in tqdm(annotated_filtered_ids, desc="Processing PubMed IDs"):
        # Fetch the MeSH information for each PMID
        mesh_info = fetch_mesh_ids(pmid)
        # Filter the MeSH information based on the combined MeSH IDs
        filtered_mesh_info = {mesh_id: descriptor_name for mesh_id, descriptor_name in mesh_info.items() if mesh_id in combined_mesh_ids}

        # Add the PMID and its filtered MeSH information to the dictionary if there is any relevant MeSH info
        if filtered_mesh_info:
            pmid_mesh_info[pmid] = filtered_mesh_info

    return pmid_mesh_info


@click.command()
@click.option('-i', '--maxo-annotations-path', required=True)
@click.option('-m', '--mesh-list-path', required=True)
@click.option('-o', '--output-dir', required=True)
@click.option('-j', '--mesh_info_json_file_path', required=True)
def main(maxo_annotations_path, mesh_list_path, output_dir, mesh_info_json_file_path):
    

    json_dir = os.path.dirname(mesh_info_json_file_path)
    if json_dir and not os.path.exists(json_dir):
        os.makedirs(json_dir)


    # Retrieve MeSH information for PubMed IDs
    pmid_mesh_info = search_articles_with_mesh_info(maxo_annotations_path, mesh_list_path)
    
    # Save the PubMed ID MeSH information to the specified JSON file
    with open(mesh_info_json_file_path, 'w') as json_file:
        json.dump(pmid_mesh_info, json_file, indent=4)

    # Generate a list of all PubMed IDs
    pmids_list = list(pmid_mesh_info.keys())

    # Fetch and save abstracts for all PubMed IDs
    fetch_and_save_abstracts_json(pmids_list, output_dir)
  

def run_in_notebook(maxo_annotations_path, mesh_list_path, output_dir, mesh_info_json_file_path):
    main.main(standalone_mode=False, args=[
        '--maxo-annotations-path', maxo_annotations_path,
        '--mesh-list-path', mesh_list_path,
        '--output-dir', output_dir,
        '--mesh_info_json_file_path', mesh_info_json_file_path,
    ])
if __name__ == '__main__':
    main()


"""
python pubmed_article_fetcher_evaluation.py -i maxo-annotations.tsv -m ../data/mesh_sets.tsv -o /evaluation_pubtator3_json -j evaluation_selected_pmid_mesh_info.json

"""
