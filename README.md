
# Using LLM for MaXO Curation

This project aims to use Large Language Models (LLMs) for the curation of the Medical Action Ontology (MaXO). The following steps outline the setup and execution of the project.

## Setting Up the Virtual Environment And Running the whole project 

First, create and activate a virtual environment:

```bash
poetry install
poetry shell  
```

Add your openAI key:

```bash
runoak set-apikey -e openai <your openai api key>

```

To run the code for the whole project
```bash
python main.py
```


To visualize the results in HTML:

```bash
python -m http.server
```

Open in your browser and type 

```bash
http://localhost:8000/index.html

```bash
## Project Outline

For a detailed outline of the project, please refer to the [guideline document](https://docs.google.com/document/d/14KhrKmsPSCVISvcsCo_3I6n0FI5wjsgteeTe2nCVLGc/edit).

## Step 1: Data Extraction

Extract PubMed IDs (PMIDs) related to a specific topic.

- **Location:** `scripts/retrive_pmids.py`
- **Example:** `python retrive_pmids.py -d 'sickle cell' -o ../dump/json_files -m 200 -n 50`

## Step 2: Entity Standardization & Preprocessing

### Using Pubtator3 for Entity Standardization and Relationships 

- **Location:** `scripts/data_preprocessing.py`
- **Example:** `python data_preprocessing.py -i ../dump/json_files -r ../dump/mesh_replaced.tsv -n ../dump/no_replaced.tsv`


### Using POET to Map MESH to MONDO, HP, and MaXO

- **Location:** `scripts/poet_replacement.py`
- **Example:** `python poet_replacement.py -i ../dump/mesh_replaced.tsv -o ../dump/poet_replaced.tsv`



I have created sample text for three rare diseases:

- Sickle Cell
- Morphine
- Cystic Fibrosis

For each disease, I have saved 50 abstracts and titles. These are stored under the `/data` directory and are used throughout the various steps of the project:

The output TSV has 3 columns:
- Column 1: PubMed ID
- Column 2: Relationship
- Column 3: Title & Abstract

- `.._no_replaced.tsv`
Contains the raw text without any replacements.

| PubMed ID | Relationship                          | Title & Abstract                                                                 |
|-----------|----------------------------------------|----------------------------------------------------------------------------------|
| 38188902  | associate\|@DISEASE_Sarcoma\|@GENE_CIC | An Unusual Case of Hyperhemolysis Syndrome and Delayed Hemolytic Transfusion... |

- `.._mesh_replaced.tsv`
Contains text after applying Pubtator3 for Entity Standardization.

| PubMed ID | Relationship                        | Title & Abstract                                                              |
|-----------|--------------------------------------|-------------------------------------------------------------------------------|
| 38188902  | Association\|diseaseD012509\|ncbi23152 | An Unusual Case of diseaseD013577 and Delayed diseaseD006461 Transfusion... |

- `.._poet_replaced.tsv`
Contains text after replacing MESH terms with MONDO, HP, and MaXO terms.

| PubMed ID | Relationship                         | Title & Abstract                                                             |
|-----------|---------------------------------------|------------------------------------------------------------------------------|
| 38188902  | Association\|MONDO:0005089\|ncbi23152 | An Unusual Case of MONDO:0002254 and Delayed diseaseD006461 Transfusion... |

# OntoGPT Integration 

## How to update our own LinkML Schema with OntoGPT

### Way 1: Using OntoGPT Directory 
* `Pip install OntoGPT`
* Create a .yaml file 
* Generate a python file: ` gen-pydantic --pydantic-version 2 custom_schema.yaml > custom_schema.py`
* Find the right path for the virtual environment: ` pip show ontogpt `
* Then move both .yaml and .py to the virtual environment:  ` mv maxo_temp.py  /Users/niyone/Desktop/maxo/maxo_venv/lib/python3.9/site-packages/ontogpt/templates/ `
* Refer to the issue: https://github.com/monarch-initiative/ontogpt/issues/222

### Way 2: Quick way using maxo_schema in automaxo/notebooks

* Use the existing `notebooks/maxo_template.yaml`
* After you updated the current one in the repo, copy the version to the virtual environment (maxo_venv): ` cp maxo_template.yaml  /Users/niyone/Desktop/maxo/maxo_venv/lib/python3.9/site-packages/ontogpt/templates/ `
* Create a python file of the yaml template in Virtual Environment : `gen-pydantic --pydantic-version 2 /Users/niyone/Desktop/maxo/maxo_venv/lib/python3.9/site-packages/ontogpt/templates/maxo_template.yaml > /Users/niyone/Desktop/maxo/maxo_venv/lib/python3.9/site-packages/ontogpt/templates/maxo_template.py`
* Now call  maxo_template as a normal ontogpt template : `ontogpt -vvv extract -t maxo_template -i input.txt`




