import click
from Bio import Entrez
import requests
import json
import os
import time
import logging
import pandas as pd

# Initialize logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.FileHandler('retrieve_pmids.log')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

Entrez.email = "enock.niyonkuru@jax.org"



def fetch_and_save_abstracts_json(pmids_list:str, json_dir_path:str, max_articles_to_save:int):
    """
    Fetches full texts for given PMC IDs in biocjson format and saves them as JSON files in the specified folder.
    Tracks the count of articles not found and successfully retrieved. Stops saving articles once a specified limit is reached.

    Parameters:
    - pmids_list (list of str): List of PMC IDs.
    - jason_dir_path (str): The base directory path where the files will be saved.
    - max_articles_to_save (int): Maximum number of articles to save before ending the function.
    """
    not_found_count = 0
    found_count = 0

    for pmid in pmids_list:
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
                        logging.info(f"Saved full text for PM ID {pmid} in '{full_path}'.")
                        found_count += 1
                    else:
                        print(f"No content for PM ID {pmid}.")
                        not_found_count += 1
                    try_again = False  # No need to retry
                except json.JSONDecodeError:
                    print(f"Failed to decode JSON for PM ID {pmid}.")
                    not_found_count += 1
                    try_again = False  # No need to retry

            elif response.status_code == 429:
                # If HTTP status code is 429, wait for 3 seconds and retry once
                print(f"Rate limit exceeded for PM ID {pmid}. Waiting 3 seconds before retrying...")
                time.sleep(3)  # Wait for 3 seconds
                # After waiting, the loop will try the request again
            else:
                print(f"Failed to fetch full text for PM ID {pmid}: HTTP {response.status_code}")
                not_found_count += 1
                try_again = False  # No need to retry


    logging.info(f'Total articles found and saved: {found_count}')
    logging.info(f'Total articles not found: {not_found_count}')


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
            print(f"Error fetching MeSH IDs for PMID {pmid}: {e}. Attempt {attempt + 1} of {retries}. Retrying in {delay} seconds.")
            time.sleep(delay)
    raise Exception(f"Failed to fetch MeSH IDs for PMID {pmid} after {retries} attempts.")


def search_articles_with_mesh_info(disease_name: str, mesh_list_path: str, max_pmid_retrieve: int):
    """
    Search articles related to a disease and treatments using combined MeSH IDs from a .tsv file, 
    and return their PubMed IDs along with the MeSH IDs and their descriptor names that contributed to their selection.
    
    Parameters:
    - disease_name: Name of the disease.
    - mesh_list_path: Path to the .tsv file containing MeSH IDs.
    - max_pmid_retrieve: Maximum number of PubMed IDs to retrieve.
    
    Returns:
    - Dictionary with PubMed IDs as keys and a dictionary of contributing MeSH IDs and descriptor names as values.
    """
    # Read the .tsv file and create a set of combined MeSH IDs
    df = pd.read_csv(mesh_list_path, sep='\t', header=None)
    
    combined_mesh_ids = {mesh_id for mesh_ids in df.iloc[:, 2] for mesh_id in mesh_ids.split(';')}

    # Combine disease name and treatment search terms
    treatment_search = "(diagnosis[MeSH Terms] OR therapeutics[MeSH Terms])"
    search_term = f"({disease_name}[Title/Abstract]) AND ({treatment_search})"

    # Perform the search
    handle = Entrez.esearch(db="pubmed", term=search_term, retmax=max_pmid_retrieve)
    record = Entrez.read(handle)
    handle.close()

    # Retrieve MeSH IDs and descriptor names for each PubMed ID and filter based on the combined mesh set
    pmid_mesh_info = {}
    for pmid in record["IdList"]:
        mesh_info = fetch_mesh_ids(pmid)
        filtered_mesh_info = {mesh_id: descriptor_name for mesh_id, descriptor_name in mesh_info.items() if mesh_id in combined_mesh_ids}
        pmid_mesh_info[pmid] = filtered_mesh_info

    return pmid_mesh_info

@click.command()
@click.option('-d', '--disease-name', required=True)
@click.option('-m', '--mesh-list-path', required=True)
@click.option('-o', '--output-dir', required=True)
@click.option('-p', '--max-pmid-retrieve', default=200, type=int)
@click.option('-n', '--max-articles-to-save', default=50, type=int)
@click.option('-j', '--json-file-path', required=True)

def pmid_extractor(disease_name, mesh_list_path, output_dir, max_pmid_retrieve, max_articles_to_save, json_file_path):
    selected_pmid_mesh_info = search_articles_with_mesh_info(disease_name, mesh_list_path, max_pmid_retrieve)
    pmids_list = list(selected_pmid_mesh_info.keys())
    
    # Create the directory if it does not exist
    json_dir = os.path.dirname(json_file_path)
    if not os.path.exists(json_dir):
        os.makedirs(json_dir)

    # Save the results to the specified JSON file
    with open(json_file_path, 'w') as json_file:
        json.dump(selected_pmid_mesh_info, json_file, indent=4)

    fetch_and_save_abstracts_json(pmids_list, output_dir, max_articles_to_save)

if __name__ == '__main__':
    pmid_extractor()
   



"""
python pubmed_article_fetcher.py -d "Disease Name" -m "/path/to/mesh/list.tsv" -o "/path/to/output/dir" -j "/path/to/selected_pmid_mesh_info.json"


"""
