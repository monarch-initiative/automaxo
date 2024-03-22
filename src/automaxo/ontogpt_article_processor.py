import os
import click
from ontogpt.engines.spires_engine import SPIRESEngine
from ontogpt.io.template_loader import get_template_details
from ontogpt.cli import write_extraction
from tqdm import tqdm
from pymongo import MongoClient
import yaml 



def process_article(pubmed_id: str, text: str, ke: SPIRESEngine, output_collection, file_name: str):
    # Extract results from the text
    results = ke.extract_from_text(text=text)

    # Convert results to YAML format
    yaml_results = yaml.dump(results)

    # Insert the results into the MongoDB collection
    output_collection.insert_one({
        "pubmed_id": pubmed_id,
        "results": yaml_results,
        "file_name": file_name  
    })

@click.command()
@click.option('-d', '--db_name', required=True, help="Name of the MongoDB database.")
@click.option('-i','--input_collection_name', required=True, help="Name of the MongoDB collection for input.")
@click.option('-o', '--output_collection_name', required=True, help="Name of the MongoDB collection for output.")
@click.option('-t', '--template', default='maxo', help='Template to use for extraction (default: maxo)')
def main(db_name, input_collection_name, output_collection_name, template):
    # Initialize the SPIRES engine with the specified template
    ke = SPIRESEngine(
        template_details=get_template_details(template=template),
        model="gpt-4-0125-preview",
        model_source="openai",
    )

    client = MongoClient('mongodb://localhost:27017/')
    db = client[db_name]
    input_collection = db[input_collection_name]
    output_collection = db[output_collection_name]


    for document in tqdm(input_collection.find(), desc="Processing documents"):
        pubmed_id = document["pmc_id"]
        text = document["text"]
        file_name = f"{pubmed_id}.yaml"

        # Check if the PubMed ID already exists in the output collection
        if output_collection.find_one({"pubmed_id": pubmed_id}):
            print(f"PubMed ID {pubmed_id} already exists in the output collection. Skipping...")
            continue  # Skip processing this document

        # Process the document if the PubMed ID is not in the output collection
        process_article(pubmed_id, text, ke, output_collection, file_name)


    client.close()

def run_in_notebook(db_name, input_collection_name, output_collection_name, template='maxo'):
    main.main(standalone_mode=False, args=[
        '--db_name', db_name,
        '--input_collection_name', input_collection_name,
        '--output_collection_name', output_collection_name,
        '--template', template
    ])

if __name__ == '__main__':
    main()

"""
python ontogpt_article_processor.py -d sickle_cell -i no_replaced_sickle_cell -o ontoGPT_sickle_cell
"""