# Installation

automaxo is setup using the dependency manager [poetry](https://python-poetry.org/){:target="_blank"}.
automaxo requires Python 3.9. There are many ways of setting this up, and users should consult documentation specific to their system.
Once you have Python3.9 installed, it may be necessary to specify the Python version to poetry. For instance, on our system
both Python 3.12 and 3.9 are installed, and Python 3.9 is available at ``/usr/bin``. Therefore, we run this command.

```bash
 poetry env use /usr/bin/python3
```

After poetry is using Python 3.9, we can install the tool by cd'ing into the `àutomaxo``directory and executing the following commands.
Note that the first command will take several minutes.

``` bash
 poetry install
 poetry shell
```

## Prerequisites

Ensure you have the following installed:

- python = ">=3.9,<3.9.7 || >3.9.7,<3.11"
- poetry

### Setting Up the Project

Clone the AutoMAxO repository and navigate to the project directory:

```bash
git clone https://github.com/your-repo/automaxo.git
cd automaxo
```

## Installation of AutoMAxO environment

First, create and activate a virtual environment:

```bash
poetry install
poetry shell
```

Add your openAI key:

```bash
runoak set-apikey -e openai <your openai api key>
```

## Running the Script

You can run the script using the following command:

```shell
python main.py --disease_name "YourDiseaseName" --max_articles_to_save 100
```

Replace "YourDiseaseName" with the name of the disease you want to process and adjust 100 to the desired number of articles to save.

or you can just run this command:

```bash
python main.py
```

and then enter a disease name, and number of articles to be saved.
