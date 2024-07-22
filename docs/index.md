# AutoMAxO

## Using LLM for MaXO Curation

This project aims to use Large Language Models (LLMs) for the curation of the Medical Action Ontology (MaXO).

The following steps outline the setup and execution of the project.

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
