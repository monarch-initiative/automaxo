import json
import os
import argparse
import logging


logger = logging.basicConfig(filename='data_preprocessing.log',
                    level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


class ProcessJsonToTSV:

    def __init__(self,json_files_path,replaced_tsv_file_path, no_replaced_tsv_file_path ):

        self._json_files_path = json_files_path
        self._replaced_tsv_file_path = replaced_tsv_file_path
        self._no_replaced_tsv_file_path = no_replaced_tsv_file_path
        self.process_jsons_to_tsv(self._json_files_path, self._replaced_tsv_file_path, self._no_replaced_tsv_file_path)



    # Updated function based on the provided structure and logic for building new text with replacements
    def correct_replacements(self, passages):
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


    def process_jsons_to_tsv(self, _json_files_path, _replaced_tsv_file_path, _no_replaced_tsv_file_path):
        """
        Processes JSON files in the given directory, extracting PMC ID and text content,
        and saves them into a single TSV file with two columns: PMC ID and text.

        Parameters:
        - _json_files_path (str): The path to the directory containing JSON files.
        - _replaced_tsv_file_path (str): The path to the output TSV file where replacement occured .
        - _no_replaced_tsv_file_path (str): The path to the output TSV file where no replacement occured.
    
        """
        # Ensure the output directory exists
        output_directory = os.path.dirname(self._replaced_tsv_file_path)
        if output_directory:
            os.makedirs(output_directory, exist_ok=True)

        # Open the TSV files for writing
        with open(self._replaced_tsv_file_path, 'w', encoding='utf-8') as replaced_tsv_file, \
            open(self._no_replaced_tsv_file_path, 'w', encoding='utf-8') as no_replaced_tsv_file:

            # Iterate over all files in the given directory
            for filename in os.listdir(self._json_files_path):
                if filename.endswith(".json"):
                    json_file_path = os.path.join(self._json_files_path, filename)
                    
                    # Read the JSON file
                    with open(json_file_path, 'r', encoding='utf-8') as file:
                        data = json.load(file)
                    
                    # Concatenate all passage no replacement texts into one string
                    text_content_no_replaced =  "".join([passage["text"] for passage in data["passages"]])

               
                    # Apply Replacement 
                    corrected_passages = self.correct_replacements(data["passages"])

                    # Concatenate all passage replaced texts into one string
                    text_content_replaced = "".join([passage["text"] for passage in corrected_passages])

                    # Extract PMC ID from the filename (assuming PMC ID is the filename without extension)
                    pmc_id = os.path.splitext(filename)[0]
                    
                    # Write the PMC ID and text content to the TSV file
                    replaced_tsv_file.write(f"{pmc_id}\t{text_content_replaced}\n")
                    
                    # Write the PMC ID and text content to the TSV file
                    no_replaced_tsv_file.write(f"{pmc_id}\t{text_content_no_replaced}\n")

            logging.info(f'Processed and saved all entries to: {self._replaced_tsv_file_path}')
            logging.info(f'Unprocessed and saved all entries to: {self._no_replaced_tsv_file_path}')
        




if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process JSON files into TSV format.")

    parser.add_argument("-i", "--json_files_path", required=True, help="Path to the directory containing JSON files.")
    parser.add_argument("-r", "--replaced_tsv_file_path", required=True, help="Path to the output TSV file where replacement occurred.")
    parser.add_argument("-n", "--no_replaced_tsv_file_path", required=True, help="Path to the output TSV file where no replacement occurred.")
    
    args = parser.parse_args()
    
    ProcessJsonToTSV(args.json_files_path, args.replaced_tsv_file_path, args.no_replaced_tsv_file_path)

"""

# Sample way of running the code:
python data_preprocessing.py  -i ../dump/json_files -r ../dump/mesh_replaced.tsv -n ../dump/no_replaced.tsv

"""
