import csv
import os
from io import BytesIO
import click
from ontogpt.engines.spires_engine import SPIRESEngine
from ontogpt.io.template_loader import get_template_details
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


@click.command()
@click.argument('input_file', type=click.Path(exists=True)) # help="Path to the input .tsv file"
@click.argument('output_dir', type=click.Path()) # help="Path to the output directory for YAML files"
@click.option('--template', default='maxo') # help='Template to use for extraction (default: maxo)'
def main(input_file, output_dir, template):
    # Initialize the SPIRES engine with the specified template
    ke = SPIRESEngine(
        template_details=get_template_details(template=template),
        model="gpt-4-0125-preview",
        model_source="openai",
    )

    # Create the output directory if it does not exist
    os.makedirs(output_dir, exist_ok=True)

    # Process the .tsv file
    process_tsv_file(input_file, ke, output_dir)

if __name__ == '__main__':
    main()


"""
python ontogpt_article_processor.py path/to/input.tsv path/to/output/directory --template maxo

"""