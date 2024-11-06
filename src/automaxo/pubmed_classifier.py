import numpy as np
import pandas as pd
import torch
import os
import csv
import argparse
from tqdm.auto import tqdm
from transformers import AutoModelForSequenceClassification, AutoTokenizer


class PubMedClassifier:
    """
    A class to handle loading a fine-tuned model and classifying text for relevance.

    Attributes:
    -----------
    model : AutoModelForSequenceClassification
        The model loaded from a pretrained directory.
    tokenizer : AutoTokenizer
        The tokenizer loaded from the pretrained directory.
    device : torch.device
        The device (CPU or GPU) where the model will run.

    Methods:
    --------
    classify_text(text: str) -> str:
        Classifies a given text as 'Relevant' or 'Not Relevant'.
    process_file(file_path: str) -> pd.DataFrame:
        Reads a TSV or CSV file and returns a DataFrame containing only relevant rows.
    """

    def __init__(self, model_dir: str):
        """
        Initializes the classifier with the fine-tuned model and tokenizer from the specified directory.

        Args:
        -----
        model_dir : str
            The directory where the model and tokenizer are saved.
        """
        self.model = AutoModelForSequenceClassification.from_pretrained(model_dir)
        self.tokenizer = AutoTokenizer.from_pretrained(model_dir)
        self.device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
        self.model.to(self.device)

    def classify_text(self, text: str) -> str:
        """
        Classifies the input text as 'Relevant' or 'Not Relevant'.

        Args:
        -----
        text : str
            The text to be classified.

        Returns:
        --------
        str
            'Relevant' if classified as relevant, otherwise 'Not Relevant'.
        """
        # Tokenize the input text
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=512)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        # Put the model in evaluation mode and perform classification
        self.model.eval()
        with torch.no_grad():
            outputs = self.model(**inputs)
            prediction = outputs.logits.argmax(dim=-1).item()

        return "Relevant" if prediction == 1 else "Not Relevant"

    def process_file(self, file_path: str) -> pd.DataFrame:
        """
        Reads a CSV or TSV file and processes each row to classify its relevance, returning only relevant rows.

        Args:
        -----
        file_path : str
            The path to the file to be processed (TSV or CSV format).

        Returns:
        --------
        pd.DataFrame
            A DataFrame containing only relevant rows.
        """
        relevant_rows = []
        df = pd.read_csv(file_path, sep='\t' if file_path.endswith('.tsv') else ',')

        # Ensure required columns are present
        if 'PMID' not in df.columns or 'Title' not in df.columns or 'Abstract' not in df.columns:
            raise ValueError("The file must contain 'PMID', 'Title', and 'Abstract' columns.")

        # Loop through the file and classify each text
        for _, row in tqdm(df.iterrows(), total=len(df), desc="Classifying rows"):
            text = f"{row['Title']} {row['Abstract']}"
            if self.classify_text(text) == "Relevant":
                relevant_rows.append(row)

        # Return a DataFrame containing only relevant rows
        return pd.DataFrame(relevant_rows)


def save_relevant_articles(file_path: str, output_file: str, classifier: PubMedClassifier):
    """
    Processes a TSV/CSV file, filters relevant articles, and saves them into a TSV file.

    Args:
    -----
    file_path : str
        The path to the TSV/CSV file containing the articles.
    output_file : str
        The path to the TSV file where relevant articles will be saved.
    classifier : PubMedClassifier
        An instance of PubMedClassifier used to classify the articles.
    """
    relevant_df = classifier.process_file(file_path)

    # Save the filtered relevant articles to a TSV file
    relevant_df.to_csv(output_file, sep='\t', index=False)
    print(f"Relevant articles saved to {output_file}")


def main(file_path=None, model_dir=None, output_file=None):
    """
    Main function that can be used for both terminal and Python script calls.

    Args:
    -----
    file_path : str
        Path to the input TSV/CSV file.
    model_dir : str
        Path to the fine-tuned model directory.
    output_file : str
        Path to the output TSV file where relevant articles will be saved.
    """

    # If arguments are not passed, get them from argparse (for terminal usage)
    if file_path is None or model_dir is None or output_file is None:
        parser = argparse.ArgumentParser(description="Filter relevant articles using a fine-tuned PubMedBERT model.")
        parser.add_argument('-i','--file_path', type=str, required=True, help="Path to the input TSV/CSV file.")
        parser.add_argument('-m','--model_dir', type=str, required=True, help="Path to the directory where the model and tokenizer are saved.")
        parser.add_argument('-o','--output_file', type=str, required=True, help="Path to the output TSV file where relevant articles will be saved.")
        
        args = parser.parse_args()
        file_path = args.file_path
        model_dir = args.model_dir
        output_file = args.output_file

    # Initialize the classifier and process the file
    classifier = PubMedClassifier(model_dir)
    save_relevant_articles(file_path, output_file, classifier)


# Entry point when running the script from the terminal
if __name__ == "__main__":
    main()

# python pubmed_classifier.py -i input_articles.tsv -m ./finetuned_pubmedbert -o ./output
