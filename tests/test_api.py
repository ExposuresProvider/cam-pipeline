#
# test_api.py -- test whether Automat-CAM-KP API is up and running at a particular URL.
#
# This API provides some basic tests for every endpoint:
# - POST /cam-kp/1.4/query
# - POST /cam-kp/cypher
# - POST /cam-kp/overlay
# - GET /cam-kp/1.4/meta_knowledge_graph
# - GET /cam-kp/1.4/sri_testing_data
# - GET /cam-kp/metadata
# - GET /cam-kp/{source_type}/{target_type}/{curie}
# - GET /cam-kp/{node_type}/{curie}
# - GET /cam-kp/simple_spec

import os
import urllib.parse

import requests

CAM_KP_API_ENDPOINT = os.getenv('CAM_KP_API_ENDPOINT', 'https://automat.renci.org/cam-kp/')
TRAPI_VERSION = os.getenv('TRAPI_VERSION', '1,4')


def test_metadata():
    """
    Test the GET /cam-kp/metadata endpoint.
    """
    metadata_url = urllib.parse.urljoin(CAM_KP_API_ENDPOINT, 'metadata')
    response = requests.get(metadata_url)
    assert response.ok, f"Could not retrieve {metadata_url}"

    metadata = response.json()

    # Check some metadata items.
    assert metadata['graph_id'] == "CAMKP_Automat"
    assert metadata['graph_name'] == "CAM Provider KG"
    assert metadata['final_node_count'] > 111_000
    assert metadata['final_edge_count'] > 3_000_000

    # Check the sources information.
    sources = metadata['sources']
    assert len(sources) == 1, f"Unexpected number of sources from CAM-KP: {sources}"
    assert sources[0]['source_id'] == "CAM-KP"
    assert sources[0]['provenance'] == "infores:go-cam"
    assert sources[0]['attribution'] == "https://github.com/ExposuresProvider/cam-kp-api"
    assert sources[0]['source_data_url'] == "https://github.com/ExposuresProvider/cam-kp-api"
    assert sources[0]['license'] == "https://github.com/ExposuresProvider/cam-kp-api/blob/master/LICENSE"

    # Check the QC results.
    assert set(metadata['qc_results']['primary_knowledge_sources']) == {"infores:ctd", "infores:aop-cam", "infores:go-cam"}

    node_curie_prefixes = metadata['qc_results']['node_curie_prefixes']
    assert "CHEBI" in node_curie_prefixes
    assert "NCBIGene" in node_curie_prefixes
    assert "PUBCHEM.COMPOUND" in node_curie_prefixes
    assert "UBERON" in node_curie_prefixes
    assert "UniProtKB" in node_curie_prefixes

    assert set(metadata['qc_results']['edge_properties']) == {
        "predicate",
        "biolink:primary_knowledge_source",
        "object",
        "subject",
        "xref"
    }

    # TODO: we need to add infores:aop-cam to https://github.com/biolink/biolink-model/blob/db44be0c49939229c28cbb71a715127941e0ce0b/infores_catalog.yaml
    assert set(metadata['qc_results']['warnings']['invalid_knowledge_sources']) == {"infores:aop-cam"}
