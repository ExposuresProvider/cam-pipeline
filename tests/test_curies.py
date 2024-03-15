#
# test_ids.py -- test whether Automat-CAM-KP API has information about identifiers.
#
import logging
import os
import urllib.parse

import pytest
import requests

CAM_KP_API_ENDPOINT = os.getenv(
    "CAM_KP_API_ENDPOINT", "https://automat.renci.org/cam-kp/"
)
NODE_NORM_API_ENDPOINT = os.getenv(
    "NODE_NORM_API_ENDPOINT", "https://nodenormalization-sri.renci.org/"
)
TRAPI_VERSION = os.getenv("TRAPI_VERSION", "1.4")

# Identifiers to check for.
CURIES_TO_TEST = [
    # Identifiers from https://github.com/ExposuresProvider/cam-pipeline/issues/101
    'PUBCHEM.COMPOUND:5865',            # Prednisone |
    'PUBCHEM.COMPOUND:5360696',         # Dextromethorphan hydrobromide (CHEMBL.COMPOUND:CHEMBL1256818) |
    'PUBCHEM.COMPOUND:165363555',       # Trifacta |
    'PUBCHEM.COMPOUND:5311101',         # Fluticasone (HMDB:HMDB0252416) |
    "PUBCHEM.COMPOUND:123600",          # Levalbuterol |
    'PUBCHEM.COMPOUND:5281004',         # Budesonide (HMDB:HMDB0242500) |
    "PUBCHEM.COMPOUND:45358055",        # Formoterol (CHEBI:5147) |
    'PUBCHEM.COMPOUND:5742832',         # Aztreonam (CHEMBL.COMPOUND:CHEMBL158) |
    "PUBCHEM.COMPOUND:145068",          # Nitric oxide |
    "PUBCHEM.COMPOUND:281",             # Carbon monoxide |
]


@pytest.mark.parametrize('curie', CURIES_TO_TEST)
def test_identifier(curie):
    """
    Test whether Automat-CAM-KP knows anything useful about a particular identifier.

    :param id: The identifier (CURIE) to test.
    """

    # Step 1. Use the node-type-curie endpoint to look up this identifier.
    node_type_curie_url = (
        CAM_KP_API_ENDPOINT
        + f"biolink:NamedThing/{curie}"
    )
    response = requests.get(node_type_curie_url)
    assert (
        response.ok
    ), f"Could not retrieve node-type/CURIE information at {node_type_curie_url}."
    node_type_data = response.json()

    assert len(node_type_data) <= 1, f"Multiple entries found for CURIE {curie}."

    # If there are zero results, that is a failure, but we can do stuff to help diagnose the issue.
    if len(node_type_data) == 0:
        # Normalize the identifier and see if that provides insights.
        node_norm_url = (NODE_NORM_API_ENDPOINT + f"get_normalized_nodes")
        response = requests.get(node_norm_url, {
            "curie": curie,
            "conflate": "true"
        })
        assert response.ok, f"Error connecting to NodeNorm at {node_norm_url}: {response}"

        response_json = response.json()
        assert curie in response_json, f"CURIE missing in response: {response_json}"

        if response_json[curie] is None:
            assert False, (f"CURIE {curie} not present in Automat-CAM-KP {CAM_KP_API_ENDPOINT} and cannot be "
                           f"normalized using {NODE_NORM_API_ENDPOINT}.")
        elif response_json[curie]['id']['identifier'] == curie:
            assert False, (f"CURIE {curie} not present in Automat-CAM-KP {CAM_KP_API_ENDPOINT}, and this is the "
                           f"normalized identifier according to {NODE_NORM_API_ENDPOINT}.")
        else:
            assert False, f"CURIE {curie} not present in Automat-CAM-KP {CAM_KP_API_ENDPOINT}, but can be normalized to {response_json[curie]['id']['identifier']} ({response_json[curie]['id']['label']}): {response_json[curie]}"

    # If we get there, there is only a single response -- perfect.
    # Step 2. See what CURIEs we connect to this CURIE.
    source_target_url = (
            CAM_KP_API_ENDPOINT
            + f"biolink:NamedThing/biolink:NamedThing/{curie}"
    )
    response = requests.get(source_target_url)
    assert (
        response.ok
    ), f"Could not retrieve source-target-curie response from {source_target_url}: {response}"
    results = response.json()

    linked_nodes = []
    for result in results:
        # We can ignore the subject, since it should always be the query CURIE.
        # subj = result[0]
        edge = result[1]
        obj = result[2]

        linked_node = {
            'xref_list': edge['xref'],
            'primary_knowledge_source': edge['biolink:primary_knowledge_source'],
            'id': obj['id'],
            'label': obj.get('name', ''),
        }

        linked_nodes.append(linked_node)

    assert len(linked_nodes) > 0, f"No linked nodes found for CURIE {curie} in {CAM_KP_API_ENDPOINT}"
    # assert len(linked_nodes) == 0, f"{len(linked_nodes)} linked nodes found for CURIE {curie} in {CAM_KP_API_ENDPOINT}"

    linked_curies = set([n['id'] for n in linked_nodes])
    print(f"Found {len(linked_nodes)} linked nodes (with {len(linked_curies)} unique CURIEs) for CURIE {curie}:")
    for linked_node in linked_nodes:
        print(f" - {linked_node['id']} ({linked_node['label']}): {linked_node['primary_knowledge_source']} at {linked_node['xref_list']}")
