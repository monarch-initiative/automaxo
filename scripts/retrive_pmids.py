from Bio import Entrez
import requests
import json
import os
import time  
import logging


logger = logging.basicConfig(filename='retrive_pmids.log',
                    level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

Entrez.email = "enock.niyonkuru@jax.org"


class RetrivePmids:

    def __init__(self,disease_name,jason_dir_path, max_pmid_retrive, max_articles_to_save ) -> None:

        self._disease_name = disease_name
        self._jason_dir_path = jason_dir_path
        self._max_pmid_retrive = max_pmid_retrive
        self._max_articles_to_save = max_articles_to_save

        self.pmids_list = self.search_articles(self._disease_name,self._max_pmid_retrive)

        logging.info(f'Length of PM IDs: {len(self.pmids_list )}')

        os.makedirs(jason_dir_path, exist_ok=True)
        
        self.fetch_and_save_abst_json(self.pmids_list , self._jason_dir_path, self._max_articles_to_save)

            

    def search_articles(self, _disease_name, _max_pmid_retrive):
        """
        Search articles related to a disease and return their PubMed IDs.
        """
        search_term = f"{_disease_name}[Title/Abstract]"
        handle = Entrez.esearch(db="pubmed", term=search_term, retmax=_max_pmid_retrive)
        record = Entrez.read(handle)
        handle.close()
        return record["IdList"]


    def fetch_and_save_abst_json(self, pmids_list, _jason_dir_path, _max_articles_to_save):
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
            if found_count >= _max_articles_to_save:
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
                            full_path = os.path.join(_jason_dir_path, filename)
                            with open(full_path, 'w', encoding='utf-8') as file:
                                json.dump(data, file, indent=4)
                            print(f"Saved full text for PM ID {pmid} in '{full_path}'.")
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
        



if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument("-d", type=str, help="Disease name", required=True)
    parser.add_argument("-o", type=str, help="Address of output directory", required=True)
    parser.add_argument("-m", "--max_pmid_retrieve", type=int, default=200, help="The maximum number of PMIDs to retrieve for a particular disease", required=False)
    parser.add_argument("-n", "--max_articles_to_save", type=int, default=50, help="The maximum number of JSON files of articles to save", required=False)

    args = parser.parse_args()

    RetrivePmids(args.d, args.o, args.max_pmid_retrieve, args.max_articles_to_save)



"""
Sample way of running the code:
python retrive_pmids.py  -d Anemia  -o ../dump/json_files -m 200 -n 50
"""