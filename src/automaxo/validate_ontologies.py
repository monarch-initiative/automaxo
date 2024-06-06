import json
import subprocess
import os
import argparse
from tqdm import tqdm

class OntologyValidation:
    def __init__(self, json_file_path, output_file_path):
        self.json_file_path = json_file_path
        self.output_file_path = output_file_path
        self.data_dir = '../../data/existing_ontologies'
        self.maxo_dict_path = os.path.join(self.data_dir, 'MAXO_terms.txt')
        self.hpo_dict_path = os.path.join(self.data_dir, 'HPO_terms.txt')
        self.mondo_dict_path = os.path.join(self.data_dir, 'MONDO_terms.txt')

    def run_command(self, command):
        try:
            subprocess.run(command, shell=True, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Command '{command}' failed with error: {e}")

    def load_dictionary(self, file_path):
        term_dict = {}
        with open(file_path, 'r') as file:
            for line in file:
                key, value = line.strip().split(' ! ', 1)
                term_dict[key.lower()] = value.lower()
        return term_dict

    def validate_and_update_json(self, maxo_dict, hpo_dict, mondo_dict):
        with open(self.json_file_path, 'r') as json_file:
            data = json.load(json_file)

        triplets_list = data.get('triplets', [])

        for item in tqdm(triplets_list, desc="Validating and updating JSON"):
            triplet = item.get('triplet', {})
            
            # Validate and update MAXO
            maxo_id = triplet.get('maxo')
            if maxo_id and maxo_id.lower() in maxo_dict:
                triplet['maxo_label'] = maxo_dict[maxo_id.lower()]
            
            # Validate and update HPO
            hpo_id = triplet.get('hpo')
            if hpo_id and hpo_id.lower() in hpo_dict:
                triplet['hpo_label'] = hpo_dict[hpo_id.lower()]
            
            # Validate and update MONDO
            mondo_id = triplet.get('mondo')
            if mondo_id and mondo_id.lower() in mondo_dict:
                triplet['mondo_label'] = mondo_dict[mondo_id.lower()]
        
        with open(self.output_file_path, 'w') as output_file:
            json.dump(data, output_file, indent=4)

    def run(self):
        # Ensure the data directory exists
        os.makedirs(self.data_dir, exist_ok=True)

        # Commands to generate ontology term files
        commands = [
            f"runoak -i sqlite:obo:maxo descendants -p i MAXO:0000001 > {self.maxo_dict_path}",
            f"runoak -i sqlite:obo:hp descendants -p i HP:0000118 > {self.hpo_dict_path}",
            f"runoak -i sqlite:obo:mondo descendants -p i MONDO:0000001 > {self.mondo_dict_path}"
        ]

        for command in tqdm(commands, desc="Running commands"):
            self.run_command(command)

        # Load dictionaries from the generated files
        maxo_dict = self.load_dictionary(self.maxo_dict_path)
        hpo_dict = self.load_dictionary(self.hpo_dict_path)
        mondo_dict = self.load_dictionary(self.mondo_dict_path)

        # Validate and update the JSON file
        self.validate_and_update_json(maxo_dict, hpo_dict, mondo_dict)

        print(f"Updated JSON file saved to {self.output_file_path}")

        # Remove the .txt files after loading them into dictionaries
        txt_files = [self.maxo_dict_path, self.hpo_dict_path, self.mondo_dict_path]
        for txt_file in txt_files:
            if os.path.exists(txt_file):
                os.remove(txt_file)

def run_in_notebook(json_file_path, output_file_path):
    updater = OntologyValidation(json_file_path, output_file_path)
    updater.run()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Update ontology labels in a JSON file.')
    parser.add_argument('json_file_path', type=str, help='Path to the input JSON file')
    parser.add_argument('output_file_path', type=str, help='Path to the output JSON file')
    args = parser.parse_args()

    run_in_notebook(args.json_file_path, args.output_file_path)
