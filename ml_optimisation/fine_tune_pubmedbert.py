import os
import torch
import logging
import argparse
import pandas as pd
from transformers import AutoModelForSequenceClassification, AutoTokenizer, AdamW, get_scheduler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from torch.utils.data import DataLoader, Dataset
from tqdm.auto import tqdm

# Set up logging
logging.basicConfig(
    filename='pubmed_bert_trainer.log',  # Log file name
    filemode='w',                        # Overwrite the log file for each run
    format='%(asctime)s - %(levelname)s - %(message)s',  # Log format
    level=logging.INFO                   # Log all levels INFO and above
)

class PubMedBertTrainer:
    """
    A class to fine-tune PubMedBERT on a dataset of abstracts and handle model training, evaluation, and saving.

    Attributes:
    -----------
    model_name : str
        The HuggingFace model identifier for the pretrained model.
    batch_size : int
        The batch size for training and evaluation data loaders.
    lr : float
        The learning rate for the optimizer.
    num_epochs : int
        The number of epochs to train the model.
    device : torch.device
        The device (CPU or CUDA) where the model will be trained.

    Methods:
    --------
    load_data(positive_path, negative_path):
        Loads the positive and negative abstracts and prepares the dataset.
    tokenize_data(texts, labels):
        Tokenizes input texts using the tokenizer from the pre-trained model.
    split_data(texts, labels):
        Splits the data into training and validation sets.
    prepare_dataloaders(train_texts, val_texts, train_labels, val_labels):
        Prepares PyTorch DataLoader objects for training and validation datasets.
    train(train_loader):
        Fine-tunes the model on the training dataset.
    evaluate(val_loader):
        Evaluates the model on the validation dataset and logs performance metrics.
    save_model(save_directory):
        Saves the fine-tuned model and tokenizer to the specified directory.
    """

    def __init__(self, model_name, batch_size=8, lr=5e-5, num_epochs=3):
        """
        Constructs all the necessary attributes for the PubMedBertTrainer object.

        Parameters:
        -----------
        model_name : str
            The HuggingFace model identifier for the pretrained model.
        batch_size : int
            The batch size for training and evaluation data loaders.
        lr : float
            The learning rate for the optimizer.
        num_epochs : int
            The number of epochs to train the model.
        """
        self.model_name = model_name
        self.batch_size = batch_size
        self.lr = lr
        self.num_epochs = num_epochs
        self.device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")

        # Load the model and tokenizer
        self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name, num_labels=2).to(self.device)
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        logging.info(f'Model and tokenizer loaded from {self.model_name}')

    def load_data(self, positive_path, negative_path):
        """
        Loads and preprocesses positive and negative abstracts, assigning labels and concatenating them.

        Parameters:
        -----------
        positive_path : str
            The file path for the positive abstracts (TSV format).
        negative_path : str
            The file path for the negative abstracts (TSV format).

        Returns:
        --------
        texts : list
            A list of all abstract texts.
        labels : list
            A list of labels corresponding to the abstracts (1 for positive, 0 for negative).
        """
        positive_abstract = pd.read_csv(positive_path, sep='\t').dropna()
        negative_abstract = pd.read_csv(negative_path, sep='\t').dropna()

        # Label the data
        positive_abstract['category'] = 1
        negative_abstract['category'] = 0
        all_abstract = pd.concat([positive_abstract, negative_abstract])

        texts = all_abstract['Text'].tolist()
        labels = all_abstract['category'].tolist()

        logging.info(f'Data loaded: {len(texts)} texts')
        return texts, labels

    def tokenize_data(self, texts, labels):
        """
        Tokenizes input texts using the tokenizer from the pre-trained model.

        Parameters:
        -----------
        texts : list
            A list of abstract texts to be tokenized.
        labels : list
            A list of labels corresponding to the texts.

        Returns:
        --------
        PubMedDataset object
            A PyTorch Dataset with tokenized inputs and labels.
        """
        encodings = self.tokenizer(texts, truncation=True, padding=True, max_length=512)
        logging.info(f'Data tokenized with max_length 512')
        return PubMedDataset(encodings, labels)

    def split_data(self, texts, labels):
        """
        Splits the dataset into training and validation sets.

        Parameters:
        -----------
        texts : list
            A list of abstract texts.
        labels : list
            A list of labels corresponding to the abstracts.

        Returns:
        --------
        tuple
            A tuple containing the training and validation texts and labels.
        """
        train_texts, val_texts, train_labels, val_labels = train_test_split(texts, labels, test_size=0.2)
        logging.info(f'Data split into train (80%) and validation (20%)')
        return train_texts, val_texts, train_labels, val_labels

    def prepare_dataloaders(self, train_texts, val_texts, train_labels, val_labels):
        """
        Prepares PyTorch DataLoader objects for the training and validation datasets.

        Parameters:
        -----------
        train_texts : list
            Training dataset texts.
        val_texts : list
            Validation dataset texts.
        train_labels : list
            Training dataset labels.
        val_labels : list
            Validation dataset labels.

        Returns:
        --------
        tuple
            A tuple containing the DataLoader objects for training and validation datasets.
        """
        train_dataset = self.tokenize_data(train_texts, train_labels)
        val_dataset = self.tokenize_data(val_texts, val_labels)

        train_loader = DataLoader(train_dataset, batch_size=self.batch_size, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=self.batch_size, shuffle=False)

        logging.info(f'DataLoader prepared: Batch size {self.batch_size}')
        return train_loader, val_loader

    def train(self, train_loader):
        """
        Fine-tunes the model on the training dataset.

        Parameters:
        -----------
        train_loader : DataLoader
            The DataLoader for the training dataset.
        """
        optimizer = AdamW(self.model.parameters(), lr=self.lr)
        num_training_steps = self.num_epochs * len(train_loader)
        lr_scheduler = get_scheduler("linear", optimizer=optimizer, num_warmup_steps=0, num_training_steps=num_training_steps)

        progress_bar = tqdm(range(num_training_steps))
        self.model.train()
        logging.info(f'Training started for {self.num_epochs} epochs')

        for epoch in range(self.num_epochs):
            for batch in train_loader:
                batch = {k: v.to(self.device) for k, v in batch.items()}
                outputs = self.model(**batch)
                loss = outputs.loss
                loss.backward()

                optimizer.step()
                lr_scheduler.step()
                optimizer.zero_grad()
                progress_bar.update(1)

            logging.info(f'Epoch {epoch + 1} completed')

    def evaluate(self, val_loader):
        """
        Evaluates the model on the validation dataset and logs performance metrics.

        Parameters:
        -----------
        val_loader : DataLoader
            The DataLoader for the validation dataset.
        """
        self.model.eval()
        all_predictions = []
        all_labels = []

        for batch in val_loader:
            batch = {k: v.to(self.device) for k, v in batch.items()}
            with torch.no_grad():
                outputs = self.model(**batch)
                predictions = outputs.logits.argmax(dim=-1)
                all_predictions.extend(predictions.cpu().numpy())
                all_labels.extend(batch['labels'].cpu().numpy())

        # Calculate metrics
        accuracy = accuracy_score(all_labels, all_predictions)
        f1 = f1_score(all_labels, all_predictions, average='weighted')
        precision = precision_score(all_labels, all_predictions, average='weighted')
        recall = recall_score(all_labels, all_predictions, average='weighted')

        logging.info(f'Validation Accuracy: {accuracy}')
        logging.info(f'Validation F1 Score: {f1}')
        logging.info(f'Validation Precision: {precision}')
        logging.info(f'Validation Recall: {recall}')

    def save_model(self, save_directory):
        """
        Saves the fine-tuned model and tokenizer to the specified directory.

        Parameters:
        -----------
        save_directory : str
            The directory where the model and tokenizer will be saved.
        """
        if not os.path.exists(save_directory):
            os.makedirs(save_directory)
        self.model.save_pretrained(save_directory)
        self.tokenizer.save_pretrained(save_directory)
        logging.info(f'Model and tokenizer saved to {save_directory}')


