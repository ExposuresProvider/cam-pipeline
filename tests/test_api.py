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
trapi_query_what_is_hsp8_mus_musculus_active_in = {
    "message": {
        "query_graph": {
            "nodes": {
                "n0": {
                    "ids": ["NCBIGene:15481"],
                },
                "n1": {
                    "categories": ["biolink:AnatomicalEntity"]
                }
            },
            "edges": {
                "e0": {
                    "subject": "n0",
                    "object": "n1",
                    "predicates": ["biolink:active_in"]
                }
            }
        }
    }
}
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


def test_meta_knowledge_graph():
    """
    Test the GET /cam-kp/1.4/meta_knowledge_graph
    """
    meta_knowledge_graph_url = urllib.parse.urljoin(
        CAM_KP_API_ENDPOINT, f"{TRAPI_VERSION}/meta_knowledge_graph"
    )
    response = requests.get(meta_knowledge_graph_url)
    assert (
        response.ok
    ), f"Unable to request the meta knowledge graph from {meta_knowledge_graph_url}."
    metakg = response.json()

    # Check nodes in the metakg.
    nodes = metakg["nodes"]
    node_types = nodes.keys()
    expected_node_types = {
        "biolink:SmallMolecule",
        "biolink:ChemicalEntity",
        "biolink:ChemicalMixture",
        "biolink:Polypeptide",
        "biolink:MolecularMixture",
        "biolink:Cell",
        "biolink:MacromolecularComplex",
        "biolink:ComplexMolecularMixture",
        "biolink:Gene",
        "biolink:BiologicalProcess",
        "biolink:MolecularActivity",
        "biolink:Pathway",
        "biolink:CellularComponent",
        "biolink:Protein",
        "biolink:Drug",
        "biolink:GrossAnatomicalStructure",
        "biolink:AnatomicalEntity",
    }
    assert (
        node_types == expected_node_types
    ), "Found differences between node types in MetaKG and expected node types."

    # Check edges in the metakg.
    edges = metakg["edges"]

    # Change subject-predicate-objects into tuples.
    edge_tuples = {
        (
            edge["subject"],
            edge["predicate"],
            edge["object"],
            "|".join(edge["qualifiers"]),
        )
        for edge in edges
    }
    edge_tuples_expected = {
        ("biolink:Polypeptide", "biolink:causes", "biolink:ChemicalEntity", ""),
        (
            "biolink:CellularComponent",
            "biolink:overlaps",
            "biolink:AnatomicalEntity",
            "",
        ),
        ("biolink:Pathway", "biolink:overlaps", "biolink:MolecularActivity", ""),
        ("biolink:Gene", "biolink:regulates", "biolink:Pathway", ""),
        ("biolink:MolecularMixture", "biolink:causes", "biolink:Protein", ""),
        (
            "biolink:Protein",
            "biolink:acts_upstream_of_or_within_positive_effect",
            "biolink:BiologicalProcess",
            "",
        ),
        ("biolink:Protein", "biolink:interacts_with", "biolink:Protein", ""),
        ("biolink:MolecularMixture", "biolink:causes", "biolink:SmallMolecule", ""),
        (
            "biolink:MolecularActivity",
            "biolink:has_input",
            "biolink:ComplexMolecularMixture",
            "",
        ),
        ("biolink:Protein", "biolink:interacts_with", "biolink:SmallMolecule", ""),
        ("biolink:Gene", "biolink:active_in", "biolink:BiologicalProcess", ""),
        (
            "biolink:Polypeptide",
            "biolink:actively_involved_in",
            "biolink:BiologicalProcess",
            "",
        ),
        ("biolink:SmallMolecule", "biolink:affects", "biolink:ChemicalEntity", ""),
        ("biolink:ChemicalEntity", "biolink:causes", "biolink:ChemicalEntity", ""),
        (
            "biolink:BiologicalProcess",
            "biolink:overlaps",
            "biolink:BiologicalProcess",
            "",
        ),
        (
            "biolink:BiologicalProcess",
            "biolink:precedes",
            "biolink:MolecularActivity",
            "",
        ),
        (
            "biolink:SmallMolecule",
            "biolink:causes",
            "biolink:ComplexMolecularMixture",
            "",
        ),
        ("biolink:Polypeptide", "biolink:active_in", "biolink:CellularComponent", ""),
        ("biolink:SmallMolecule", "biolink:causes", "biolink:BiologicalProcess", ""),
        ("biolink:SmallMolecule", "biolink:regulates", "biolink:MolecularActivity", ""),
        (
            "biolink:BiologicalProcess",
            "biolink:has_output",
            "biolink:ChemicalEntity",
            "",
        ),
        ("biolink:Gene", "biolink:regulates", "biolink:BiologicalProcess", ""),
        ("biolink:Polypeptide", "biolink:affects", "biolink:MolecularMixture", ""),
        ("biolink:CellularComponent", "biolink:causes", "biolink:Protein", ""),
        (
            "biolink:CellularComponent",
            "biolink:enables",
            "biolink:MolecularActivity",
            "",
        ),
        ("biolink:Gene", "biolink:causes", "biolink:Polypeptide", ""),
        (
            "biolink:Protein",
            "biolink:acts_upstream_of_positive_effect",
            "biolink:CellularComponent",
            "",
        ),
        ("biolink:Protein", "biolink:active_in", "biolink:CellularComponent", ""),
        ("biolink:Protein", "biolink:interacts_with", "biolink:MolecularMixture", ""),
        ("biolink:Gene", "biolink:affects", "biolink:ComplexMolecularMixture", ""),
        ("biolink:Gene", "biolink:actively_involved_in", "biolink:Cell", ""),
        (
            "biolink:Gene",
            "biolink:acts_upstream_of_or_within_negative_effect",
            "biolink:CellularComponent",
            "",
        ),
        (
            "biolink:MolecularActivity",
            "biolink:causes",
            "biolink:MolecularActivity",
            "",
        ),
        ("biolink:SmallMolecule", "biolink:interacts_with", "biolink:Protein", ""),
        (
            "biolink:ChemicalEntity",
            "biolink:capable_of",
            "biolink:MolecularActivity",
            "",
        ),
        (
            "biolink:CellularComponent",
            "biolink:regulates",
            "biolink:MolecularActivity",
            "",
        ),
        ("biolink:BiologicalProcess", "biolink:has_input", "biolink:Polypeptide", ""),
        ("biolink:Polypeptide", "biolink:affects", "biolink:CellularComponent", ""),
        ("biolink:Pathway", "biolink:overlaps", "biolink:Pathway", ""),
        ("biolink:SmallMolecule", "biolink:located_in", "biolink:Cell", ""),
        ("biolink:Gene", "biolink:enables", "biolink:CellularComponent", ""),
        (
            "biolink:CellularComponent",
            "biolink:overlaps",
            "biolink:BiologicalProcess",
            "",
        ),
        ("biolink:Gene", "biolink:interacts_with", "biolink:MolecularMixture", ""),
        ("biolink:Protein", "biolink:causes", "biolink:Polypeptide", ""),
        ("biolink:Gene", "biolink:interacts_with", "biolink:Gene", ""),
        ("biolink:ChemicalMixture", "biolink:interacts_with", "biolink:Protein", ""),
        ("biolink:SmallMolecule", "biolink:enables", "biolink:MolecularActivity", ""),
        (
            "biolink:Gene",
            "biolink:acts_upstream_of_negative_effect",
            "biolink:BiologicalProcess",
            "",
        ),
        ("biolink:Protein", "biolink:located_in", "biolink:CellularComponent", ""),
        ("biolink:AnatomicalEntity", "biolink:causes", "biolink:Gene", ""),
        (
            "biolink:MolecularActivity",
            "biolink:has_output",
            "biolink:MolecularMixture",
            "",
        ),
        ("biolink:MolecularMixture", "biolink:causes", "biolink:MolecularActivity", ""),
        ("biolink:Gene", "biolink:occurs_in", "biolink:CellularComponent", ""),
        ("biolink:BiologicalProcess", "biolink:has_participant", "biolink:Cell", ""),
        ("biolink:MolecularActivity", "biolink:causes", "biolink:Pathway", ""),
        ("biolink:MolecularActivity", "biolink:preceded_by", "biolink:Protein", ""),
        ("biolink:Gene", "biolink:located_in", "biolink:AnatomicalEntity", ""),
        ("biolink:Gene", "biolink:interacts_with", "biolink:CellularComponent", ""),
        ("biolink:BiologicalProcess", "biolink:enabled_by", "biolink:Gene", ""),
        ("biolink:BiologicalProcess", "biolink:has_participant", "biolink:Gene", ""),
        (
            "biolink:CellularComponent",
            "biolink:has_part",
            "biolink:MolecularActivity",
            "",
        ),
        ("biolink:Cell", "biolink:overlaps", "biolink:Protein", ""),
        ("biolink:Cell", "biolink:has_participant", "biolink:Gene", ""),
        ("biolink:Gene", "biolink:affects", "biolink:Cell", ""),
        ("biolink:Protein", "biolink:active_in", "biolink:AnatomicalEntity", ""),
        ("biolink:Pathway", "biolink:has_part", "biolink:MolecularActivity", ""),
        (
            "biolink:ChemicalEntity",
            "biolink:causes",
            "biolink:ComplexMolecularMixture",
            "",
        ),
        ("biolink:Gene", "biolink:affects", "biolink:ChemicalMixture", ""),
        ("biolink:MolecularActivity", "biolink:enabled_by", "biolink:Polypeptide", ""),
        ("biolink:MolecularMixture", "biolink:interacts_with", "biolink:Gene", ""),
        ("biolink:Protein", "biolink:interacts_with", "biolink:CellularComponent", ""),
        ("biolink:ChemicalEntity", "biolink:interacts_with", "biolink:Polypeptide", ""),
        (
            "biolink:MolecularMixture",
            "biolink:actively_involved_in",
            "biolink:MolecularActivity",
            "",
        ),
        (
            "biolink:BiologicalProcess",
            "biolink:has_participant",
            "biolink:MacromolecularComplex",
            "",
        ),
        ("biolink:Gene", "biolink:active_in", "biolink:Cell", ""),
        (
            "biolink:Gene",
            "biolink:directly_physically_interacts_with",
            "biolink:Protein",
            "",
        ),
        (
            "biolink:Gene",
            "biolink:acts_upstream_of_or_within_negative_effect",
            "biolink:BiologicalProcess",
            "",
        ),
        ("biolink:Pathway", "biolink:has_participant", "biolink:Polypeptide", ""),
        (
            "biolink:Gene",
            "biolink:actively_involved_in",
            "biolink:CellularComponent",
            "",
        ),
        ("biolink:Protein", "biolink:affects", "biolink:ChemicalMixture", ""),
        (
            "biolink:CellularComponent",
            "biolink:interacts_with",
            "biolink:Polypeptide",
            "",
        ),
        ("biolink:MolecularActivity", "biolink:preceded_by", "biolink:Pathway", ""),
        ("biolink:Polypeptide", "biolink:precedes", "biolink:CellularComponent", ""),
        ("biolink:MolecularMixture", "biolink:affects", "biolink:Protein", ""),
        (
            "biolink:MolecularActivity",
            "biolink:has_input",
            "biolink:ChemicalMixture",
            "",
        ),
        ("biolink:Gene", "biolink:enables", "biolink:BiologicalProcess", ""),
        ("biolink:Protein", "biolink:affects", "biolink:MolecularMixture", ""),
        ("biolink:BiologicalProcess", "biolink:overlaps", "biolink:Gene", ""),
        (
            "biolink:SmallMolecule",
            "biolink:interacts_with",
            "biolink:ChemicalEntity",
            "",
        ),
        ("biolink:MolecularMixture", "biolink:affects", "biolink:SmallMolecule", ""),
        ("biolink:Gene", "biolink:causes", "biolink:SmallMolecule", ""),
        ("biolink:SmallMolecule", "biolink:causes", "biolink:Gene", ""),
        (
            "biolink:ComplexMolecularMixture",
            "biolink:causes",
            "biolink:SmallMolecule",
            "",
        ),
        (
            "biolink:Protein",
            "biolink:actively_involved_in",
            "biolink:CellularComponent",
            "",
        ),
        (
            "biolink:MolecularActivity",
            "biolink:has_output",
            "biolink:CellularComponent",
            "",
        ),
        ("biolink:Gene", "biolink:causes", "biolink:MolecularActivity", ""),
        ("biolink:BiologicalProcess", "biolink:has_input", "biolink:Cell", ""),
        ("biolink:Gene", "biolink:active_in", "biolink:GrossAnatomicalStructure", ""),
        ("biolink:Polypeptide", "biolink:interacts_with", "biolink:Gene", ""),
        ("biolink:Protein", "biolink:causes", "biolink:Cell", ""),
        ("biolink:Drug", "biolink:causes", "biolink:Gene", ""),
        ("biolink:Gene", "biolink:affects", "biolink:Gene", ""),
        (
            "biolink:Protein",
            "biolink:acts_upstream_of_positive_effect",
            "biolink:BiologicalProcess",
            "",
        ),
        (
            "biolink:BiologicalProcess",
            "biolink:occurs_in",
            "biolink:AnatomicalEntity",
            "",
        ),
        (
            "biolink:CellularComponent",
            "biolink:acts_upstream_of_or_within_positive_effect",
            "biolink:Pathway",
            "",
        ),
        (
            "biolink:CellularComponent",
            "biolink:occurs_in",
            "biolink:CellularComponent",
            "",
        ),
        ("biolink:Cell", "biolink:overlaps", "biolink:AnatomicalEntity", ""),
        (
            "biolink:BiologicalProcess",
            "biolink:temporally_related_to",
            "biolink:MolecularActivity",
            "",
        ),
        (
            "biolink:CellularComponent",
            "biolink:colocalizes_with",
            "biolink:MolecularActivity",
            "",
        ),
        ("biolink:MolecularActivity", "biolink:has_participant", "biolink:Gene", ""),
        ("biolink:MolecularMixture", "biolink:affects", "biolink:MolecularMixture", ""),
        ("biolink:CellularComponent", "biolink:causes", "biolink:MolecularMixture", ""),
        (
            "biolink:CellularComponent",
            "biolink:acts_upstream_of_or_within_positive_effect",
            "biolink:MolecularActivity",
            "",
        ),
        (
            "biolink:SmallMolecule",
            "biolink:actively_involved_in",
            "biolink:MolecularActivity",
            "",
        ),
        ("biolink:MolecularActivity", "biolink:enabled_by", "biolink:Protein", ""),
        ("biolink:Polypeptide", "biolink:causes", "biolink:Polypeptide", ""),
        (
            "biolink:Protein",
            "biolink:directly_physically_interacts_with",
            "biolink:CellularComponent",
            "",
        ),
        (
            "biolink:ChemicalMixture",
            "biolink:interacts_with",
            "biolink:CellularComponent",
            "",
        ),
        ("biolink:CellularComponent", "biolink:overlaps", "biolink:Cell", ""),
        ("biolink:Protein", "biolink:causes", "biolink:MolecularActivity", ""),
        ("biolink:MolecularActivity", "biolink:has_input", "biolink:Cell", ""),
        (
            "biolink:MolecularActivity",
            "biolink:overlaps",
            "biolink:MolecularActivity",
            "",
        ),
        ("biolink:CellularComponent", "biolink:enabled_by", "biolink:Gene", ""),
        (
            "biolink:MolecularActivity",
            "biolink:precedes",
            "biolink:CellularComponent",
            "",
        ),
        ("biolink:Gene", "biolink:affects", "biolink:CellularComponent", ""),
        ("biolink:Protein", "biolink:affects", "biolink:Gene", ""),
        (
            "biolink:MolecularMixture",
            "biolink:causes",
            "biolink:ComplexMolecularMixture",
            "",
        ),
        ("biolink:CellularComponent", "biolink:has_participant", "biolink:Gene", ""),
        ("biolink:Gene", "biolink:causes", "biolink:ChemicalEntity", ""),
        (
            "biolink:MolecularActivity",
            "biolink:has_input",
            "biolink:MolecularMixture",
            "",
        ),
        ("biolink:MolecularActivity", "biolink:has_input", "biolink:Gene", ""),
        (
            "biolink:MolecularActivity",
            "biolink:regulates",
            "biolink:BiologicalProcess",
            "",
        ),
        ("biolink:SmallMolecule", "biolink:affects", "biolink:Protein", ""),
        (
            "biolink:MolecularActivity",
            "biolink:has_participant",
            "biolink:CellularComponent",
            "",
        ),
        ("biolink:SmallMolecule", "biolink:affects", "biolink:SmallMolecule", ""),
        (
            "biolink:CellularComponent",
            "biolink:causes",
            "biolink:CellularComponent",
            "",
        ),
        (
            "biolink:SmallMolecule",
            "biolink:acts_upstream_of_positive_effect",
            "biolink:BiologicalProcess",
            "",
        ),
        ("biolink:BiologicalProcess", "biolink:affects", "biolink:Protein", ""),
        ("biolink:Cell", "biolink:overlaps", "biolink:CellularComponent", ""),
        ("biolink:Pathway", "biolink:regulates", "biolink:MolecularActivity", ""),
        (
            "biolink:Polypeptide",
            "biolink:acts_upstream_of_or_within",
            "biolink:MolecularActivity",
            "",
        ),
        ("biolink:BiologicalProcess", "biolink:has_output", "biolink:Protein", ""),
        (
            "biolink:BiologicalProcess",
            "biolink:temporally_related_to",
            "biolink:Pathway",
            "",
        ),
        (
            "biolink:CellularComponent",
            "biolink:acts_upstream_of_or_within",
            "biolink:Pathway",
            "",
        ),
        (
            "biolink:Gene",
            "biolink:acts_upstream_of_or_within",
            "biolink:MolecularActivity",
            "",
        ),
        (
            "biolink:Gene",
            "biolink:actively_involved_in",
            "biolink:BiologicalProcess",
            "",
        ),
        (
            "biolink:BiologicalProcess",
            "biolink:has_output",
            "biolink:SmallMolecule",
            "",
        ),
        ("biolink:ChemicalMixture", "biolink:affects", "biolink:Gene", ""),
        ("biolink:Gene", "biolink:regulates", "biolink:Gene", ""),
        (
            "biolink:BiologicalProcess",
            "biolink:has_input",
            "biolink:ChemicalEntity",
            "",
        ),
        ("biolink:ChemicalEntity", "biolink:affects", "biolink:Polypeptide", ""),
        ("biolink:Protein", "biolink:affects", "biolink:CellularComponent", ""),
        ("biolink:Pathway", "biolink:preceded_by", "biolink:BiologicalProcess", ""),
        (
            "biolink:CellularComponent",
            "biolink:causes",
            "biolink:BiologicalProcess",
            "",
        ),
        ("biolink:Gene", "biolink:capable_of", "biolink:MolecularActivity", ""),
        (
            "biolink:CellularComponent",
            "biolink:acts_upstream_of_positive_effect",
            "biolink:BiologicalProcess",
            "",
        ),
        ("biolink:Protein", "biolink:causes", "biolink:ChemicalEntity", ""),
        (
            "biolink:MolecularActivity",
            "biolink:enabled_by",
            "biolink:SmallMolecule",
            "",
        ),
        ("biolink:Pathway", "biolink:has_participant", "biolink:ChemicalEntity", ""),
        ("biolink:SmallMolecule", "biolink:affects", "biolink:MolecularMixture", ""),
        (
            "biolink:Gene",
            "biolink:directly_physically_interacts_with",
            "biolink:CellularComponent",
            "",
        ),
        (
            "biolink:ChemicalEntity",
            "biolink:actively_involved_in",
            "biolink:MolecularActivity",
            "",
        ),
        (
            "biolink:Polypeptide",
            "biolink:interacts_with",
            "biolink:CellularComponent",
            "",
        ),
        (
            "biolink:BiologicalProcess",
            "biolink:causes",
            "biolink:BiologicalProcess",
            "",
        ),
        (
            "biolink:CellularComponent",
            "biolink:interacts_with",
            "biolink:ChemicalEntity",
            "",
        ),
        (
            "biolink:CellularComponent",
            "biolink:occurs_in",
            "biolink:AnatomicalEntity",
            "",
        ),
        (
            "biolink:Protein",
            "biolink:actively_involved_in",
            "biolink:BiologicalProcess",
            "",
        ),
        ("biolink:CellularComponent", "biolink:overlaps", "biolink:Gene", ""),
        ("biolink:Pathway", "biolink:occurs_in", "biolink:AnatomicalEntity", ""),
        (
            "biolink:MolecularMixture",
            "biolink:affects",
            "biolink:CellularComponent",
            "",
        ),
        ("biolink:Cell", "biolink:has_part", "biolink:Protein", ""),
        (
            "biolink:CellularComponent",
            "biolink:actively_involved_in",
            "biolink:MolecularActivity",
            "",
        ),
        (
            "biolink:MolecularActivity",
            "biolink:precedes",
            "biolink:BiologicalProcess",
            "",
        ),
        (
            "biolink:BiologicalProcess",
            "biolink:preceded_by",
            "biolink:MolecularActivity",
            "",
        ),
        ("biolink:Protein", "biolink:interacts_with", "biolink:ChemicalMixture", ""),
        ("biolink:CellularComponent", "biolink:regulates", "biolink:Protein", ""),
        ("biolink:Protein", "biolink:regulates", "biolink:CellularComponent", ""),
        (
            "biolink:Polypeptide",
            "biolink:directly_physically_interacts_with",
            "biolink:Protein",
            "",
        ),
        (
            "biolink:CellularComponent",
            "biolink:overlaps",
            "biolink:CellularComponent",
            "",
        ),
        (
            "biolink:MolecularActivity",
            "biolink:has_input",
            "biolink:CellularComponent",
            "",
        ),
        ("biolink:Gene", "biolink:overlaps", "biolink:CellularComponent", ""),
        ("biolink:Protein", "biolink:has_input", "biolink:MolecularActivity", ""),
        (
            "biolink:MolecularActivity",
            "biolink:preceded_by",
            "biolink:BiologicalProcess",
            "",
        ),
        ("biolink:ChemicalEntity", "biolink:causes", "biolink:MolecularMixture", ""),
        ("biolink:ChemicalEntity", "biolink:causes", "biolink:Gene", ""),
        ("biolink:ChemicalEntity", "biolink:affects", "biolink:Protein", ""),
        ("biolink:CellularComponent", "biolink:preceded_by", "biolink:Polypeptide", ""),
        (
            "biolink:ComplexMolecularMixture",
            "biolink:affects",
            "biolink:ChemicalEntity",
            "",
        ),
        ("biolink:ChemicalEntity", "biolink:affects", "biolink:SmallMolecule", ""),
        ("biolink:Gene", "biolink:regulates", "biolink:CellularComponent", ""),
        ("biolink:Gene", "biolink:interacts_with", "biolink:Polypeptide", ""),
        ("biolink:Gene", "biolink:overlaps", "biolink:AnatomicalEntity", ""),
        (
            "biolink:CellularComponent",
            "biolink:actively_involved_in",
            "biolink:Pathway",
            "",
        ),
        ("biolink:Polypeptide", "biolink:causes", "biolink:MolecularActivity", ""),
        (
            "biolink:BiologicalProcess",
            "biolink:has_part",
            "biolink:MolecularActivity",
            "",
        ),
        (
            "biolink:MolecularActivity",
            "biolink:has_output",
            "biolink:ChemicalMixture",
            "",
        ),
        ("biolink:ChemicalEntity", "biolink:causes", "biolink:CellularComponent", ""),
        ("biolink:Protein", "biolink:interacts_with", "biolink:Cell", ""),
        ("biolink:GrossAnatomicalStructure", "biolink:overlaps", "biolink:Gene", ""),
        ("biolink:Polypeptide", "biolink:affects", "biolink:Gene", ""),
        (
            "biolink:CellularComponent",
            "biolink:affects",
            "biolink:MolecularMixture",
            "",
        ),
        ("biolink:Pathway", "biolink:regulates", "biolink:Pathway", ""),
        (
            "biolink:Protein",
            "biolink:active_in",
            "biolink:GrossAnatomicalStructure",
            "",
        ),
        ("biolink:Gene", "biolink:acts_upstream_of_or_within", "biolink:Pathway", ""),
        ("biolink:MolecularMixture", "biolink:causes", "biolink:Gene", ""),
        ("biolink:Gene", "biolink:interacts_with", "biolink:MacromolecularComplex", ""),
        (
            "biolink:BiologicalProcess",
            "biolink:regulates",
            "biolink:MolecularActivity",
            "",
        ),
        (
            "biolink:BiologicalProcess",
            "biolink:has_output",
            "biolink:CellularComponent",
            "",
        ),
        ("biolink:Pathway", "biolink:causes", "biolink:BiologicalProcess", ""),
        ("biolink:Protein", "biolink:interacts_with", "biolink:Gene", ""),
        ("biolink:Protein", "biolink:located_in", "biolink:Cell", ""),
        ("biolink:Cell", "biolink:has_part", "biolink:AnatomicalEntity", ""),
        ("biolink:Protein", "biolink:overlaps", "biolink:AnatomicalEntity", ""),
        (
            "biolink:BiologicalProcess",
            "biolink:has_participant",
            "biolink:Polypeptide",
            "",
        ),
        ("biolink:Polypeptide", "biolink:interacts_with", "biolink:Polypeptide", ""),
        (
            "biolink:MolecularMixture",
            "biolink:affects",
            "biolink:ComplexMolecularMixture",
            "",
        ),
        (
            "biolink:GrossAnatomicalStructure",
            "biolink:overlaps",
            "biolink:GrossAnatomicalStructure",
            "",
        ),
        (
            "biolink:Gene",
            "biolink:acts_upstream_of_positive_effect",
            "biolink:MolecularActivity",
            "",
        ),
        ("biolink:Protein", "biolink:regulates", "biolink:BiologicalProcess", ""),
        (
            "biolink:CellularComponent",
            "biolink:affects",
            "biolink:CellularComponent",
            "",
        ),
        ("biolink:Protein", "biolink:active_in", "biolink:Cell", ""),
        (
            "biolink:BiologicalProcess",
            "biolink:has_output",
            "biolink:AnatomicalEntity",
            "",
        ),
        (
            "biolink:CellularComponent",
            "biolink:active_in",
            "biolink:AnatomicalEntity",
            "",
        ),
        (
            "biolink:ChemicalEntity",
            "biolink:acts_upstream_of_or_within",
            "biolink:BiologicalProcess",
            "",
        ),
        ("biolink:MolecularMixture", "biolink:causes", "biolink:CellularComponent", ""),
        ("biolink:BiologicalProcess", "biolink:causes", "biolink:Cell", ""),
        ("biolink:MolecularMixture", "biolink:interacts_with", "biolink:Protein", ""),
        ("biolink:Cell", "biolink:interacts_with", "biolink:Protein", ""),
        ("biolink:MacromolecularComplex", "biolink:interacts_with", "biolink:Gene", ""),
        (
            "biolink:MolecularActivity",
            "biolink:temporally_related_to",
            "biolink:BiologicalProcess",
            "",
        ),
        (
            "biolink:Protein",
            "biolink:acts_upstream_of_negative_effect",
            "biolink:MolecularActivity",
            "",
        ),
        ("biolink:BiologicalProcess", "biolink:regulates", "biolink:Pathway", ""),
        (
            "biolink:CellularComponent",
            "biolink:preceded_by",
            "biolink:MolecularActivity",
            "",
        ),
        ("biolink:MolecularActivity", "biolink:has_output", "biolink:Gene", ""),
        ("biolink:BiologicalProcess", "biolink:preceded_by", "biolink:Pathway", ""),
        ("biolink:Polypeptide", "biolink:capable_of", "biolink:MolecularActivity", ""),
        (
            "biolink:MolecularActivity",
            "biolink:causes",
            "biolink:CellularComponent",
            "",
        ),
        (
            "biolink:CellularComponent",
            "biolink:regulates",
            "biolink:CellularComponent",
            "",
        ),
        ("biolink:Protein", "biolink:affects", "biolink:Polypeptide", ""),
        ("biolink:Gene", "biolink:causes", "biolink:Protein", ""),
        ("biolink:SmallMolecule", "biolink:causes", "biolink:Polypeptide", ""),
        ("biolink:MolecularMixture", "biolink:causes", "biolink:MolecularMixture", ""),
        ("biolink:ChemicalEntity", "biolink:affects", "biolink:ChemicalEntity", ""),
        (
            "biolink:CellularComponent",
            "biolink:located_in",
            "biolink:AnatomicalEntity",
            "",
        ),
        (
            "biolink:SmallMolecule",
            "biolink:affects",
            "biolink:ComplexMolecularMixture",
            "",
        ),
        ("biolink:CellularComponent", "biolink:has_input", "biolink:Polypeptide", ""),
        (
            "biolink:Protein",
            "biolink:directly_physically_interacts_with",
            "biolink:Gene",
            "",
        ),
        ("biolink:BiologicalProcess", "biolink:has_participant", "biolink:Protein", ""),
        (
            "biolink:BiologicalProcess",
            "biolink:has_participant",
            "biolink:SmallMolecule",
            "",
        ),
        (
            "biolink:ChemicalEntity",
            "biolink:regulates",
            "biolink:MolecularActivity",
            "",
        ),
        (
            "biolink:MolecularActivity",
            "biolink:regulates",
            "biolink:MolecularActivity",
            "",
        ),
        ("biolink:Gene", "biolink:affects", "biolink:Polypeptide", ""),
        ("biolink:BiologicalProcess", "biolink:has_input", "biolink:Protein", ""),
        ("biolink:MolecularActivity", "biolink:preceded_by", "biolink:Gene", ""),
        ("biolink:CellularComponent", "biolink:causes", "biolink:ChemicalMixture", ""),
        ("biolink:Cell", "biolink:overlaps", "biolink:Cell", ""),
        ("biolink:BiologicalProcess", "biolink:has_input", "biolink:SmallMolecule", ""),
        (
            "biolink:CellularComponent",
            "biolink:precedes",
            "biolink:MolecularActivity",
            "",
        ),
        ("biolink:Protein", "biolink:causes", "biolink:Protein", ""),
        ("biolink:Gene", "biolink:overlaps", "biolink:BiologicalProcess", ""),
        ("biolink:Gene", "biolink:located_in", "biolink:GrossAnatomicalStructure", ""),
        ("biolink:Gene", "biolink:located_in", "biolink:CellularComponent", ""),
        ("biolink:SmallMolecule", "biolink:interacts_with", "biolink:Gene", ""),
        ("biolink:Protein", "biolink:causes", "biolink:SmallMolecule", ""),
        ("biolink:Gene", "biolink:causes", "biolink:MolecularMixture", ""),
        (
            "biolink:Gene",
            "biolink:acts_upstream_of_or_within_positive_effect",
            "biolink:MolecularActivity",
            "",
        ),
        ("biolink:BiologicalProcess", "biolink:precedes", "biolink:Pathway", ""),
        ("biolink:Polypeptide", "biolink:causes", "biolink:Pathway", ""),
        (
            "biolink:Gene",
            "biolink:actively_involved_in",
            "biolink:MolecularActivity",
            "",
        ),
        ("biolink:BiologicalProcess", "biolink:has_part", "biolink:Pathway", ""),
        ("biolink:CellularComponent", "biolink:overlaps", "biolink:Polypeptide", ""),
        ("biolink:Pathway", "biolink:has_participant", "biolink:SmallMolecule", ""),
        ("biolink:Protein", "biolink:affects", "biolink:Cell", ""),
        ("biolink:Pathway", "biolink:overlaps", "biolink:BiologicalProcess", ""),
        ("biolink:Pathway", "biolink:precedes", "biolink:MolecularActivity", ""),
        ("biolink:Polypeptide", "biolink:overlaps", "biolink:CellularComponent", ""),
        (
            "biolink:CellularComponent",
            "biolink:interacts_with",
            "biolink:SmallMolecule",
            "",
        ),
        (
            "biolink:CellularComponent",
            "biolink:has_part",
            "biolink:CellularComponent",
            "",
        ),
        ("biolink:CellularComponent", "biolink:has_participant", "biolink:Protein", ""),
        (
            "biolink:MolecularActivity",
            "biolink:preceded_by",
            "biolink:CellularComponent",
            "",
        ),
        ("biolink:MolecularActivity", "biolink:has_input", "biolink:Polypeptide", ""),
        (
            "biolink:MolecularActivity",
            "biolink:colocalizes_with",
            "biolink:CellularComponent",
            "",
        ),
        (
            "biolink:Protein",
            "biolink:acts_upstream_of_or_within",
            "biolink:MolecularActivity",
            "",
        ),
        (
            "biolink:Polypeptide",
            "biolink:acts_upstream_of_positive_effect",
            "biolink:MolecularActivity",
            "",
        ),
        (
            "biolink:SmallMolecule",
            "biolink:interacts_with",
            "biolink:CellularComponent",
            "",
        ),
        ("biolink:Pathway", "biolink:has_input", "biolink:Protein", ""),
        (
            "biolink:Protein",
            "biolink:acts_upstream_of_or_within_positive_effect",
            "biolink:MolecularActivity",
            "",
        ),
        (
            "biolink:Gene",
            "biolink:directly_physically_interacts_with",
            "biolink:Gene",
            "",
        ),
        ("biolink:ChemicalEntity", "biolink:causes", "biolink:BiologicalProcess", ""),
        (
            "biolink:MolecularActivity",
            "biolink:causes",
            "biolink:BiologicalProcess",
            "",
        ),
        ("biolink:AnatomicalEntity", "biolink:overlaps", "biolink:Protein", ""),
        ("biolink:ChemicalEntity", "biolink:enables", "biolink:MolecularActivity", ""),
        (
            "biolink:MolecularActivity",
            "biolink:has_part",
            "biolink:MolecularActivity",
            "",
        ),
        (
            "biolink:CellularComponent",
            "biolink:occurs_in",
            "biolink:GrossAnatomicalStructure",
            "",
        ),
        (
            "biolink:BiologicalProcess",
            "biolink:has_participant",
            "biolink:MolecularActivity",
            "",
        ),
        ("biolink:MolecularMixture", "biolink:affects", "biolink:Gene", ""),
        ("biolink:CellularComponent", "biolink:causes", "biolink:Gene", ""),
        (
            "biolink:BiologicalProcess",
            "biolink:has_participant",
            "biolink:AnatomicalEntity",
            "",
        ),
        (
            "biolink:CellularComponent",
            "biolink:regulates",
            "biolink:BiologicalProcess",
            "",
        ),
        (
            "biolink:CellularComponent",
            "biolink:capable_of",
            "biolink:MolecularActivity",
            "",
        ),
        ("biolink:ChemicalEntity", "biolink:interacts_with", "biolink:Protein", ""),
        ("biolink:BiologicalProcess", "biolink:occurs_in", "biolink:Gene", ""),
        (
            "biolink:Protein",
            "biolink:acts_upstream_of_negative_effect",
            "biolink:Pathway",
            "",
        ),
        ("biolink:MolecularActivity", "biolink:overlaps", "biolink:Pathway", ""),
        (
            "biolink:ChemicalEntity",
            "biolink:interacts_with",
            "biolink:SmallMolecule",
            "",
        ),
        ("biolink:Cell", "biolink:overlaps", "biolink:Gene", ""),
        ("biolink:Gene", "biolink:overlaps", "biolink:Cell", ""),
        (
            "biolink:ComplexMolecularMixture",
            "biolink:affects",
            "biolink:SmallMolecule",
            "",
        ),
        (
            "biolink:Protein",
            "biolink:acts_upstream_of_or_within_negative_effect",
            "biolink:MolecularActivity",
            "",
        ),
        (
            "biolink:ChemicalEntity",
            "biolink:affects",
            "biolink:ComplexMolecularMixture",
            "",
        ),
        ("biolink:CellularComponent", "biolink:occurs_in", "biolink:Cell", ""),
        (
            "biolink:Protein",
            "biolink:acts_upstream_of_or_within",
            "biolink:Pathway",
            "",
        ),
        ("biolink:Pathway", "biolink:has_participant", "biolink:Protein", ""),
        (
            "biolink:Cell",
            "biolink:actively_involved_in",
            "biolink:MolecularActivity",
            "",
        ),
        ("biolink:CellularComponent", "biolink:overlaps", "biolink:Protein", ""),
        ("biolink:AnatomicalEntity", "biolink:has_part", "biolink:Gene", ""),
        ("biolink:CellularComponent", "biolink:affects", "biolink:Polypeptide", ""),
        (
            "biolink:BiologicalProcess",
            "biolink:precedes",
            "biolink:BiologicalProcess",
            "",
        ),
        ("biolink:CellularComponent", "biolink:interacts_with", "biolink:Protein", ""),
        ("biolink:Pathway", "biolink:occurs_in", "biolink:Cell", ""),
        ("biolink:Gene", "biolink:causes", "biolink:CellularComponent", ""),
        (
            "biolink:BiologicalProcess",
            "biolink:occurs_in",
            "biolink:GrossAnatomicalStructure",
            "",
        ),
        (
            "biolink:BiologicalProcess",
            "biolink:occurs_in",
            "biolink:CellularComponent",
            "",
        ),
        (
            "biolink:BiologicalProcess",
            "biolink:has_participant",
            "biolink:ChemicalEntity",
            "",
        ),
        ("biolink:Polypeptide", "biolink:interacts_with", "biolink:ChemicalEntity", ""),
        (
            "biolink:GrossAnatomicalStructure",
            "biolink:has_part",
            "biolink:CellularComponent",
            "",
        ),
        ("biolink:Pathway", "biolink:has_part", "biolink:Pathway", ""),
        (
            "biolink:Polypeptide",
            "biolink:actively_involved_in",
            "biolink:MolecularActivity",
            "",
        ),
        ("biolink:Protein", "biolink:overlaps", "biolink:Cell", ""),
        ("biolink:Polypeptide", "biolink:affects", "biolink:Polypeptide", ""),
        ("biolink:Gene", "biolink:active_in", "biolink:AnatomicalEntity", ""),
        (
            "biolink:BiologicalProcess",
            "biolink:overlaps",
            "biolink:MolecularActivity",
            "",
        ),
        (
            "biolink:MolecularActivity",
            "biolink:has_input",
            "biolink:MacromolecularComplex",
            "",
        ),
        ("biolink:SmallMolecule", "biolink:causes", "biolink:MolecularActivity", ""),
        (
            "biolink:AnatomicalEntity",
            "biolink:has_part",
            "biolink:GrossAnatomicalStructure",
            "",
        ),
        (
            "biolink:AnatomicalEntity",
            "biolink:has_part",
            "biolink:CellularComponent",
            "",
        ),
        ("biolink:Gene", "biolink:causes", "biolink:AnatomicalEntity", ""),
        ("biolink:BiologicalProcess", "biolink:affects", "biolink:Cell", ""),
        (
            "biolink:AnatomicalEntity",
            "biolink:overlaps",
            "biolink:AnatomicalEntity",
            "",
        ),
        (
            "biolink:Protein",
            "biolink:acts_upstream_of_or_within_negative_effect",
            "biolink:Pathway",
            "",
        ),
        ("biolink:SmallMolecule", "biolink:affects", "biolink:Gene", ""),
        ("biolink:BiologicalProcess", "biolink:has_output", "biolink:Cell", ""),
        (
            "biolink:Gene",
            "biolink:acts_upstream_of_or_within_positive_effect",
            "biolink:Pathway",
            "",
        ),
        (
            "biolink:GrossAnatomicalStructure",
            "biolink:has_part",
            "biolink:AnatomicalEntity",
            "",
        ),
        (
            "biolink:CellularComponent",
            "biolink:acts_upstream_of_or_within",
            "biolink:BiologicalProcess",
            "",
        ),
        ("biolink:BiologicalProcess", "biolink:affects", "biolink:Gene", ""),
        (
            "biolink:CellularComponent",
            "biolink:acts_upstream_of_or_within_positive_effect",
            "biolink:BiologicalProcess",
            "",
        ),
        ("biolink:Protein", "biolink:regulates", "biolink:Gene", ""),
        ("biolink:Polypeptide", "biolink:causes", "biolink:Protein", ""),
        ("biolink:BiologicalProcess", "biolink:has_output", "biolink:Gene", ""),
        ("biolink:Polypeptide", "biolink:causes", "biolink:SmallMolecule", ""),
        (
            "biolink:MolecularActivity",
            "biolink:has_input",
            "biolink:ChemicalEntity",
            "",
        ),
        ("biolink:ComplexMolecularMixture", "biolink:causes", "biolink:Gene", ""),
        ("biolink:MolecularActivity", "biolink:has_output", "biolink:Polypeptide", ""),
        (
            "biolink:BiologicalProcess",
            "biolink:has_input",
            "biolink:AnatomicalEntity",
            "",
        ),
        ("biolink:MolecularActivity", "biolink:enabled_by", "biolink:Gene", ""),
        ("biolink:Protein", "biolink:affects", "biolink:ChemicalEntity", ""),
        ("biolink:SmallMolecule", "biolink:affects", "biolink:CellularComponent", ""),
        ("biolink:CellularComponent", "biolink:affects", "biolink:ChemicalMixture", ""),
        (
            "biolink:Gene",
            "biolink:acts_upstream_of_or_within",
            "biolink:CellularComponent",
            "",
        ),
        ("biolink:SmallMolecule", "biolink:causes", "biolink:ChemicalEntity", ""),
        ("biolink:Gene", "biolink:causes", "biolink:Pathway", ""),
        ("biolink:Protein", "biolink:preceded_by", "biolink:Polypeptide", ""),
        ("biolink:Polypeptide", "biolink:affects", "biolink:SmallMolecule", ""),
        ("biolink:MolecularMixture", "biolink:causes", "biolink:Polypeptide", ""),
        ("biolink:Gene", "biolink:capable_of", "biolink:CellularComponent", ""),
        ("biolink:Gene", "biolink:has_input", "biolink:Gene", ""),
        (
            "biolink:CellularComponent",
            "biolink:directly_physically_interacts_with",
            "biolink:Protein",
            "",
        ),
        ("biolink:Gene", "biolink:overlaps", "biolink:GrossAnatomicalStructure", ""),
        ("biolink:Protein", "biolink:interacts_with", "biolink:Polypeptide", ""),
        (
            "biolink:MolecularActivity",
            "biolink:has_input",
            "biolink:MolecularActivity",
            "",
        ),
        ("biolink:Polypeptide", "biolink:located_in", "biolink:CellularComponent", ""),
        ("biolink:Polypeptide", "biolink:causes", "biolink:MolecularMixture", ""),
        (
            "biolink:Polypeptide",
            "biolink:acts_upstream_of_or_within_positive_effect",
            "biolink:MolecularActivity",
            "",
        ),
        ("biolink:CellularComponent", "biolink:located_in", "biolink:Cell", ""),
        (
            "biolink:Gene",
            "biolink:acts_upstream_of_negative_effect",
            "biolink:MolecularActivity",
            "",
        ),
        ("biolink:BiologicalProcess", "biolink:overlaps", "biolink:Pathway", ""),
        ("biolink:Gene", "biolink:affects", "biolink:ChemicalEntity", ""),
        (
            "biolink:MolecularActivity",
            "biolink:occurs_in",
            "biolink:CellularComponent",
            "",
        ),
        (
            "biolink:MolecularActivity",
            "biolink:enabled_by",
            "biolink:CellularComponent",
            "",
        ),
        (
            "biolink:MolecularActivity",
            "biolink:has_participant",
            "biolink:ChemicalEntity",
            "",
        ),
        ("biolink:Gene", "biolink:causes", "biolink:ComplexMolecularMixture", ""),
        (
            "biolink:CellularComponent",
            "biolink:coexists_with",
            "biolink:CellularComponent",
            "",
        ),
        ("biolink:MolecularActivity", "biolink:affects", "biolink:SmallMolecule", ""),
        (
            "biolink:Pathway",
            "biolink:occurs_in",
            "biolink:GrossAnatomicalStructure",
            "",
        ),
        ("biolink:Gene", "biolink:causes", "biolink:BiologicalProcess", ""),
        (
            "biolink:SmallMolecule",
            "biolink:capable_of",
            "biolink:MolecularActivity",
            "",
        ),
        ("biolink:Protein", "biolink:causes", "biolink:Pathway", ""),
        ("biolink:Pathway", "biolink:occurs_in", "biolink:CellularComponent", ""),
        ("biolink:Gene", "biolink:regulates", "biolink:MolecularActivity", ""),
        (
            "biolink:GrossAnatomicalStructure",
            "biolink:has_part",
            "biolink:BiologicalProcess",
            "",
        ),
        ("biolink:CellularComponent", "biolink:causes", "biolink:Polypeptide", ""),
        ("biolink:Polypeptide", "biolink:precedes", "biolink:Protein", ""),
        ("biolink:Protein", "biolink:overlaps", "biolink:GrossAnatomicalStructure", ""),
        (
            "biolink:BiologicalProcess",
            "biolink:has_participant",
            "biolink:ComplexMolecularMixture",
            "",
        ),
        ("biolink:CellularComponent", "biolink:regulates", "biolink:Gene", ""),
        ("biolink:Protein", "biolink:overlaps", "biolink:CellularComponent", ""),
        ("biolink:Polypeptide", "biolink:has_part", "biolink:SmallMolecule", ""),
        (
            "biolink:MolecularActivity",
            "biolink:occurs_in",
            "biolink:AnatomicalEntity",
            "",
        ),
        ("biolink:Gene", "biolink:interacts_with", "biolink:Protein", ""),
        (
            "biolink:Polypeptide",
            "biolink:acts_upstream_of_or_within",
            "biolink:Pathway",
            "",
        ),
        ("biolink:MolecularActivity", "biolink:has_output", "biolink:Protein", ""),
        ("biolink:CellularComponent", "biolink:affects", "biolink:Gene", ""),
        ("biolink:Polypeptide", "biolink:affects", "biolink:ChemicalEntity", ""),
        ("biolink:ChemicalEntity", "biolink:affects", "biolink:MolecularMixture", ""),
        (
            "biolink:Protein",
            "biolink:acts_upstream_of_positive_effect",
            "biolink:MolecularActivity",
            "",
        ),
        (
            "biolink:BiologicalProcess",
            "biolink:affects",
            "biolink:CellularComponent",
            "",
        ),
        (
            "biolink:MolecularActivity",
            "biolink:has_output",
            "biolink:SmallMolecule",
            "",
        ),
        (
            "biolink:BiologicalProcess",
            "biolink:has_output",
            "biolink:GrossAnatomicalStructure",
            "",
        ),
        (
            "biolink:MolecularActivity",
            "biolink:overlaps",
            "biolink:BiologicalProcess",
            "",
        ),
        ("biolink:Gene", "biolink:located_in", "biolink:Cell", ""),
        (
            "biolink:Gene",
            "biolink:acts_upstream_of_or_within_negative_effect",
            "biolink:MolecularActivity",
            "",
        ),
        ("biolink:Polypeptide", "biolink:regulates", "biolink:MolecularActivity", ""),
        ("biolink:BiologicalProcess", "biolink:has_part", "biolink:Gene", ""),
        ("biolink:Drug", "biolink:affects", "biolink:Gene", ""),
        (
            "biolink:Gene",
            "biolink:acts_upstream_of_negative_effect",
            "biolink:Pathway",
            "",
        ),
        ("biolink:Pathway", "biolink:regulates", "biolink:BiologicalProcess", ""),
        (
            "biolink:Protein",
            "biolink:directly_physically_interacts_with",
            "biolink:Polypeptide",
            "",
        ),
        ("biolink:Gene", "biolink:enables", "biolink:MolecularActivity", ""),
        ("biolink:ChemicalEntity", "biolink:affects", "biolink:CellularComponent", ""),
        (
            "biolink:BiologicalProcess",
            "biolink:temporally_related_to",
            "biolink:BiologicalProcess",
            "",
        ),
        ("biolink:CellularComponent", "biolink:has_part", "biolink:Gene", ""),
        ("biolink:MolecularActivity", "biolink:preceded_by", "biolink:Polypeptide", ""),
        ("biolink:Polypeptide", "biolink:causes", "biolink:CellularComponent", ""),
        (
            "biolink:SmallMolecule",
            "biolink:acts_upstream_of_or_within_positive_effect",
            "biolink:BiologicalProcess",
            "",
        ),
        (
            "biolink:BiologicalProcess",
            "biolink:has_part",
            "biolink:CellularComponent",
            "",
        ),
        (
            "biolink:AnatomicalEntity",
            "biolink:has_part",
            "biolink:BiologicalProcess",
            "",
        ),
        ("biolink:Gene", "biolink:interacts_with", "biolink:SmallMolecule", ""),
        (
            "biolink:CellularComponent",
            "biolink:located_in",
            "biolink:CellularComponent",
            "",
        ),
        ("biolink:Cell", "biolink:has_part", "biolink:CellularComponent", ""),
        ("biolink:CellularComponent", "biolink:affects", "biolink:ChemicalEntity", ""),
        (
            "biolink:ChemicalEntity",
            "biolink:actively_involved_in",
            "biolink:BiologicalProcess",
            "",
        ),
        ("biolink:Protein", "biolink:enables", "biolink:MolecularActivity", ""),
        (
            "biolink:BiologicalProcess",
            "biolink:has_participant",
            "biolink:ChemicalMixture",
            "",
        ),
        ("biolink:Gene", "biolink:interacts_with", "biolink:MolecularActivity", ""),
        ("biolink:Pathway", "biolink:preceded_by", "biolink:MolecularActivity", ""),
        (
            "biolink:CellularComponent",
            "biolink:actively_involved_in",
            "biolink:BiologicalProcess",
            "",
        ),
        ("biolink:SmallMolecule", "biolink:regulates", "biolink:BiologicalProcess", ""),
        (
            "biolink:BiologicalProcess",
            "biolink:has_input",
            "biolink:ChemicalMixture",
            "",
        ),
        (
            "biolink:CellularComponent",
            "biolink:directly_physically_interacts_with",
            "biolink:CellularComponent",
            "",
        ),
        ("biolink:Protein", "biolink:causes", "biolink:ChemicalMixture", ""),
        (
            "biolink:Gene",
            "biolink:acts_upstream_of_positive_effect",
            "biolink:CellularComponent",
            "",
        ),
        (
            "biolink:CellularComponent",
            "biolink:active_in",
            "biolink:CellularComponent",
            "",
        ),
        (
            "biolink:BiologicalProcess",
            "biolink:causes",
            "biolink:MolecularActivity",
            "",
        ),
        (
            "biolink:Polypeptide",
            "biolink:acts_upstream_of_or_within",
            "biolink:BiologicalProcess",
            "",
        ),
        ("biolink:Polypeptide", "biolink:interacts_with", "biolink:Protein", ""),
        (
            "biolink:Gene",
            "biolink:acts_upstream_of_or_within",
            "biolink:BiologicalProcess",
            "",
        ),
        ("biolink:MolecularActivity", "biolink:precedes", "biolink:Protein", ""),
        ("biolink:Polypeptide", "biolink:interacts_with", "biolink:SmallMolecule", ""),
        ("biolink:AnatomicalEntity", "biolink:affects", "biolink:Gene", ""),
        (
            "biolink:BiologicalProcess",
            "biolink:affects",
            "biolink:BiologicalProcess",
            "",
        ),
        ("biolink:BiologicalProcess", "biolink:occurs_in", "biolink:Cell", ""),
        ("biolink:Gene", "biolink:capable_of", "biolink:BiologicalProcess", ""),
        (
            "biolink:Protein",
            "biolink:directly_physically_interacts_with",
            "biolink:Protein",
            "",
        ),
        ("biolink:Gene", "biolink:causes", "biolink:ChemicalMixture", ""),
        ("biolink:MolecularMixture", "biolink:affects", "biolink:Polypeptide", ""),
        ("biolink:Gene", "biolink:interacts_with", "biolink:ChemicalEntity", ""),
        ("biolink:Gene", "biolink:causes", "biolink:Gene", ""),
        ("biolink:CellularComponent", "biolink:causes", "biolink:SmallMolecule", ""),
        (
            "biolink:MolecularActivity",
            "biolink:has_output",
            "biolink:ChemicalEntity",
            "",
        ),
        ("biolink:Protein", "biolink:located_in", "biolink:AnatomicalEntity", ""),
        ("biolink:AnatomicalEntity", "biolink:has_part", "biolink:Cell", ""),
        (
            "biolink:CellularComponent",
            "biolink:acts_upstream_of_positive_effect",
            "biolink:MolecularActivity",
            "",
        ),
        (
            "biolink:BiologicalProcess",
            "biolink:has_participant",
            "biolink:MolecularMixture",
            "",
        ),
        ("biolink:Polypeptide", "biolink:precedes", "biolink:MolecularActivity", ""),
        (
            "biolink:CellularComponent",
            "biolink:acts_upstream_of_negative_effect",
            "biolink:MolecularActivity",
            "",
        ),
        (
            "biolink:MolecularActivity",
            "biolink:preceded_by",
            "biolink:MolecularActivity",
            "",
        ),
        (
            "biolink:Gene",
            "biolink:acts_upstream_of_or_within_negative_effect",
            "biolink:Pathway",
            "",
        ),
        ("biolink:Protein", "biolink:actively_involved_in", "biolink:Pathway", ""),
        ("biolink:MolecularMixture", "biolink:causes", "biolink:ChemicalEntity", ""),
        ("biolink:MolecularActivity", "biolink:has_input", "biolink:SmallMolecule", ""),
        (
            "biolink:BiologicalProcess",
            "biolink:has_input",
            "biolink:MolecularMixture",
            "",
        ),
        ("biolink:Protein", "biolink:precedes", "biolink:MolecularActivity", ""),
        ("biolink:BiologicalProcess", "biolink:has_input", "biolink:Gene", ""),
        (
            "biolink:BiologicalProcess",
            "biolink:regulates",
            "biolink:BiologicalProcess",
            "",
        ),
        ("biolink:Protein", "biolink:interacts_with", "biolink:ChemicalEntity", ""),
        ("biolink:Polypeptide", "biolink:causes", "biolink:BiologicalProcess", ""),
        (
            "biolink:CellularComponent",
            "biolink:acts_upstream_of_or_within",
            "biolink:MolecularActivity",
            "",
        ),
        ("biolink:Protein", "biolink:causes", "biolink:MolecularMixture", ""),
        ("biolink:Protein", "biolink:causes", "biolink:Gene", ""),
        (
            "biolink:Protein",
            "biolink:actively_involved_in",
            "biolink:MolecularActivity",
            "",
        ),
        ("biolink:Protein", "biolink:affects", "biolink:Protein", ""),
        (
            "biolink:BiologicalProcess",
            "biolink:preceded_by",
            "biolink:BiologicalProcess",
            "",
        ),
        (
            "biolink:Gene",
            "biolink:acts_upstream_of_positive_effect",
            "biolink:Pathway",
            "",
        ),
        (
            "biolink:MolecularActivity",
            "biolink:regulates",
            "biolink:CellularComponent",
            "",
        ),
        ("biolink:SmallMolecule", "biolink:causes", "biolink:Protein", ""),
        ("biolink:Gene", "biolink:regulates", "biolink:Protein", ""),
        ("biolink:SmallMolecule", "biolink:causes", "biolink:SmallMolecule", ""),
        ("biolink:Cell", "biolink:has_part", "biolink:BiologicalProcess", ""),
        ("biolink:Gene", "biolink:actively_involved_in", "biolink:Pathway", ""),
        ("biolink:Protein", "biolink:preceded_by", "biolink:MolecularActivity", ""),
        (
            "biolink:Gene",
            "biolink:acts_upstream_of_or_within_positive_effect",
            "biolink:CellularComponent",
            "",
        ),
        ("biolink:CellularComponent", "biolink:causes", "biolink:ChemicalEntity", ""),
        ("biolink:Gene", "biolink:affects", "biolink:Protein", ""),
        (
            "biolink:BiologicalProcess",
            "biolink:has_input",
            "biolink:CellularComponent",
            "",
        ),
        ("biolink:Gene", "biolink:causes", "biolink:Cell", ""),
        (
            "biolink:CellularComponent",
            "biolink:interacts_with",
            "biolink:ChemicalMixture",
            "",
        ),
        ("biolink:SmallMolecule", "biolink:affects", "biolink:Polypeptide", ""),
        ("biolink:Gene", "biolink:affects", "biolink:SmallMolecule", ""),
        ("biolink:AnatomicalEntity", "biolink:overlaps", "biolink:Cell", ""),
        ("biolink:ChemicalEntity", "biolink:causes", "biolink:Polypeptide", ""),
        ("biolink:MolecularActivity", "biolink:has_participant", "biolink:Protein", ""),
        (
            "biolink:Gene",
            "biolink:acts_upstream_of_positive_effect",
            "biolink:BiologicalProcess",
            "",
        ),
        ("biolink:Pathway", "biolink:causes", "biolink:MolecularActivity", ""),
        ("biolink:GrossAnatomicalStructure", "biolink:has_part", "biolink:Cell", ""),
        (
            "biolink:MolecularActivity",
            "biolink:has_participant",
            "biolink:SmallMolecule",
            "",
        ),
        (
            "biolink:MolecularActivity",
            "biolink:precedes",
            "biolink:MolecularActivity",
            "",
        ),
        (
            "biolink:SmallMolecule",
            "biolink:located_in",
            "biolink:CellularComponent",
            "",
        ),
        (
            "biolink:CellularComponent",
            "biolink:acts_upstream_of_or_within_negative_effect",
            "biolink:MolecularActivity",
            "",
        ),
        ("biolink:Protein", "biolink:regulates", "biolink:Protein", ""),
        ("biolink:SmallMolecule", "biolink:causes", "biolink:MolecularMixture", ""),
        ("biolink:Pathway", "biolink:preceded_by", "biolink:Pathway", ""),
        ("biolink:AnatomicalEntity", "biolink:overlaps", "biolink:Gene", ""),
        (
            "biolink:Protein",
            "biolink:acts_upstream_of_or_within",
            "biolink:CellularComponent",
            "",
        ),
        ("biolink:CellularComponent", "biolink:coexists_with", "biolink:Cell", ""),
        (
            "biolink:Protein",
            "biolink:acts_upstream_of_or_within_positive_effect",
            "biolink:CellularComponent",
            "",
        ),
        (
            "biolink:CellularComponent",
            "biolink:causes",
            "biolink:MolecularActivity",
            "",
        ),
        (
            "biolink:BiologicalProcess",
            "biolink:has_part",
            "biolink:BiologicalProcess",
            "",
        ),
        ("biolink:Polypeptide", "biolink:enables", "biolink:MolecularActivity", ""),
        ("biolink:BiologicalProcess", "biolink:causes", "biolink:Pathway", ""),
        (
            "biolink:GrossAnatomicalStructure",
            "biolink:has_part",
            "biolink:GrossAnatomicalStructure",
            "",
        ),
        ("biolink:Protein", "biolink:affects", "biolink:SmallMolecule", ""),
        ("biolink:Gene", "biolink:affects", "biolink:MolecularMixture", ""),
        ("biolink:MolecularActivity", "biolink:has_input", "biolink:Protein", ""),
        ("biolink:ChemicalEntity", "biolink:interacts_with", "biolink:Gene", ""),
        ("biolink:MolecularActivity", "biolink:interacts_with", "biolink:Gene", ""),
        (
            "biolink:BiologicalProcess",
            "biolink:has_participant",
            "biolink:GrossAnatomicalStructure",
            "",
        ),
        ("biolink:SmallMolecule", "biolink:located_in", "biolink:AnatomicalEntity", ""),
        (
            "biolink:MolecularActivity",
            "biolink:has_participant",
            "biolink:MolecularMixture",
            "",
        ),
        (
            "biolink:BiologicalProcess",
            "biolink:has_participant",
            "biolink:CellularComponent",
            "",
        ),
        (
            "biolink:Pathway",
            "biolink:temporally_related_to",
            "biolink:BiologicalProcess",
            "",
        ),
        ("biolink:MolecularActivity", "biolink:regulates", "biolink:Pathway", ""),
        ("biolink:Gene", "biolink:acts_upstream_of_or_within", "biolink:Cell", ""),
        ("biolink:Pathway", "biolink:has_participant", "biolink:MolecularMixture", ""),
        ("biolink:ChemicalMixture", "biolink:causes", "biolink:Gene", ""),
        ("biolink:Pathway", "biolink:has_participant", "biolink:Gene", ""),
        ("biolink:Pathway", "biolink:causes", "biolink:Pathway", ""),
        ("biolink:MolecularActivity", "biolink:precedes", "biolink:Pathway", ""),
        ("biolink:Protein", "biolink:causes", "biolink:CellularComponent", ""),
        (
            "biolink:MolecularActivity",
            "biolink:has_part",
            "biolink:BiologicalProcess",
            "",
        ),
        (
            "biolink:MolecularActivity",
            "biolink:occurs_in",
            "biolink:GrossAnatomicalStructure",
            "",
        ),
        (
            "biolink:CellularComponent",
            "biolink:interacts_with",
            "biolink:MolecularMixture",
            "",
        ),
        ("biolink:Pathway", "biolink:has_input", "biolink:Gene", ""),
        ("biolink:CellularComponent", "biolink:interacts_with", "biolink:Gene", ""),
        (
            "biolink:MolecularMixture",
            "biolink:interacts_with",
            "biolink:CellularComponent",
            "",
        ),
        ("biolink:Pathway", "biolink:precedes", "biolink:Pathway", ""),
        (
            "biolink:ChemicalEntity",
            "biolink:interacts_with",
            "biolink:CellularComponent",
            "",
        ),
        ("biolink:Pathway", "biolink:has_part", "biolink:BiologicalProcess", ""),
        ("biolink:CellularComponent", "biolink:causes", "biolink:Pathway", ""),
        ("biolink:ChemicalEntity", "biolink:causes", "biolink:Protein", ""),
        ("biolink:Gene", "biolink:active_in", "biolink:CellularComponent", ""),
        (
            "biolink:MolecularActivity",
            "biolink:enabled_by",
            "biolink:ChemicalEntity",
            "",
        ),
        ("biolink:MolecularActivity", "biolink:occurs_in", "biolink:Cell", ""),
        (
            "biolink:CellularComponent",
            "biolink:interacts_with",
            "biolink:CellularComponent",
            "",
        ),
        ("biolink:CellularComponent", "biolink:affects", "biolink:Protein", ""),
        (
            "biolink:BiologicalProcess",
            "biolink:affects",
            "biolink:MacromolecularComplex",
            "",
        ),
        (
            "biolink:BiologicalProcess",
            "biolink:overlaps",
            "biolink:CellularComponent",
            "",
        ),
        ("biolink:CellularComponent", "biolink:affects", "biolink:SmallMolecule", ""),
        (
            "biolink:Protein",
            "biolink:acts_upstream_of_or_within",
            "biolink:BiologicalProcess",
            "",
        ),
        ("biolink:Polypeptide", "biolink:actively_involved_in", "biolink:Pathway", ""),
        ("biolink:Protein", "biolink:regulates", "biolink:MolecularActivity", ""),
        (
            "biolink:AnatomicalEntity",
            "biolink:overlaps",
            "biolink:CellularComponent",
            "",
        ),
        ("biolink:SmallMolecule", "biolink:causes", "biolink:CellularComponent", ""),
        ("biolink:Protein", "biolink:capable_of", "biolink:MolecularActivity", ""),
        ("biolink:Polypeptide", "biolink:causes", "biolink:Gene", ""),
        ("biolink:GrossAnatomicalStructure", "biolink:overlaps", "biolink:Protein", ""),
        (
            "biolink:ChemicalEntity",
            "biolink:located_in",
            "biolink:CellularComponent",
            "",
        ),
        ("biolink:Polypeptide", "biolink:affects", "biolink:Protein", ""),
        ("biolink:ComplexMolecularMixture", "biolink:affects", "biolink:Gene", ""),
        ("biolink:Cell", "biolink:coexists_with", "biolink:CellularComponent", ""),
        ("biolink:Cell", "biolink:has_part", "biolink:Gene", ""),
        ("biolink:MolecularMixture", "biolink:affects", "biolink:ChemicalEntity", ""),
        ("biolink:Polypeptide", "biolink:overlaps", "biolink:Polypeptide", ""),
        ("biolink:CellularComponent", "biolink:active_in", "biolink:Cell", ""),
        (
            "biolink:ComplexMolecularMixture",
            "biolink:causes",
            "biolink:ChemicalEntity",
            "",
        ),
        ("biolink:ChemicalEntity", "biolink:causes", "biolink:SmallMolecule", ""),
        (
            "biolink:MolecularMixture",
            "biolink:regulates",
            "biolink:MolecularActivity",
            "",
        ),
        ("biolink:Pathway", "biolink:has_participant", "biolink:CellularComponent", ""),
        ("biolink:CellularComponent", "biolink:has_part", "biolink:Protein", ""),
        ("biolink:Gene", "biolink:precedes", "biolink:MolecularActivity", ""),
        (
            "biolink:CellularComponent",
            "biolink:directly_physically_interacts_with",
            "biolink:Gene",
            "",
        ),
        (
            "biolink:Protein",
            "biolink:acts_upstream_of_or_within_negative_effect",
            "biolink:BiologicalProcess",
            "",
        ),
        (
            "biolink:SmallMolecule",
            "biolink:actively_involved_in",
            "biolink:BiologicalProcess",
            "",
        ),
        (
            "biolink:Gene",
            "biolink:acts_upstream_of_or_within_positive_effect",
            "biolink:BiologicalProcess",
            "",
        ),
        ("biolink:ChemicalEntity", "biolink:causes", "biolink:MolecularActivity", ""),
        ("biolink:SmallMolecule", "biolink:interacts_with", "biolink:Polypeptide", ""),
        ("biolink:Gene", "biolink:affects", "biolink:AnatomicalEntity", ""),
        ("biolink:Polypeptide", "biolink:regulates", "biolink:Protein", ""),
        ("biolink:Pathway", "biolink:precedes", "biolink:BiologicalProcess", ""),
        ("biolink:Protein", "biolink:causes", "biolink:BiologicalProcess", ""),
        ("biolink:ChemicalEntity", "biolink:affects", "biolink:Gene", ""),
        ("biolink:MolecularActivity", "biolink:affects", "biolink:Gene", ""),
        (
            "biolink:Gene",
            "biolink:acts_upstream_of_negative_effect",
            "biolink:CellularComponent",
            "",
        ),
    }
    assert (
        edge_tuples == edge_tuples_expected
    ), "Found differences between edge types in MetaKG and expected edge types."


