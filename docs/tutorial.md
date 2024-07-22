# AutoMAxO Tutorial

Welcome to the AutoMAxO tutorial. This guide will walk you through running the AutoMAxO project, step by step.

## Step 1: Retrieve MeSH IDs

Start by retrieving the MeSH IDs related to the treatment and diagnosis of your specified disease. 

## Step 2: Extract Data from JSON Files

Extract data from the JSON files and save the text where each row represents the title and abstract of an article.

## Step 3: Integrate OntoGPT

Integrate OntoGPT article by article to process the text data.

## Step 4: Integrate OntoGPT

Post Process OntoGPT Results

## Step 5: Validate Annotations

Validate the annotations to ensure the right labels are used.


# Running the Script

You can run the script using the following command:

```shell
python main.py --disease_name "YourDiseaseName" --max_articles_to_save 100
```
Replace "YourDiseaseName" with the name of the disease you want to process and adjust 100 to the desired number of articles to save.
