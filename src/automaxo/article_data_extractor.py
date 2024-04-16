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

def extract_passages(passages):
    biotype_prefix = {
        "gene": "ncbi",
        "disease": "disease",
        "chemical": "chemical",
        "variant": "variant",
        "specie": "specie",
        "cell line": "cellosaurus"
    }
    
    for passage in passages:
        new_text = ""
        last_offset = 0
        text_offset = passage.get("offset", 0)  # Safe get with default
        for annotation in sorted(passage.get("annotations", []), key=lambda x: x["locations"][0]["offset"]):
            biotype = annotation["infons"]["biotype"]
            normalized_id = annotation["infons"]["normalized_id"]
            if normalized_id:
                prefix = biotype_prefix.get(biotype, "")
                replacement_text = f"{prefix}{normalized_id}"
                for location in annotation["locations"]:
                    start = location["offset"] - text_offset
                    end = start + location["length"]
                    new_text += passage["text"][last_offset:start] + replacement_text
                    last_offset = end

        new_text += passage["text"][last_offset:]
        passage["text"] = new_text
    
    return passages

@click.command()
@click.option('-i', '--json_files_path', required=True, help="Path to the directory containing JSON files.")
@click.option('-n', '--no_replaced_tsv_file_path', required=True, help="Path to the output TSV file where no replacement occurred.")
def process_article_jsons_to_tsv(json_files_path, no_replaced_tsv_file_path):
    output_directory = os.path.dirname(no_replaced_tsv_file_path)
    if not os.path.exists(output_directory):
        os.makedirs(output_directory, exist_ok=True)

    json_files = [f for f in os.listdir(json_files_path) if f.endswith(".json")]
    with open(no_replaced_tsv_file_path, 'w', encoding='utf-8') as no_replaced_tsv_file:
        for filename in tqdm(json_files, desc="Processing JSON files"):
            try:
                json_file_path = os.path.join(json_files_path, filename)
                with open(json_file_path, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                text_content_no_replaced = "".join(p["text"] for p in data["passages"])
                corrected_passages = extract_passages(data["passages"])
                text_content_replaced = "".join(p["text"] for p in corrected_passages)
                relationships = ' ;'.join(r['name'] for r in data.get('relations_display', []))
                pmc_id = os.path.splitext(filename)[0]
                no_replaced_tsv_file.write(f"{pmc_id}\t{relationships}\t{text_content_no_replaced}\n")
            except Exception as e:
                logger.error(f"Failed to process file {filename}: {e}")

        logger.info(f'Processed all entries and saved to: {no_replaced_tsv_file_path}')



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