def test_simple_spec():
    """
    Test the GET /cam-kp/simple_spec endpoint.
    """
    simple_spec_tests = [
        {
            "source": "UBERON:0002240",
            "target": "NCBIGene:15481",
            # TODO: wait, what?
            "expected_predicates": {"biolink:overlaps"},
        }
    ]

    simple_spec_endpoint = urllib.parse.urljoin(CAM_KP_API_ENDPOINT, "simple_spec")
    for simple_spec_test in simple_spec_tests:
        response = requests.get(
            simple_spec_endpoint,
            {
                "source": simple_spec_test["source"],
                "target": simple_spec_test["target"],
            },
        )
        assert (
            response.ok
        ), f"Unable to look up {simple_spec_endpoint} with source: {simple_spec_test['source']} and target: {simple_spec_test['target']}."
        predicates = set(map(lambda res: res["edge_type"], response.json()))
        logging.debug(
            f"Retrieved predicates predicates_for_edge for {simple_spec_test['source']} to {simple_spec_test['target']}: {predicates}"
        )

        assert (
            simple_spec_test["expected_predicates"] == predicates
        ), f"When querying for {simple_spec_test['source']} to {simple_spec_test['target']}, expected predicates {simple_spec_test['expected_predicates']} did not match {predicates}."


def test_source_target_curie_one_hop_and_simple_spec():
    """
    Test the GET /cam-kp/{source_type}/{target_type}/{curie} endpoint and the /cam-kp/simple_spec endpoint.
    """
    source_target_curies = [
        {
            "source_type": "biolink:AnatomicalEntity",
            "target_type": "biolink:Gene",
            "curie": "UBERON:0002240",
            "expected_node_ids": {"UBERON:0002240", "NCBIGene:15481"},
            "expected_xrefs": {"http://model.geneontology.org/SYNGO_2911"},
            "expected_predicates": {},
            "expected_knowledge_sources": {"infores:go-cam"},
        }
    ]

    for source_target_curie in source_target_curies:
        source_target_url = (
            CAM_KP_API_ENDPOINT
            + f"{source_target_curie['source_type']}/{source_target_curie['target_type']}/{source_target_curie['curie']}"
        )
        response = requests.get(source_target_url)
        assert (
            response.ok
        ), f"Could not retrieve source-target-curie response from {source_target_url}."
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

        assert (
            source_target_curie["expected_node_ids"] <= node_ids
        ), f"All node IDs in {source_target_curie['expected_node_ids']} are not present in the list of node IDs obtained: {node_ids}"
        assert (
            source_target_curie["expected_xrefs"] <= xrefs
        ), f"All expected xrefs in {source_target_curie['expected_xrefs']} are not present in the list of xrefs obtained: {xrefs}"
        assert (
            source_target_curie["expected_knowledge_sources"] <= knowledge_sources
        ), f"All expected knowledge sources in {source_target_curie['expected_knowledge_sources']} are not present in the list of knowledge sources obtained: {knowledge_sources}"


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


