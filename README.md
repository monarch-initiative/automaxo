
# Using LLM for MaXO Curation

This project aims to use Large Language Models (LLMs) for the curation of the Medical Action Ontology (MaXO). The following steps outline the setup and execution of the project.

## Setting Up the Virtual Environment

First, create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

Then, install the required dependencies:

```bash
pip install -r requirements.txt
```

## Project Outline

For a detailed outline of the project, please refer to the [guideline document](https://docs.google.com/document/d/14KhrKmsPSCVISvcsCo_3I6n0FI5wjsgteeTe2nCVLGc/edit).

## Step 1: Data Extraction

Extract PubMed IDs (PMIDs) related to a specific topic.

- **Location:** `scripts/retrive_pmids.py`
- **Example:** `python retrive_pmids.py -d 'sickle cell' -o ../dump/json_files -m 200 -n 50`

## Step 2: Entity Standardization & Preprocessing

### Using Pubtator3 for Entity Standardization

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

- `.._mesh_replaced.tsv`: Contains text after applying Pubtator3 for Entity Standardization.
- `.._no_replaced.tsv`: Contains the raw text without any replacements.
- `.._poet_replaced.tsv`: Contains text after replacing MESH terms with MONDO, HP, and MaXO terms.
