import click
import src.automaxo as automaxo
from automaxo import import_mesh_data, pmid_extractor, process_article_jsons_to_tsv, text_filter, process_ontogpt_articles, process_triplets_and_mesh, ontology_validation

class AutoMaxoRunner:
    def __init__(self, disease_name, max_articles_to_save):
        self.disease_name = disease_name
        self.max_articles_to_save = max_articles_to_save
        self.base_data_path = f"data/{disease_name.replace(' ', '_')}/"
        self.json_files_dir = self.base_data_path + "pubtator3_json/"
        self.mesh_info_file_path = self.base_data_path + "selected_pmid_mesh_info.json"
        self.finetuned_pubmed_bert_model_dir = "ml_optimisation/finetuned_pubmedbert/"
        self.no_replaced_tsv_file_path = self.base_data_path + f"{disease_name.replace(' ', '_')}_no_replaced.tsv"
        self.filtered_tsv_file_path = self.base_data_path + f"{disease_name.replace(' ', '_')}_filtered.tsv"
        self.poet_replaced_tsv_file_path = self.base_data_path + f"{disease_name.replace(' ', '_')}_poet_replaced.tsv"
        self.ontogpt_yaml_files_dir = self.base_data_path + "ontoGPT_yaml/"
        self.output_json_path = self.base_data_path + "detailed_post_ontoGPT.json"
        self.final_automaxo_results_path = self.base_data_path + "final_automaxo_results.json"


    def run(self):       
        print(f"Starting to retrieve raw data and  mesh IDs related to treatment of {self.disease_name}...")
        pmid_extractor(
            disease_name=self.disease_name,
            mesh_list_path="data/mesh_sets.tsv",
            output_dir=self.json_files_dir,
            json_file_path=self.mesh_info_file_path,
            max_articles_to_save=self.max_articles_to_save
        )

        print(f"Starting to extract data from json files and save the text where each row is title and abstract ...")
        process_article_jsons_to_tsv(
            self.json_files_dir,
            self.no_replaced_tsv_file_path
            )
        
        print(f"Starting to filter relevant articles using fine-tuned pubmed_bert each row is title and abstract ...")
        text_filter(
            self.no_replaced_tsv_file_path,
            self.finetuned_pubmed_bert_model_dir,
            self.filtered_tsv_file_path
            )

        print(f"Starting integration of OntoGPT article by article ...")
        process_ontogpt_articles(
            self.filtered_tsv_file_path, 
            self.ontogpt_yaml_files_dir, 
            template='maxo'
            )

        print(f"Starting to Post Process OntoGPT results and saving the triplets found  ...")
        process_triplets_and_mesh(
            self.ontogpt_yaml_files_dir, 
            self.mesh_info_file_path, 
            self.no_replaced_tsv_file_path, 
            self.output_json_path 
            )
        
        print(f"Starting to validate annotations to ensure right labels  ...")
        ontology_validation(
            self.output_json_path, 
            self.final_automaxo_results_path 
            )

        print(f"The whole process is complete detailed results are saved in a JSON file at {self.final_automaxo_results_path} ")


@click.command()
@click.option('--disease_name', prompt='Disease Name', help='The name of the disease to be processed.')
@click.option('--max_articles_to_save', prompt='Max Articles To Save', help='Maximum number of articles to save.')
def main(disease_name, max_articles_to_save):
    disease_name = disease_name.lower()  # Convert the disease name to lowercase
    runner = AutoMaxoRunner(disease_name, max_articles_to_save)
    runner.run()

if __name__ == "__main__":
    main()
