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
    Processes JSON files containing article data and writes the extracted PubMed ID, title, and abstract
    to a TSV file.

    Parameters:
    json_files_path (str): Path to the directory containing JSON files to be processed.
    no_replaced_tsv_file_path (str): Path to the output TSV file where the results will be saved.

    Description:
    The function reads JSON files, extracting the PubMed ID, title, and abstract from each article.
    Each JSON file can be in one of two formats:
    - Type 1: Contains a 'PubTator3' key with a list of article entries.
    - Type 2: Direct list of articles without a 'PubTator3' wrapper.

    Each line in the resulting TSV file corresponds to a PubMed ID followed by its associated title and abstract,
    separated by tabs. The function also ensures the output directory exists and creates it if necessary.
    """
    output_directory = os.path.dirname(no_replaced_tsv_file_path)
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    json_files = [f for f in os.listdir(json_files_path) if f.endswith(".json")]
    with open(no_replaced_tsv_file_path, 'w', encoding='utf-8') as tsv_file:
        tsv_file.write("PMID\tTitle\tAbstract\n")  # Write header to the TSV file
        for filename in tqdm(json_files, desc="Processing JSON files"):
            file_path = os.path.join(json_files_path, filename)
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                articles = data['PubTator3'] if 'PubTator3' in data else [data]
                
                for article in articles:
                    pmid = article['id']
                    title = ""
                    abstract = ""
                    for passage in article['passages']:
                        if passage['infons'].get('type') == 'title':
                            title = passage['text']
                        elif passage['infons'].get('type') == 'abstract':
                            abstract = passage['text']
                    
                    # Write each PubMed ID, title, and abstract to the TSV file
                    tsv_file.write(f"{pmid}\t{title}\t{abstract}\n")



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
