# AutoMAxO Tutorial

Welcome to the AutoMAxO tutorial. This guide will walk you through running the AutoMAxO project step by step.

### Note:
There are two options to run the whole AutoMAxO pipeline depending on your usage:
1. You can run the entire project with just one command if you would like to retrieve a certain number of articles that discuss therapeutics and extract medical actions.

```shell
python main.py --disease_name "YourDiseaseName" --max_articles_to_save 100
```
Replace "YourDiseaseName" with the name of the disease you want to process and adjust `100` to the desired number of articles to save.

2. You can run each file separately to easily modify and integrate AutoMAxO into different applications to accomplish various tasks. In this tutorial, we will be using "sickle cell" as a sample disease, but you can change it to any name you prefer. Follow the step-by-step instructions below:

## Step 1: Extract MeSH Sets from Target MeSH IDs

The script, `mesh_importer.py`, reads a list of targeted MeSH IDs and their labels to create a formatted file with MeSH sets required for the AutoMAxO project.

| Option       | Meaning                                          |
|--------------|--------------------------------------------------|
| --input-file | Path to the .tsv file containing MeSH target IDs |
| --output-file| Path to the output .tsv file with MeSH sets      |

For example:

```shell
python mesh_importer.py --input-file path/to/mesh_target_ids.tsv --output-file path/to/mesh_sets.tsv
```
The default format for `mesh_target_ids` in the project is as follows:

| mesh.id | label        |
|---------|--------------|
| D013812 | Therapeutics |

Sample output for `mesh_sets`:

| label        | mesh.id | mesh set                             |
|--------------|---------|--------------------------------------|
| Therapeutics | D013812 | 061645;D000075162;D000161;D000203;D019050 |

## Step 2: Retrieve MeSH IDs

The script, `pubmed_article_fetcher.py`,start by retrieving raw data and MeSH IDs related to the treatment of your specified disease. In this stage, the script first checks whether there are already existing articles in the directory to avoid duplicate extraction. It ensures that the new articles being extracted are not the same as the ones already existing in the directory, and attempts to extract up to the maximum number specified by the user.

| Option | Meaning                                                                   |
|--------|---------------------------------------------------------------------------|
| -d     | Disease name                                                              |
| -m     | Path to the .tsv file with MeSH sets created in Step 1                    |
| -o     | Directory where retrieved articles will be saved in the form of .json files |
| -j     | Path to the .json file to save MeSH IDs related to retrieved articles     |
| -n     | Maximum number of articles to retrieve                                    |

For example:

```shell
python pubmed_article_fetcher.py -d "sickle cell" -m ../../data/mesh_sets.tsv -o ../../data/sickle_cell/pubtator3_json/ -j ../../data/sickle_cell/selected_pmid_mesh_info.json -n 2
```

Note:
* The disease name is not case-sensitive.
* The maximum number of articles will include articles both about a specific disease and having at least one of the MeSH IDs in the MeSH sets from Step 1, meaning articles about therapeutics of a specific disease, for example, in our use case.

## Step 3: Pre-process Extracted Data from JSON Files

The script, `article_data_extractor.py`, extracts data from JSON files and saves the text where each row represents the title and abstract of an article.

| Option | Meaning                                    |
|--------|--------------------------------------------|
| -i     | Directory containing JSON files produced in Step 2 |
| -n     | Path to the .tsv file for pre-processed text data  |

For example:

```shell
python article_data_extractor.py -i ../../data/sickle_cell/pubtator3_json/ -n ../../data/sickle_cell/sickle_cell_no_replaced.tsv
```

## Step 4: Integrate OntoGPT

The script, `ontogpt_article_processor.py`, processes the text data from the pre-processed .tsv file using OntoGPT. Each row in the .tsv file is treated as an input text for OntoGPT. For more information about OntoGPT, please refer to <a href="https://github.com/monarch-initiative/ontogpt" target="_blank">this repo</a>.


| Option     | Meaning                                                            |
|------------|--------------------------------------------------------------------|
| -i         | Path to the .tsv file for pre-processed text produced in Step 3    |
| -o         | Directory containing YAML files produced by LLMs (OntoGPT)         |
| -template  | Name of the template for OntoGPT (default = 'maxo')                |

For example:

```shell
python ontogpt_article_processor.py -i ../../data/sickle_cell/sickle_cell_no_replaced.tsv -o ../../data/sickle_cell/ontoGPT_yaml/
```

## Step 5: Post-process LLM Results

The script, `ontology_validation.py`, 
Post-process LLM results from separate YAML files into a single JSON file. This includes further grounding of terms to the existing ontologies and ranking extracted triplets by frequency of appearance.

| Option | Meaning                                                                                   |
|--------|-------------------------------------------------------------------------------------------|
| -i     | Directory containing YAML files produced in Step 4                                        |
| -s     | Path to the .json file to save MeSH IDs related to retrieved articles produced in Step 2  |
| -n     | Path to the .tsv file for pre-processed text produced in Step 3                           |
| -o     | Path to the .json file to save post-processed LLM results in one file                     |

For example:

```shell
python triplet_ranking_and_mesh_combiner.py -i ../../data/sickle_cell/ontoGPT_yaml/ -s ../../data/sickle_cell/selected_pmid_mesh_info.json -n ../../data/sickle_cell/sickle_cell_no_replaced.tsv -o ../../data/sickle_cell/detailed_post_ontoGPT.json
```

## Step 6: Validate Annotations

The script, `ontology_validation.py`, updates ontology labels in a JSON file by validating and augmenting MAXO, HPO, and MONDO IDs with their corresponding labels. It processes the JSON data, generates ontology term files using `runoak`, and integrates these terms into the JSON file to enhance the dataset with accurate ontology information.


| Option              | Meaning                                                                                   |
|---------------------|-------------------------------------------------------------------------------------------|
| -json_file_path     | Path to the .json file of post-processed LLM results produced in Step 5                   |
| -output_file_path   | Path to the .json file, final result of validated ontologies produced by automaxo         |

For example:

```shell
python ontology_validation.py ../../data/sickle_cell/detailed_post_ontoGPT.json ../../data/sickle_cell/final_automaxo_results.json
```

# Running the Script

You can run the script using the following command:

```shell
python main.py --disease_name "YourDiseaseName" --max_articles_to_save 100
```
Replace "YourDiseaseName" with the name of the disease you want to process and adjust `100` to the desired number of articles to save.