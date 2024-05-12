import click
from Bio import Entrez
import requests
import json
import os
import time
import logging
import pandas as pd
from tqdm import tqdm


# Set up your logging as per the provided configuration
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.FileHandler('retrieve_pmids.log')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Set up basic configuration for logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

# Optional Global Variables
NCBI_KEY = "7c7bd2e8c94b474559a8993a626f9ea64008"  # Set this if you have an API key
ENTREZ_EMAIL = "enockniyonkuru250@gmail.com"	# Set this if you have a registered email

RETRY_MAX = 3
BATCH_SIZE = 500



def fetch_and_save_abstracts_json(pmids_list, json_dir_path):
    """
    Fetches full texts for given PMC IDs in biocjson format and saves them as JSON files in the specified folder.
    Tracks the count of articles not found and successfully retrieved. Stops saving articles once a specified limit is reached.

    Parameters:
    - pmids_list (list of str): List of PMC IDs.
    - json_dir_path (str): The base directory path where the files will be saved.
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

def fetch_mesh_ids(pmid: str) -> dict:
    """Fetch MeSH IDs and their descriptor names for a given PubMed ID."""
    if ENTREZ_EMAIL:
        Entrez.email = ENTREZ_EMAIL  # Only set if email is provided

    retries = 0
    params = {
        'db': 'pubmed',
        'id': pmid,
        'retmode': 'xml'
    }
    if NCBI_KEY:
        params['api_key'] = NCBI_KEY  # Only add API key to params if it's provided

    while retries < RETRY_MAX:
        try:
            handle = Entrez.efetch(**params)
            article = Entrez.read(handle)
            handle.close()

            mesh_info = {}
            if 'PubmedArticle' in article:
                mesh_heading_list = article['PubmedArticle'][0].get('MedlineCitation', {}).get('MeshHeadingList', [])
                for mesh_heading in mesh_heading_list:
                    descriptor = mesh_heading.get('DescriptorName')
                    if descriptor:
                        mesh_id = descriptor.attributes.get('UI')
                        if mesh_id:
                            mesh_info[mesh_id] = str(descriptor)
            return mesh_info
        except Exception as e:
            logging.error(f"Error fetching MeSH IDs for PMID {pmid}: {e}")
            time.sleep(1)
            retries += 1
    logging.error(f"Failed to fetch MeSH IDs for PMID {pmid} after {RETRY_MAX} attempts.")
    return {}

def search_mesh_info_existing_pmids(mesh_list_path: str, existing_pmids: set):
    df = pd.read_csv(mesh_list_path, sep='\t', header=None)
    combined_mesh_ids = {mesh_id for mesh_ids in df.iloc[:, 2] for mesh_id in mesh_ids.split(';')}

    existing_pmid_mesh_info = {}
    for pmid in tqdm(existing_pmids, desc="Retrieving MeSH info for existing PMIDs"):
        mesh_info = fetch_mesh_ids(pmid)
        if mesh_info:  # Only store if there's any data fetched
            existing_pmid_mesh_info[pmid] = mesh_info

    filtered_existing_pmid_mesh_info = {}
    for pmid, mesh_info in existing_pmid_mesh_info.items():
        filtered_mesh_info = {mesh_id: descriptor_name for mesh_id, descriptor_name in mesh_info.items() if mesh_id in combined_mesh_ids}
        if filtered_mesh_info:
            filtered_existing_pmid_mesh_info[pmid] = filtered_mesh_info

    return filtered_existing_pmid_mesh_info


@click.command()
@click.option('-i', '--maxo-annotations-path', required=True)
@click.option('-m', '--mesh-list-path', required=True)
@click.option('-o', '--output-dir', required=True)
@click.option('-j', '--json-file-path', required=True)

# def main(maxo_annotations_path, mesh_list_path, output_dir, json_file_path):

#     # Create the directory if it does not exist
#     json_dir = os.path.dirname(json_file_path)
#     if not os.path.exists(json_dir):
#         os.makedirs(json_dir)

def main(maxo_annotations_path, mesh_list_path, output_dir, json_file_path):
    # Create the directory if it does not exist
    json_dir = os.path.dirname(json_file_path)
    if json_dir and not os.path.exists(json_dir):
        os.makedirs(json_dir)

    # Read the Maxo annotations and extract the PubMed IDs
    maxo_annotations_df = pd.read_csv(maxo_annotations_path, delimiter='\t')
    annotated_pm_ids = maxo_annotations_df['citation']
    annotated_filtered_ids = set(id.split(':')[1] for id in annotated_pm_ids if id.startswith('PMID:'))


    #Retrieve MeSH information for existing PubMed IDs
    selected_pmid_mesh_info = search_mesh_info_existing_pmids(mesh_list_path, existing_pmids=annotated_filtered_ids)


    # Save the combined results to the specified JSON file
    with open(json_file_path, 'w') as json_file:
        json.dump(selected_pmid_mesh_info, json_file, indent=4)

    # Generate a list of all PubMed IDs (existing and new)
    pmids_list = list(selected_pmid_mesh_info.keys())

    # Fetch and save abstracts for all PubMed IDs
    fetch_and_save_abstracts_json(pmids_list, output_dir)
  


def run_in_notebook(maxo_annotations_path, mesh_list_path, output_dir, json_file_path):
    main.main(standalone_mode=False, args=[
        '--maxo-annotations-path', maxo_annotations_path,
        '--mesh-list-path', mesh_list_path,
        '--output-dir', output_dir,
        '--json-file-path', json_file_path,

    ])

if __name__ == '__main__':
    main()


"""
python pubmed_article_fetcher.py -d "sickle cell" -m ../../data/mesh_sets.tsv -o ../../data/sickle_cell/pubtator3_json/  -j ../../data/sickle_cell/selected_pmid_mesh_info.json -n 10



"""
