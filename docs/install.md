# Installation

## 1. Prerequisites

Ensure you have the following installed:
* Python: >=3.9, <3.9.7 or >3.9.7, <3.11
* Poetry
* OpenAI API Key

### Install the Right Version of Python
AutoMAxO requires Python 3.9. There are many ways to set this up, and users should consult documentation specific to their system.

### Install Poetry
AutoMAxO is set up using the dependency manager [Poetry](https://python-poetry.org/).

Once you have Python 3.9 installed, it may be necessary to specify the Python version to Poetry. For instance, on our system, both Python 3.12 and 3.9 are installed, and Python 3.9 is available at `/usr/bin`.

Therefore, we run this command:

```bash
poetry env use /usr/bin/python3
```

## 2. Setting Up the Project

Clone the AutoMAxO repository and navigate to the project directory:

```bash
git clone https://github.com/monarch-initiative/automaxo
cd automaxo
```

## 3. Installation of AutoMAxO Environment

After Poetry is using Python 3.9, you can install the tool by navigating to the `automaxo` directory and executing the following commands. Note that the first command will take several minutes.

```bash
poetry install
poetry shell
```

Add your OpenAI key:

```bash
runoak set-apikey -e openai <your_openai_api_key>
```

## 4. Running the Script

You can run the script using the following command:

```bash
python main.py
```

You will then be prompted to enter a disease name and the number of articles to be processed.

Alternatively, you can run this command all at once:

```bash
python main.py --disease_name "YourDiseaseName" --max_articles_to_save 100
```

Replace "YourDiseaseName" with the name of the disease you want to process and adjust `100` to the desired number of articles to be processed.