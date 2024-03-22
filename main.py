import click
import src.automaxo as automaxo
from automaxo import import_mesh_data, pmid_extractor, process_article_jsons_to_mongodb, process_ontogpt_articles, process_triplets_and_mesh

class AutoMaxoRunner:
    def __init__(self, disease_name, max_pmid_retrieve=10, max_articles_to_save=10):
        self.disease_name = disease_name
        self.max_pmid_retrieve = max_pmid_retrieve
        self.max_articles_to_save = max_articles_to_save
        self.base_data_path = f"data/{disease_name.replace(' ', '_')}/"
        self.json_files_dir = self.base_data_path + "pubtator3_json/"
        self.mesh_info_file_path = self.base_data_path + "selected_pmid_mesh_info.json"
        self.replaced_tsv_file_path = self.base_data_path + f"{disease_name.replace(' ', '_')}_mesh_replaced.tsv"
        self.no_replaced_tsv_file_path = self.base_data_path + f"{disease_name.replace(' ', '_')}_no_replaced.tsv"
        self.ontogpt_yaml_files_dir = self.base_data_path + "ontoGPT_yaml/"
        self.output_path = self.base_data_path + "post_ontoGPT.json"

    def run(self):
        print("Starting to get children MeSH IDs for target mesh IDs (Therapeutics and Diagnosis) ...")
        self.get_targeted_mesh_ids()
        
        print(f"Starting to retrieve mesh IDs related to treatment and diagnosis of {self.disease_name}...")
        self.retrieve_pubmed_ids()

        print(f"Starting to extract data from json files and apply PubTator 3 NER to one csv file ...")
        process_article_jsons_to_mongodb(
            db_name = "sickle_cell_test",
            input_collection_name = "sickle_cell_raw_data",
            replaced_collection_name = "replaced_sickle_cell",
            no_replaced_collection_name = "no_replaced_sickle_cell"          
            )

        print(f"Starting integration of OntoGPT article by article ...")
        process_ontogpt_articles(self.no_replaced_tsv_file_path, self.ontogpt_yaml_files_dir, template='maxo')

        print(f"Starting to Post Process OntoGPT results and saving the triplets found  ...")
        process_triplets_and_mesh(self.ontogpt_yaml_files_dir, self.mesh_info_file_path, self.output_path)
        print(f"The whole process is complete and the results are saved at {self.output_path}")

    def get_targeted_mesh_ids(self):
        input_file = "data/mesh_target_ids.tsv"
        mesh_list_path = "data/mesh_sets.tsv"
        import_mesh_data(input_file, mesh_list_path)

    def retrieve_pubmed_ids(self):
        pmid_extractor(
            disease_name=self.disease_name,
            mesh_list_path="data/mesh_sets.tsv",
            max_pmid_retrieve=self.max_pmid_retrieve,
            max_articles_to_save=self.max_articles_to_save,
            db_name = "sickle_cell_test",
            collection_name = "sickle_cell_raw_data",
            info_collection_name = "pmid_mesh_info"
        )

@click.command()
@click.option('--disease_name', prompt='Disease Name', help='The name of the disease to be processed.')
@click.option('--max_pmid_retrieve', default=500, help='Maximum number of PubMed IDs to retrieve.')
@click.option('--max_articles_to_save', default=100, help='Maximum number of articles to save.')
def main(disease_name, max_pmid_retrieve, max_articles_to_save):
    runner = AutoMaxoRunner(disease_name, max_pmid_retrieve, max_articles_to_save)
    runner.run()

if __name__ == "__main__":
    main()
