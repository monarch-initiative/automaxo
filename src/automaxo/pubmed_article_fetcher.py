import click
from Bio import Entrez
import requests
import json
import os
import time
import logging
import pandas as pd
from tqdm import tqdm
from pymongo import MongoClient

# Initialize logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.FileHandler('retrieve_pmids.log')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

Entrez.email = "enock.niyonkuru@jax.org"


def fetch_and_save_abstracts_to_mongodb(pmids_list, db_name, collection_name, max_articles_to_save):
    client = MongoClient('mongodb://localhost:27017/')
    db = client[db_name]
    collection = db[collection_name]

    not_found_count = 0
    found_count = 0
    skipped_count = 0

    for pmid in tqdm(pmids_list, desc="Fetching PMIDs", total=len(pmids_list)):
        if found_count >= max_articles_to_save:
            break  # End the loop if the maximum number of articles to save has been reached

        # Check if the PMID already exists in the collection
        if collection.find_one({'_id': pmid}):
            logger.info(f"PMID {pmid} already exists in the collection. Skipping...")
            skipped_count += 1
            continue  # Skip to the next PMID

        api_url = f"https://www.ncbi.nlm.nih.gov/research/pubtator3-api/publications/export/biocjson?pmids={pmid}"
        try_again = True  # Flag to control the retry mechanism
        while try_again:
            response = requests.get(api_url)
            if response.status_code == 200 and response.text.strip():
                try:
                    data = response.json()
                    if data:
                        data.pop('_id', None)  # Remove the '_id' field if it exists
                        collection.update_one({'_id': pmid}, {'$set': data}, upsert=True)
                        logger.info(f"Saved full text for PMID {pmid} in MongoDB collection '{collection_name}'.")
                        found_count += 1
                    else:
                        logger.info(f"No content for PMID {pmid}.")
                        not_found_count += 1
                    try_again = False
                except json.JSONDecodeError:
                    logger.info(f"Failed to decode JSON for PMID {pmid}.")
                    not_found_count += 1
                    try_again = False

            elif response.status_code == 429:
                logger.info(f"Rate limit exceeded for PMID {pmid}. Waiting 3 seconds before retrying...")
                time.sleep(3)
            else:
                logger.info(f"Failed to fetch full text for PMID {pmid}: HTTP {response.status_code}")
                not_found_count += 1
                try_again = False

    logger.info(f'Total articles found and saved: {found_count}')
    logger.info(f'Total articles not found: {not_found_count}')
    logger.info(f'Total articles skipped (already in collection): {skipped_count}')
    print(f"Total number of articles found and saved: {found_count} / {found_count + not_found_count + skipped_count} ")

    client.close()


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


def search_articles_with_mesh_info(disease_name: str, mesh_list_path: str, max_pmid_retrieve: int, db_name: str, collection_name: str):
    df = pd.read_csv(mesh_list_path, sep='\t', header=None)
    combined_mesh_ids = {mesh_id for mesh_ids in df.iloc[:, 2] for mesh_id in mesh_ids.split(';')}

    treatment_search = "(diagnosis[MeSH Terms] OR therapeutics[MeSH Terms])"
    search_term = f"({disease_name}[Title/Abstract]) AND ({treatment_search})"

    # Connect to MongoDB
    client = MongoClient('mongodb://localhost:27017/')
    db = client[db_name]
    collection = db[collection_name]

    pmid_mesh_info = {}
    retrieved_count = 0
    retstart = 0  # Starting index for PubMed search results

    while retrieved_count < max_pmid_retrieve:
        handle = Entrez.esearch(db="pubmed", term=search_term, retmax=max_pmid_retrieve, retstart=retstart)
        record = Entrez.read(handle)
        handle.close()

        for pmid in record["IdList"]:
            if collection.find_one({'_id': pmid}):
                continue  # Skip if PMID already exists in the collection

            mesh_info = fetch_mesh_ids(pmid)
            filtered_mesh_info = {mesh_id: descriptor_name for mesh_id, descriptor_name in mesh_info.items() if mesh_id in combined_mesh_ids}

            if filtered_mesh_info:  # Only add PMIDs with relevant MeSH info
                pmid_mesh_info[pmid] = filtered_mesh_info
                retrieved_count += 1

            if retrieved_count >= max_pmid_retrieve:
                break  # Stop if the maximum number of new PMIDs is reached

        retstart += max_pmid_retrieve  # Update the starting index for the next batch of search results

    client.close()
    return pmid_mesh_info


@click.command()
@click.option('-d', '--disease-name', required=True)
@click.option('-m', '--mesh-list-path', required=True)
@click.option('-p', '--max-pmid-retrieve', default=200, type=int)
@click.option('-n', '--max-articles-to-save', default=50, type=int)
@click.option('-b', '--db-name', required=True)  # MongoDB database name option
@click.option('-c', '--collection-name', required=True)  # MongoDB collection name option
@click.option('-i', '--info-collection-name', required=True)  # MongoDB collection name for pmid mesh info

def main(disease_name, mesh_list_path, max_pmid_retrieve, max_articles_to_save, db_name, collection_name, info_collection_name):
    selected_pmid_mesh_info = search_articles_with_mesh_info(disease_name, mesh_list_path, max_pmid_retrieve, db_name, collection_name)
    pmids_list = list(selected_pmid_mesh_info.keys())

    # Connect to MongoDB
    client = MongoClient('mongodb://localhost:27017/')
    db = client[db_name]
    info_collection = db[info_collection_name]

    # Save selected_pmid_mesh_info to MongoDB
    for pmid, mesh_info in selected_pmid_mesh_info.items():
        info_collection.update_one({'_id': pmid}, {'$set': {'mesh_info': mesh_info}}, upsert=True)

    # Call the function to save abstracts to MongoDB
    fetch_and_save_abstracts_to_mongodb(pmids_list, db_name, collection_name, max_articles_to_save)

    # Close the MongoDB connection
    client.close()

def run_in_notebook(disease_name, mesh_list_path, max_pmid_retrieve, max_articles_to_save, db_name, collection_name, info_collection_name):
    main.main(standalone_mode=False, args=[
        '--disease-name', disease_name,
        '--mesh-list-path', mesh_list_path,
        '--max-pmid-retrieve', str(max_pmid_retrieve),
        '--max-articles-to-save', str(max_articles_to_save),
        '--db-name', db_name,
        '--collection-name', collection_name,
        '--info-collection-name', info_collection_name
    ])

if __name__ == '__main__':
    main()

"""
python pubmed_article_fetcher.py -d "sickle cell" -m ../../data/mesh_sets.tsv -p 20 -n 10 -b sickle_cell_test -c sickle_cell_raw_data -i pmid_mesh_info
"""
