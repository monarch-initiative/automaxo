# Data

Each run of AutoMAxO produces a data collection within the `data` directory of the project.

This collection will be named for the target disease, and will contain the following:

* `{disease_name}_no_replaced.tsv`: a table of the articles processed in the run, including their PubMed IDs, titles, and abstracts, with no ID replacement.

* `selected_pmid_mesh_info.json`: a JSON representation of the MeSH terms corresponding to each PubMed entry, as provided by PubMed itself.

* `detailed_post_ontoGPT.json`: a JSON representation of the annotations extracted from each input text by OntoGPT, with identifiers.

* `final_automaxo_results.json`: a JSON representation of the annotations extracted from each input, after AutoMAxO processing.

* `pubtator3_json`: a directory of JSON representations of each PubMed entry and its corresponding annotations from PubTator.

* `ontoGPT_yaml`: a directory of raw YAML output for each PubMed entry from OntoGPT. This includes the full input text and raw, ungrounded LLM responses.
