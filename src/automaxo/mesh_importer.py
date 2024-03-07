import click
from SPARQLWrapper import SPARQLWrapper, JSON
from typing import List


class MeSHEntry:

    """
    reads a list of targeted mesh ids and their labels and creates a formated file with mesh sets required for WN2VEC output
    ...

    Attributes
    ----------
    :param id: mesh id (ex: D007674)	Kidney Diseases
    :type id: str
    :param label: a lable corresponding to mesh id (ex "Kidney Diseases")
    :type label: str
    """

    def __init__(self, id, label) -> None:
        """
        Constructs all the necessary attributes for the  class MeSHEntry class

        """
        self._id = id
        self._label = label

    @property
    def id(self):
        """
        returns the mesh id
        """
        return self._id

    @property
    def label(self):
        """
        returns the label corresponding to the mesh id
        """
        return self._label

    @property
    def meshlabel(self):
        """
        returns the string with mesh label
        """
        return "D" + self._id[1:]

    def __str__(self):
        """
        returns a string with mesh id and mesh label
        """
        return f"{self._id}: {self._label}"


def get_query(meshid):
    return (
        """
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    PREFIX meshv: <http://id.nlm.nih.gov/mesh/vocab#>
    PREFIX mesh: <http://id.nlm.nih.gov/mesh/>
    PREFIX mesh2015: <http://id.nlm.nih.gov/mesh/2015/>
    PREFIX mesh2016: <http://id.nlm.nih.gov/mesh/2016/>
    PREFIX mesh2017: <http://id.nlm.nih.gov/mesh/2017/>

    SELECT DISTINCT ?descriptor ?label
    FROM <http://id.nlm.nih.gov/mesh>

    WHERE {
        mesh:%s meshv:treeNumber ?treeNum .
        ?childTreeNum meshv:parentTreeNumber+ ?treeNum .
        ?descriptor meshv:treeNumber ?childTreeNum .
        ?descriptor rdfs:label ?label .
    }

    ORDER BY ?label
    """
        % meshid
    )


def extract_MeSH_id(mesh_uri):
    """
    mesh_uri is something like http://id.nlm.nih.gov/mesh/D008258
    return the id, e.g., D008258
    """
    if not mesh_uri.startswith("http://id.nlm.nih.gov/mesh/"):
        raise ValueError("Malformed MeSH URI: '%s'" % mesh_uri)
    mesh = mesh_uri[27:]
    return mesh


def get_mesh_entries(meshid: str):
    mesh_entries = []
    if not meshid.startswith("D"):
        raise ValueError(f"Mesh ID needs to be of the form D008258 but we got {meshid}")
    sparql = SPARQLWrapper("https://id.nlm.nih.gov/mesh/sparql")
    query = get_query(meshid)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    for result in results["results"]["bindings"]:
        mesh_label = result["label"]["value"]
        mesh_id = extract_MeSH_id(result["descriptor"]["value"])
        me = MeSHEntry(id=mesh_id, label=mesh_label)
        mesh_entries.append(me)
    return mesh_entries


@click.command()
@click.option('--input-file', default='../../data/mesh_target_ids.tsv', help='Path to the input TSV file containing target MeSH IDs.')
@click.option('--output-file', default='../../data/mesh_sets.tsv', help='Path to the output TSV file.')
def main(input_file: str, output_file: str):
    with open(input_file) as f, open(output_file, "wt") as fh:
        next(f)  # Skip header
        for line in f:
            fields = line.rstrip().split("\t")
            if len(fields) == 2:
                meshid, label = fields
                me = MeSHEntry(id=meshid, label=label)
                entries = get_mesh_entries(meshid)
                if len(entries) < 3:
                    continue
                entry_id_list = [e.meshlabel for e in entries]
                entry_str = ";".join(entry_id_list)
                fh.write(f"{label}\t{meshid}\t{entry_str}\n")

def run_in_notebook(input_file: str, output_file: str):
    main.main(standalone_mode=False, args=['--input-file', input_file, '--output-file', output_file])

if __name__ == '__main__':
    main()





"""
python mesh_importer.py --input-file path/to/mesh_target_ids.tsv --output-file path/to/mesh_sets.tsv

"""
