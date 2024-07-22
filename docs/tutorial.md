# AutoMAxO Tutorial

Welcome to the AutoMAxO tutorial. This guide will walk you through running the AutoMAxO project, step by step.

### Note:
There are two options to run the whole AutoMAxO pipeline depending of the usage: 
1. You can run the whole project by just one command if you would like to retrieve certain number of articles that talks about therapeutics and extract medical actions.

```shell
python main.py --disease_name "YourDiseaseName" --max_articles_to_save 100
```
Replace "YourDiseaseName" with the name of the disease you want to process and adjust 100 to the desired number of articles to save.

2. You can run eah file separately to easily modify and integrate AutoMAxO to differnt applications to accomplish differnt tasks. Follow the following step by step:  


## Step 1: Extract MeSH Sets from Target MeSH IDs

Reads a list of targeted mesh ids and their labels and creates a formated file with mesh sets required for AutoMAxO project

```shell
python mesh_importer.py --input-file path/to/mesh_target_ids.tsv --output-file path/to/mesh_sets.tsv
```

The default of the project for mesh_target_ids, following the right formart is this:

| mesh.id | label          |
|--------|-----------------|
| D013812 | Therapeutics   |

Sample of the output:  mesh_sets :

| label        | mesh.id         | mesh set                                 |
|--------------|-----------------|------------------------------------------|
| Therapeutics | D013812         |061645;D000075162;D000161;D000203;D019050 |

## Step 2: Retrieve MeSH IDs

Start by retrieving raw data and MeSH IDs related to the treatment of your specified disease. On this stage the scrip first checks whether there are already existing articles in the directory, and to avoid duplicate extraction, it ensures that the new articles being extracted are not the same as the ones already exisitng in the directory, and try to extract up to the maximum as the user mentioned. 



| option | meaning                                                                   |
|--------|---------------------------------------------------------------------------|
| _-d_   | a disease Name                                                            |
| _-m_   | a path for _.tsv_ file  with mesh sets created in step 1                  |
| _-o_   | directory where retreived articles will be saved in form of _.json_ files |
| _-j_   | a path for _.json_ file to save MeSH ids related to retrieved articles    |
| _-n_   | maximum articles to be retrieved                                          |


for example:
```shell
python pubmed_article_fetcher.py -d "sickle cell" -m ../../data/mesh_sets.tsv -o ../../data/sickle_cell/pubtator3_json/  -j ../../data/sickle_cell/selected_pmid_mesh_info.json -n 2

```
Note:  
* a disease name is not case sensitive
* The maximum articles, will be the articles both abuout  a specific disease and has at least one one the MeSH Ids in the mesh sets from step 1, means articles about a theraputics of a specific disease for our use case for example. 


## Step 3: Pre Process Extract Data from JSON Files

Extract data from the JSON files and save the text where each row represents the title and abstract of an article.

| option | meaning                                                                   |
|--------|---------------------------------------------------------------------------|
| _-i_   | directory containing json files produced in step 2                        |
| _-n_   | a path for _.tsv_ file pre processed text data                            |


for example:
```shell
python article_data_extractor.py -i ../../data/sickle_cell/pubtator3_json/ -n  ../../data/sickle_cell/sickle_cell_no_replaced.tsv 

```

## Step 4: Integrate OntoGPT

Integrate OntoGPT article by article to process the text data. This step each row represents each articles extracted, each row is treated as an input text for ontoGPT. 


| option        | meaning                                                                   |
|---------------|---------------------------------------------------------------------------|
| _-i_          | a path for _.tsv_ file pre processed text produced in step 3              |
| _-o_          | directory containing yaml files produced by LLMs (ontoGPT)                |
| _-template_   | name of the tamplate to ontoGPT (default = 'maxo')                        |



for example:
```shell
python ontogpt_article_processor.py -i ../../data/sickle_cell/sickle_cell_no_replaced.tsv -o ../../data/sickle_cell/ontoGPT_yaml/

```

## Step 5: Post Process LLMs Results 

Post process LLMs results for separate yamal files to single json file, including further grounding of terms to the existing ontologies, and ranking extracted triplets by frequency of appearance. 


| option  | meaning                                                                                    |
|---------|--------------------------------------------------------------------------------------------|
| _-i_    | directory containing yaml files produced in step 4                                         |
| _-s_    | a path for _.json_ file to save MeSH ids related to retrieved articles produced in step 2  |
| _-n     | a path for _.tsv_ file pre processed text produced in step 3                               |
| _-o     | a path to  _.json_ file to save post processed LLM results in one file                     |



for example:
```shell
python triplet_ranking_and_mesh_combiner.py -i ../../data/sickle_cell/ontoGPT_yaml/ -s ../../data/sickle_cell/selected_pmid_mesh_info.json -n ../../data/sickle_cell/sickle_cell_no_replaced.tsv -o ../../data/sickle_cell/detailed_post_ontoGPT.json


```

## Step 6: Validate Annotations

Validate the annotations to ensure the right labels are used.


# Running the Script

You can run the script using the following command:

```shell
python main.py --disease_name "YourDiseaseName" --max_articles_to_save 100
```
Replace "YourDiseaseName" with the name of the disease you want to process and adjust 100 to the desired number of articles to save.
