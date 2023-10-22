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
#
# These tests assume that some edges will always be in Automat-CAM-KP:
# - NCBIGene:15481 ("heat shock protein 8 [Mus musculus (house mouse)]")
#   biolink:active_in UBERON:0002240 ("spinal cord")
import logging
import os
import urllib.parse

import requests

CAM_KP_API_ENDPOINT = os.getenv(
    "CAM_KP_API_ENDPOINT", "https://automat.renci.org/cam-kp/"
)
TRAPI_VERSION = os.getenv("TRAPI_VERSION", "1.4")

# Some data that is used by multiple tests.
uberon_0002240_node_info = {
    "name": "spinal cord",
    "description": "Part of the central nervous system located in the vertebral canal continuous with and caudal to "
    "the brain; demarcated from brain by plane of foramen magnum. It is composed of an inner core of "
    "gray matter in which nerve cells predominate, and an outer layer of white matter in which "
    "myelinated nerve fibers predominate, and surrounds the central canal. (CUMBO).",
    "id": "UBERON:0002240",
    "information_content": 57.9,
    "equivalent_identifiers": [
        "UBERON:0002240",
        "UMLS:C0037925",
        "MESH:D013116",
        "NCIT:C12464",
    ],
}


def test_metadata():
    """
    Test the GET /cam-kp/metadata endpoint.
    """
    metadata_url = urllib.parse.urljoin(CAM_KP_API_ENDPOINT, "metadata")
    response = requests.get(metadata_url)
    assert response.ok, f"Could not retrieve metadata from {metadata_url}."

    metadata = response.json()

    # Check some metadata items.
    assert metadata["graph_id"] == "CAMKP_Automat"
    assert metadata["graph_name"] == "CAM Provider KG"
    assert metadata["final_node_count"] > 111_000
    assert metadata["final_edge_count"] > 3_000_000

    # Check the sources information.
    sources = metadata["sources"]
    assert len(sources) == 1, f"Unexpected number of sources from CAM-KP: {sources}"
    assert sources[0]["source_id"] == "CAM-KP"
    assert sources[0]["provenance"] == "infores:go-cam"
    assert (
        sources[0]["attribution"] == "https://github.com/ExposuresProvider/cam-kp-api"
    )
    assert (
        sources[0]["source_data_url"]
        == "https://github.com/ExposuresProvider/cam-kp-api"
    )
    assert (
        sources[0]["license"]
        == "https://github.com/ExposuresProvider/cam-kp-api/blob/master/LICENSE"
    )

    # Check the QC results.
    assert set(metadata["qc_results"]["primary_knowledge_sources"]) == {
        "infores:ctd",
        "infores:aop-cam",
        "infores:go-cam",
    }

    node_curie_prefixes = metadata["qc_results"]["node_curie_prefixes"]
    assert "CHEBI" in node_curie_prefixes
    assert "NCBIGene" in node_curie_prefixes
    assert "PUBCHEM.COMPOUND" in node_curie_prefixes
    assert "UBERON" in node_curie_prefixes
    assert "UniProtKB" in node_curie_prefixes

    assert set(metadata["qc_results"]["edge_properties"]) == {
        "predicate",
        "biolink:primary_knowledge_source",
        "object",
        "subject",
        "xref",
    }

    # TODO: we need to add infores:aop-cam to https://github.com/biolink/biolink-model/blob/db44be0c49939229c28cbb71a715127941e0ce0b/infores_catalog.yaml
    assert set(metadata["qc_results"]["warnings"]["invalid_knowledge_sources"]) == {
        "infores:aop-cam"
    }


def test_sri_testing_data():
    """
    Test the SRI Testing Data output at GET /cam-kp/1.4/sri_testing_data.
    """
    sri_testing_url = urllib.parse.urljoin(
        CAM_KP_API_ENDPOINT, f"{TRAPI_VERSION}/sri_testing_data"
    )
    response = requests.get(sri_testing_url)
    assert response.ok, f"Could not retrieve SRI Testing Data URL at {sri_testing_url}."
    sri_testing_data = response.json()

    edges = sri_testing_data["edges"]
    assert (
        len(edges) > 500
    ), f"Expected at least 100 edges in SRI Testing Data but got {len(edges)}."

    # Make sure all _id fields look like CURIEs.
    all_subject_ids = list(map(lambda edge: (edge["subject_id"], edge), edges))
    all_object_ids = list(map(lambda edge: (edge["object_id"], edge), edges))
    for ident, id_edge in all_subject_ids + all_object_ids:
        assert (
            ":" in ident
        ), f"CURIE {ident} in edge {id_edge} does not look like a valid CURIE."

    all_predicates = set(map(lambda edge: edge["predicate"], edges))
    assert all_predicates == {
        "biolink:active_in",
        "biolink:actively_involved_in",
        "biolink:acts_upstream_of_negative_effect",
        "biolink:acts_upstream_of_or_within",
        "biolink:acts_upstream_of_or_within_negative_effect",
        "biolink:acts_upstream_of_or_within_positive_effect",
        "biolink:acts_upstream_of_positive_effect",
        "biolink:affects",
        "biolink:capable_of",
        "biolink:causes",
        "biolink:coexists_with",
        "biolink:colocalizes_with",
        "biolink:directly_physically_interacts_with",
        "biolink:enables",
        "biolink:has_input",
        "biolink:has_output",
        "biolink:has_part",
        "biolink:has_participant",
        "biolink:interacts_with",
        "biolink:located_in",
        "biolink:occurs_in",
        "biolink:overlaps",
        "biolink:precedes",
        "biolink:regulates",
        "biolink:temporally_related_to",
    }

    all_subject_categories = set(map(lambda edge: edge["subject_category"], edges))
    assert all_subject_categories == {
        "biolink:AnatomicalEntity",
        "biolink:BiologicalProcess",
        "biolink:Cell",
        "biolink:CellularComponent",
        "biolink:ChemicalEntity",
        "biolink:ChemicalMixture",
        "biolink:ComplexMolecularMixture",
        "biolink:Drug",
        "biolink:Gene",
        "biolink:GrossAnatomicalStructure",
        "biolink:MolecularActivity",
        "biolink:MolecularMixture",
        "biolink:Pathway",
        "biolink:Polypeptide",
        "biolink:Protein",
        "biolink:SmallMolecule",
    }

    all_edge_categories = set(map(lambda edge: edge["object_category"], edges))
    assert all_edge_categories == {
        "biolink:AnatomicalEntity",
        "biolink:BiologicalProcess",
        "biolink:Cell",
        "biolink:CellularComponent",
        "biolink:ChemicalEntity",
        "biolink:ChemicalMixture",
        "biolink:ComplexMolecularMixture",
        "biolink:Gene",
        "biolink:GrossAnatomicalStructure",
        "biolink:MacromolecularComplex",
        "biolink:MolecularActivity",
        "biolink:MolecularMixture",
        "biolink:Pathway",
        "biolink:Polypeptide",
        "biolink:Protein",
        "biolink:SmallMolecule",
    }