class PubMedDataset(Dataset):
    """
    A PyTorch Dataset class to handle tokenized data and labels.

    Attributes:
    -----------
    encodings : dict
        A dictionary of tokenized input data (input_ids, attention_mask, etc.).
    labels : list
        A list of labels corresponding to the input data.

    Methods:
    --------
    __getitem__(idx):
        Returns the tokenized input data and label at the specified index.
    __len__():
        Returns the length of the dataset.
    """
    def __init__(self, encodings, labels):
        """
        Constructs all the necessary attributes for the PubMedDataset object.

        Parameters:
        -----------
        encodings : dict
            A dictionary of tokenized input data (input_ids, attention_mask, etc.).
        labels : list
            A list of labels corresponding to the input data.
        """
        self.encodings = encodings
        self.labels = labels

    def __getitem__(self, idx):
        """
        Returns the tokenized input data and label at the specified index.

        Parameters:
        -----------
        idx : int
            Index of the data item.

        Returns:
        --------
        dict
            A dictionary containing the tokenized input data and the corresponding label.
        """
        item = {key: torch.tensor(val[idx]) for key, val in self.encodings.items()}
        item['labels'] = torch.tensor(self.labels[idx])
        return item

    def __len__(self):
        """
        Returns the length of the dataset.

        Returns:
        --------
        int
            The number of data samples in the dataset.
        """
        return len(self.labels)


def main(positive_path=None, negative_path=None, save_path=None):
    """
    Main function to fine-tune PubMedBERT using argparse to pass the positive and negative data paths,
    as well as the save path for the model.

    """
    
    if positive_path is None or negative_path is None or save_path is None:
        parser = argparse.ArgumentParser(description="Fine-tune PubMedBERT on a dataset of abstracts.")
        parser.add_argument('-p', '--positive_data', type=str, required=True, help="Path to the positive data (TSV format).")
        parser.add_argument('-n', '--negative_data', type=str, required=True, help="Path to the negative data (TSV format).")
        parser.add_argument('-s', '--save_path', type=str, required=True, help="Directory where the fine-tuned model will be saved.")
        
        args = parser.parse_args()
        positive_path = args.positive_data
        negative_path = args.negative_data
        save_path = args.save_path
    
    trainer = PubMedBertTrainer(model_name="microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext")

    # Load and split data
    texts, labels = trainer.load_data(positive_path, negative_path)
    train_texts, val_texts, train_labels, val_labels = trainer.split_data(texts, labels)

    # Prepare dataloaders
    train_loader, val_loader = trainer.prepare_dataloaders(train_texts, val_texts, train_labels, val_labels)

    # Train the model
    trainer.train(train_loader)

    # Evaluate the model
    trainer.evaluate(val_loader)

    # Save the model
    trainer.save_model(save_path)


if __name__ == "__main__":
    main()

# python fine_tune_pubmedbert.py -p positive.tsv -n negative.tsv -s ./finetuned_pubmedbert_2
