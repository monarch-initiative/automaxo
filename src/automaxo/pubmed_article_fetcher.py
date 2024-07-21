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

# Optional Global Variables
NCBI_KEY = "7c7bd2e8c94b474559a8993a626f9ea64008"  # Set this if you have an API key
ENTREZ_EMAIL = "enockniyonkuru250@gmail.com"	# Set this if you have a registered email

RETRY_MAX = 3
BATCH_SIZE = 500



def fetch_and_save_abstracts_json(pmids_list, json_dir_path, max_articles_to_save):
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
        if found_count >= max_articles_to_save:
            break  # End the loop if the maximum number of articles to save has been reached

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
            logger.error(f"Error fetching MeSH IDs for PMID {pmid}: {e}")
            time.sleep(1)
            retries += 1
    raise Exception(f"Failed to fetch MeSH IDs for PMID {pmid} after {RETRY_MAX} attempts.")



def search_mesh_info_existing_pmids(mesh_list_path: str, existing_pmids: set):
    df = pd.read_csv(mesh_list_path, sep='\t', header=None)
    combined_mesh_ids = {mesh_id for mesh_ids in df.iloc[:, 2] for mesh_id in mesh_ids.split(';')}

    # Retrieve MeSH information for existing PubMed IDs
    existing_pmid_mesh_info = {pmid: fetch_mesh_ids(pmid) for pmid in tqdm(existing_pmids, desc="Retrieving MeSH info for existing PMIDs")}

    # Filter the MeSH information based on the combined mesh IDs
    filtered_existing_pmid_mesh_info = {}
    for pmid, mesh_info in existing_pmid_mesh_info.items():
        filtered_mesh_info = {mesh_id: descriptor_name for mesh_id, descriptor_name in mesh_info.items() if mesh_id in combined_mesh_ids}
        if filtered_mesh_info:  # Only add PMIDs with relevant MeSH info
            filtered_existing_pmid_mesh_info[pmid] = filtered_mesh_info

    return filtered_existing_pmid_mesh_info

def search_articles_with_mesh_info(disease_name: str, mesh_list_path: str, max_articles_to_save: int, existing_pmids: set):
    df = pd.read_csv(mesh_list_path, sep='\t', header=None)
    combined_mesh_ids = {mesh_id for mesh_ids in df.iloc[:, 2] for mesh_id in mesh_ids.split(';')}

    treatment_search = "(diagnosis[MeSH Terms] OR therapeutics[MeSH Terms])"
    search_term = f"({disease_name}[Title/Abstract]) AND ({treatment_search})"

    pmid_mesh_info = {}
    retrieved_count = 0
    retstart = 0

    while retrieved_count < max_articles_to_save:
        try:
            params = {
                'db': 'pubmed',
                'term': search_term,
                'retmax': max_articles_to_save,
                'retstart': retstart,
                'email': ENTREZ_EMAIL if ENTREZ_EMAIL else None,
                'api_key': NCBI_KEY if NCBI_KEY else None
            }
            handle = Entrez.esearch(**params)
            record = Entrez.read(handle)
            handle.close()

            for pmid in record["IdList"]:
                if pmid in existing_pmids:
                    continue

                mesh_info = fetch_mesh_ids(pmid)
                filtered_mesh_info = {mesh_id: descriptor_name for mesh_id, descriptor_name in mesh_info.items() if mesh_id in combined_mesh_ids}

                if filtered_mesh_info:
                    pmid_mesh_info[pmid] = filtered_mesh_info
                    retrieved_count += 1
                    if retrieved_count >= max_articles_to_save:
                        break

            retstart += max_articles_to_save
        except Exception as e:
            logger.error(f"Error processing batch starting at {retstart}: {e}")
            break

    return pmid_mesh_info

@click.command()
@click.option('-d', '--disease-name', required=True)
@click.option('-m', '--mesh-list-path', required=True)
@click.option('-o', '--output-dir', required=True)
@click.option('-j', '--json-file-path', required=True)
@click.option('-n', '--max-articles-to-save', default=50, type=int)

def main(disease_name, mesh_list_path, output_dir, json_file_path, max_articles_to_save):

    # Create the directory if it does not exist
    json_dir = os.path.dirname(json_file_path)
    if not os.path.exists(json_dir):
        os.makedirs(json_dir)

    # Check the output directory and create a set of existing PubMed IDs
    existing_pmids = set()
    if os.path.exists(output_dir):
        for filename in os.listdir(output_dir):
            if filename.endswith('.json'):
                pmid = filename.split('.')[0]
                existing_pmids.add(pmid)
    
    logger.info(f" The directory {output_dir} had already {len(existing_pmids)} extracted articles.")

    # Retrieve MeSH information for existing PubMed IDs
    existing_pmid_mesh_info = search_mesh_info_existing_pmids(mesh_list_path, existing_pmids)


    # Retrieve MeSH information for new PubMed IDs
    print((f"Starting to search for {max_articles_to_save} pmids that were not previously saved ...."))
    new_pmid_mesh_info = search_articles_with_mesh_info(disease_name, mesh_list_path, max_articles_to_save, existing_pmids)
    

    # Combine existing and new PubMed ID MeSH information
    selected_pmid_mesh_info = {**existing_pmid_mesh_info, **new_pmid_mesh_info}

    # Save the combined results to the specified JSON file
    with open(json_file_path, 'w') as json_file:
        json.dump(selected_pmid_mesh_info, json_file, indent=4)

    # Generate a list of all PubMed IDs (existing and new)
    pmids_list = list(new_pmid_mesh_info.keys())

    # Fetch and save abstracts for all PubMed IDs
    fetch_and_save_abstracts_json(pmids_list, output_dir, max_articles_to_save)
  

def run_in_notebook(disease_name, mesh_list_path, output_dir, json_file_path, max_articles_to_save):
    main.main(standalone_mode=False, args=[
        '--disease-name', disease_name,
        '--mesh-list-path', mesh_list_path,
        '--output-dir', output_dir,
        '--json-file-path', json_file_path,
        '--max-articles-to-save', max_articles_to_save

    ])

if __name__ == '__main__':
    main()


"""
python pubmed_article_fetcher.py -d "sickle cell" -m ../../data/mesh_sets.tsv -o ../../data/sickle_cell/pubtator3_json/  -j ../../data/sickle_cell/selected_pmid_mesh_info.json -n 2



"""