def test_query():
    f"""
    Test the POST /cam-kp/{TRAPI_VERSION}/query endpoint.
    """

    query_post_url = f"{CAM_KP_API_ENDPOINT}{TRAPI_VERSION}/query"
    response = requests.post(query_post_url, json=trapi_query_what_is_hsp8_mus_musculus_active_in)
    assert response.ok, f"Got response {response} when attempting to post example TRAPI message to {query_post_url}: {trapi_query_what_is_hsp8_mus_musculus_active_in}"

    assert "message" in response.json()
    message = response.json()["message"]

    assert "query_graph" in message
    assert "knowledge_graph" in message

    # Check the knowledge graph nodes
    assert "nodes" in message["knowledge_graph"]
    nodes = message["knowledge_graph"]["nodes"]
    node_ids = set(nodes.keys())

    assert len(node_ids) > 0
    assert "UBERON:0002240" in node_ids
    assert nodes["UBERON:0002240"]["name"] == "spinal cord"

    # Check the knowledge graph edges
    assert "edges" in message["knowledge_graph"]
    edges = message["knowledge_graph"]["edges"]

    edge_values_spinal_cord = list(filter(lambda edge: edge["object"] == "UBERON:0002240", edges.values()))
    assert len(edge_values_spinal_cord) == 1
    spinal_cord_edge = edge_values_spinal_cord[0]

    assert spinal_cord_edge["subject"] == "NCBIGene:15481"
    assert spinal_cord_edge["predicate"] == "biolink:active_in"
    assert spinal_cord_edge["object"] == "UBERON:0002240"
    assert spinal_cord_edge["sources"] == [
        {
            "resource_id": "infores:automat-cam-kp",
            "resource_role": "aggregator_knowledge_source",
            "upstream_resource_ids": [
                "infores:go-cam"
            ],
            "source_record_urls": None
        },
        {
            "resource_id": "infores:go-cam",
            "resource_role": "primary_knowledge_source",
            "upstream_resource_ids": None,
            "source_record_urls": None,
        }
    ]
    assert spinal_cord_edge["qualifiers"] is None
    assert spinal_cord_edge["attributes"] == [
        {
            "attribute_type_id": "biolink:xref",
            "value": [
                "http://model.geneontology.org/SYNGO_2911"
            ],
            "value_type_id": "EDAM:data_0006",
            "original_attribute_name": "xref",
            "value_url": None,
            "attribute_source": None,
            "description": None,
            "attributes": None,
        }
    ]