def test_simple_spec():
    """
    Test the GET /cam-kp/simple_spec endpoint.
    """
    simple_spec_tests = [{
        'source': 'UBERON:0002240',
        'target': 'NCBIGene:15481',
        # TODO: wait, what?
        'expected_predicates': {'biolink:overlaps'}
    }]

    simple_spec_endpoint = urllib.parse.urljoin(CAM_KP_API_ENDPOINT, "simple_spec")
    for simple_spec_test in simple_spec_tests:
        response = requests.get(simple_spec_endpoint, {"source": simple_spec_test["source"], "target": simple_spec_test["target"]})
        assert response.ok, f"Unable to look up {simple_spec_endpoint} with source: {simple_spec_test['source']} and target: {simple_spec_test['target']}."
        predicates = set(map(lambda res: res['edge_type'], response.json()))
        logging.debug(f"Retrieved predicates predicates_for_edge for {simple_spec_test['source']} to {simple_spec_test['target']}: {predicates}")

        assert simple_spec_test["expected_predicates"] == predicates, f"When querying for {simple_spec_test['source']} to {simple_spec_test['target']}, expected predicates {simple_spec_test['expected_predicates']} did not match {predicates}."


def test_source_target_curie_one_hop_and_simple_spec():
    """
    Test the GET /cam-kp/{source_type}/{target_type}/{curie} endpoint and the /cam-kp/simple_spec endpoint.
    """
    source_target_curies = [
        {
            "source_type": "biolink:AnatomicalEntity",
            "target_type": "biolink:Gene",
            "curie": "UBERON:0002240",
            "expected_node_ids": {
                "UBERON:0002240",
                "NCBIGene:15481"
            },
            "expected_xrefs": {
                "http://model.geneontology.org/SYNGO_2911"
            },
            "expected_predicates": {},
            "expected_knowledge_sources": { "infores:go-cam" },
        }
    ]

    for source_target_curie in source_target_curies:
        source_target_url = (
            CAM_KP_API_ENDPOINT
            + f"{source_target_curie['source_type']}/{source_target_curie['target_type']}/{source_target_curie['curie']}"
        )
        response = requests.get(source_target_url)
        assert response.ok, f"Could not retrieve source-target-curie response from {source_target_url}."
        results = response.json()

        xrefs = set()
        knowledge_sources = set()
        node_ids = set()
        for result in results:
            edge = result[1]
            if "xref" in edge:
                xrefs.update(edge["xref"])
            if "biolink:primary_knowledge_source" in edge:
                knowledge_sources.add(edge["biolink:primary_knowledge_source"])

            if "id" in result[0]:
                node_ids.add(result[0]["id"])

            if "id" in result[2]:
                node_ids.add(result[2]["id"])

        assert source_target_curie["expected_node_ids"] <= node_ids, f"All node IDs in {source_target_curie['expected_node_ids']} are not present in the list of node IDs obtained: {node_ids}"
        assert source_target_curie["expected_xrefs"] <= xrefs, f"All expected xrefs in {source_target_curie['expected_xrefs']} are not present in the list of xrefs obtained: {xrefs}"
        assert source_target_curie["expected_knowledge_sources"] <= knowledge_sources, f"All expected knowledge sources in {source_target_curie['expected_knowledge_sources']} are not present in the list of knowledge sources obtained: {knowledge_sources}"


def test_node_type_curie():
    """
    Test the GET /cam-kp/{node_type}/{curie} endpoint.
    """
    node_type_curies = [
        {
            "node_type": "biolink:AnatomicalEntity",
            "curie": "UBERON:0002240",
            "expected": uberon_0002240_node_info,
        }
    ]

    for node_type_curie in node_type_curies:
        node_type_curie_url = (
            CAM_KP_API_ENDPOINT
            + f"{node_type_curie['node_type']}/{node_type_curie['curie']}"
        )
        response = requests.get(node_type_curie_url)
        assert (
            response.ok
        ), f"Could not retrieve node-type/CURIE information at {node_type_curie_url}."
        node_type_data = response.json()

        assert len(node_type_data) == 1
        assert node_type_data[0] == node_type_curie["expected"]
