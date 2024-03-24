import click
import json
import os
import logging
from tqdm import tqdm

logger = logging.basicConfig(filename='data_preprocessing.log',
                    level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


# Updated function based on the provided structure and logic for building new text with replacements
def extract_passages(passages:str):
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
        text_offset = passage["offset"] # Initialize last_offset to the start of the passage text        
        for annotation in sorted(passage["annotations"], key=lambda x: x["locations"][0]["offset"]):
            biotype = annotation["infons"]["biotype"]
            normalized_id = annotation["infons"]["normalized_id"]
            if normalized_id:
                prefix = biotype_prefix.get(biotype, "")
                replacement_text = f"{prefix}{normalized_id}"
                for location in annotation["locations"]:
                    start = location["offset"] - text_offset
                    end = start + location["length"]
                    # Append text from last_offset to the start of the current annotation
                    new_text += passage["text"][last_offset:start]
                    # Append the replacement text
                    new_text += replacement_text
                    # Update last_offset to after the current annotation
                    last_offset = end

        # Append any remaining text after the last annotation
        new_text += passage["text"][last_offset:]
        # Update the passage text with the new constructed text
        passage["text"] = new_text
    
    return passages

def extract_relationships(relations:str):
    biotype_prefix = {
        "gene": "ncbi",
        "disease": "disease",
        "chemical": "chemical",
        "variant": "variant",
        "specie": "specie",
        "cell line": "cellosaurus"
    }

    relationships = []
    for relation in relations:
        infons = relation['infons']
        role1_biotype = infons['role1']['biotype']
        role1_normalized_id = infons['role1']['normalized_id']
        role2_biotype = infons['role2']['biotype']
        role2_normalized_id = infons['role2']['normalized_id']
        relationship_type = infons['type']

        # Apply prefixes based on biotype
        role1_prefix = biotype_prefix.get(role1_biotype, "")
        role2_prefix = biotype_prefix.get(role2_biotype, "")

        relationships.append(f"{relationship_type}|{role1_prefix}{role1_normalized_id}|{role2_prefix}{role2_normalized_id}")

    return relationships


@click.command()
@click.option('-i', '--json_files_path', required=True, help="Path to the directory containing JSON files.")
@click.option('-r', '--replaced_tsv_file_path', required=True, help="Path to the output TSV file where replacement occurred.")
@click.option('-n', '--no_replaced_tsv_file_path', required=True, help="Path to the output TSV file where no replacement occurred.")

def process_article_jsons_to_tsv(json_files_path:str, replaced_tsv_file_path:str, no_replaced_tsv_file_path:str):
    """
    Processes JSON files in the given directory, extracting PMC ID, text content, and relationship,
    and saves them into a single TSV file with three columns: PMC ID, text, and relationship.

    Parameters:
    - json_files_path (str): The path to the directory containing JSON files.
    - replaced_tsv_file_path (str): The path to the output TSV file where replacement occurred.
    - no_replaced_tsv_file_path (str): The path to the output TSV file where no replacement occurred.
    """

    # Ensure the output directory exists
    output_directory = os.path.dirname(replaced_tsv_file_path)
    if output_directory:
        os.makedirs(output_directory, exist_ok=True)

    json_files = [f for f in os.listdir(json_files_path) if f.endswith(".json")]
     # Open the TSV files for writing
    with open(replaced_tsv_file_path, 'w', encoding='utf-8') as replaced_tsv_file, \
         open(no_replaced_tsv_file_path, 'w', encoding='utf-8') as no_replaced_tsv_file:
        
        # Iterate over all files in the given directory
        for filename in tqdm(json_files, desc="Processing JSON files", total=len(json_files)):
            json_file_path = os.path.join(json_files_path, filename)

            with open(json_file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)

                # Concatenate all passage no replacement texts into one string
                text_content_no_replaced = "".join([passage["text"] for passage in data["passages"]])

                # Apply Replacement
                corrected_passages = extract_passages(data["passages"])

                # Concatenate all passage replaced texts into one string
                text_content_replaced = "".join([passage["text"] for passage in corrected_passages])

                # Extract relationships
                relationship_no_replaced = [relation['name'] for relation in data['relations_display']]
                relationship_no_replaced = ' ;'.join(relationship_no_replaced)

                relationship_replaced = extract_relationships(data.get('relations', []))
                relationships_replaced = "; ".join(relationship_replaced)


                # Extract PMC ID from the filename (assuming PMC ID is the filename without extension)
                pmc_id = os.path.splitext(filename)[0]

                # Write the PMC ID, text content, and relationships to the TSV file
                replaced_tsv_file.write(f"{pmc_id}\t{relationships_replaced}\t{text_content_replaced}\n")

                # Write the PMC ID, text content, and relationships to the TSV file
                no_replaced_tsv_file.write(f"{pmc_id}\t{relationship_no_replaced}\t{text_content_no_replaced}\n")

        logging.info(f'Processed and saved all entries to: {replaced_tsv_file_path}')
        logging.info(f'Unprocessed and saved all entries to: {no_replaced_tsv_file_path}')
        


def run_in_notebook(json_files_path, replaced_tsv_file_path, no_replaced_tsv_file_path):
    process_article_jsons_to_tsv.main(standalone_mode=False, args=[
        '--json_files_path', json_files_path,
        '--replaced_tsv_file_path', replaced_tsv_file_path,
        '--no_replaced_tsv_file_path', no_replaced_tsv_file_path
    ])


if __name__ == '__main__':
    process_article_jsons_to_tsv()


"""
python article_data_extractor.py -i "/path/to/json/files" -r "/path/to/replaced.tsv" -n "/path/to/no_replaced.tsv"

python article_data_extractor.py -i ../../data/sickle_cell/pubtator3_json/ -r ../../data/sickle_cell/sickle_cell_mesh_replaced.tsv -n ../../data/sickle_cell/sickle_cell_no_replaced.tsv 

"""
