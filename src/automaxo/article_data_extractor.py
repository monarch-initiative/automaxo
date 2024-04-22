import click
import json
import os
import logging
from tqdm import tqdm

# Configure specific logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.FileHandler('data_preprocessing.log')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


@click.command()
@click.option('-i', '--json_files_path', required=True, help="Path to the directory containing JSON files.")
@click.option('-n', '--no_replaced_tsv_file_path', required=True, help="Path to the output TSV file where no replacement occurred.")

def process_article_jsons_to_tsv(json_files_path, no_replaced_tsv_file_path):
    """
    Processes JSON files containing article data in two possible formats and writes the
    extracted PubMed ID and the concatenated text from passages to a TSV file.

    Parameters:
    json_files_path (str): Path to the directory containing JSON files to be processed.
    no_replaced_tsv_file_path (str): Path to the output TSV file where the results will be saved.

    Description:
    The function reads JSON files from the specified directory. Each file is expected to be in one
    of two formats:
    - Type 1: Contains a 'PubTator3' key with a list of article entries.
    - Type 2: Direct list of articles without a 'PubTator3' wrapper.
    
    For each article in the JSON files, it extracts the PubMed ID and concatenates all texts
    from the 'passages' field. The PubMed ID and concatenated text are then written to a TSV file,
    where each line corresponds to a PubMed ID followed by its associated text, separated by a tab.

    The function also ensures that the output directory exists, and if not, it creates it.

    Uses:
    - tqdm for progress indication during processing.
    - json for parsing JSON files.
    - os for directory and file operations.
    """
    output_directory = os.path.dirname(no_replaced_tsv_file_path)
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    json_files = [f for f in os.listdir(json_files_path) if f.endswith(".json")]
    with open(no_replaced_tsv_file_path, 'w', encoding='utf-8') as tsv_file:
        for filename in tqdm(json_files, desc="Processing JSON files"):
            file_path = os.path.join(json_files_path, filename)
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                # Check if 'PubTator3' key exists to determine the JSON type
                if 'PubTator3' in data:
                    articles = data['PubTator3']
                else:
                    articles = [data]
                
                # Initialize a dictionary to hold concatenated texts for each PubMed ID
                pubmed_texts = {}
                for article in articles:
                    pmid = article['id']
                    # Concatenate texts within the same PubMed ID
                    if pmid not in pubmed_texts:
                        pubmed_texts[pmid] = ""
                    pubmed_texts[pmid] += " ".join(passage['text'] for passage in article['passages'])
                
                # Write each PubMed ID and its concatenated text to the TSV file
                for pmid, text in pubmed_texts.items():
                    tsv_file.write(f"{pmid}\t{text}\n")


def run_in_notebook(json_files_path, no_replaced_tsv_file_path):
    process_article_jsons_to_tsv.main(standalone_mode=False, args=[
        '--json_files_path', json_files_path,
        '--no_replaced_tsv_file_path', no_replaced_tsv_file_path
    ])


if __name__ == '__main__':
    process_article_jsons_to_tsv()


"""
python article_data_extractor.py -i "/path/to/json/files"  -n "/path/to/no_replaced.tsv"

python article_data_extractor.py -i ../../data/sickle_cell/pubtator3_json/ -n  ../../data/sickle_cell/sickle_cell_no_replaced.tsv 

"""
