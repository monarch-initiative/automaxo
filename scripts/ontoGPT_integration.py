import csv
import os
import argparse
from io import BytesIO
from ontogpt.engines.spires_engine import SPIRESEngine
from ontogpt.io.template_loader import get_template_details
from ontogpt.io.yaml_wrapper import dump_minimal_yaml
from ontogpt.cli import write_extraction

def process_article(pubmed_id: str, text: str, ke: SPIRESEngine, output_dir: str):
    """
    Process a single article and save the extracted results to a YAML file in the specified output directory.

    Args:
        pubmed_id (str): The PubMed ID of the article.
        text (str): The text content of the article.
        ke (SPIRESEngine): The knowledge extraction engine used to extract information from the text.
        output_dir (str): The directory where the extracted YAML file will be saved.

    """
    # Extract results from the text
    results = ke.extract_from_text(text=text)

    # Prepare the output stream and format
    output = BytesIO()
    output_format = "yaml"

    # Call the write_extraction function
    write_extraction(
        results=results,
        output=output,
        output_format=output_format,
        knowledge_engine=ke
    )

    # Save the output to a YAML file named after the PubMed ID in the specified output directory
    output_filename = os.path.join(output_dir, f"{pubmed_id}.yaml")
    with open(output_filename, "wb") as output_file:
        output.seek(0)
        output_file.write(output.getvalue())

def process_tsv_file(file_path: str, ke: SPIRESEngine, output_dir: str):
    """
    Read a .tsv file and process each article, saving the outputs in the specified directory.

    Args:
        file_path (str): The path to the .tsv file containing the articles.
        ke (SPIRESEngine): The knowledge extraction engine used to extract information from the articles.
        output_dir (str): The directory where the extracted YAML files will be saved.

    """
    with open(file_path, "r") as file:
        reader = csv.reader(file, delimiter="\t")
        for row in reader:
            pubmed_id, relationship, text = row
            process_article(pubmed_id, text, ke, output_dir)


def main():
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="Process .tsv file and extract results to YAML files.")
    parser.add_argument("input_file", help="Path to the input .tsv file")
    parser.add_argument("output_dir", help="Path to the output directory for YAML files")
    parser.add_argument("--template", default="maxo", help="Template to use for extraction (default: maxo)")
    args = parser.parse_args()

    # Initialize the SPIRES engine with the specified template
    ke = SPIRESEngine(
        template_details=get_template_details(template=args.template),
        model="gpt-4-0125-preview",
        model_source="openai",
    )

    # Create the output directory if it does not exist
    os.makedirs(args.output_dir, exist_ok=True)

    # Process the .tsv file
    process_tsv_file(args.input_file, ke, args.output_dir)


if __name__ == "__main__":
    main()


"""
python ontoGPT_integration.py path/to/input.tsv path/to/output/directory --template your_template


python ontoGPT_integration.py ../data/sickle_cell_no_replaced.tsv ../dump/ontoGPT_yaml_files/ontoGPT_sickle_cell


/Users/niyone/Desktop/maxo/automaxo/data/sickle_cell_no_replaced.tsv

/Users/niyone/Desktop/maxo/automaxo/dump/ontoGPT_yaml_files/ontoGPT_sickle_cell
"""