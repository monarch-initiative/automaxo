import click
import json
import os
import logging
from tqdm import tqdm
from pymongo import MongoClient


# Initialize logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.FileHandler('process_articles.log')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


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
@click.option('-i', '--db_name', required=True, help="Name of the MongoDB database.")
@click.option('-c', '--input_collection_name', required=True, help="Name of the MongoDB collection for input.")
@click.option('-r', '--replaced_collection_name', required=True, help="Name of the MongoDB collection for replaced data output.")
@click.option('-n', '--no_replaced_collection_name', required=True, help="Name of the MongoDB collection for non-replaced data output.")

def process_article_jsons_to_mongodb(db_name, input_collection_name, replaced_collection_name, no_replaced_collection_name):
    client = MongoClient('mongodb://localhost:27017/')
    db = client[db_name]
    input_collection = db[input_collection_name]
    replaced_collection = db[replaced_collection_name]
    no_replaced_collection = db[no_replaced_collection_name]

    for document in tqdm(input_collection.find(), desc="Processing documents"):
        # Assume 'passages' and 'relations_display' fields exist in the document
        text_content_no_replaced = "".join([passage["text"] for passage in document["passages"]])
        corrected_passages = extract_passages(document["passages"])
        text_content_replaced = "".join([passage["text"] for passage in corrected_passages])
        relationship_no_replaced = "; ".join([relation['name'] for relation in document['relations_display']])
        relationship_replaced = "; ".join(extract_relationships(document.get('relations', [])))

        # Insert processed data into the output collections
        replaced_collection.insert_one({
            'pmc_id': document['_id'],
            'relationships': relationship_replaced,
            'text': text_content_replaced
        })

        no_replaced_collection.insert_one({
            'pmc_id': document['_id'],
            'relationships': relationship_no_replaced,
            'text': text_content_no_replaced
        })

    logger.info(f'Processed and saved all entries to replaced collection: {replaced_collection_name}')
    logger.info(f'Processed and saved all entries to no replaced collection: {no_replaced_collection_name}')

    client.close()

def run_in_notebook(db_name, input_collection_name, replaced_collection_name, no_replaced_collection_name):
    process_article_jsons_to_mongodb.main(standalone_mode=False, args=[
        '--db_name', db_name,
        '--input_collection_name', input_collection_name,
        '--replaced_collection_name', replaced_collection_name,
        '--no_replaced_collection_name', no_replaced_collection_name
    ])

if __name__ == '__main__':
    process_article_jsons_to_mongodb()


"""
python article_data_extractor.py -i sickle_cell -c sickle_cell_raw_data -r replaced_sickle_cell -n no_replaced_sickle_cell
"""
