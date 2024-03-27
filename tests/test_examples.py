#
# test_examples.py
#
# Test the example files in ./examples and ensure we are getting roughly the right number of results.
#
import json
import os
import pytest
import requests

CAM_KP_API_ENDPOINT = os.getenv(
    "CAM_KP_API_ENDPOINT", "https://automat.renci.org/cam-kp/"
)
TRAPI_VERSION = os.getenv("TRAPI_VERSION", "1.4")

script_dir = os.path.dirname(os.path.abspath(__file__))
example_files_to_test = [
    file for file in os.listdir(os.path.join(script_dir, "examples")) if file.lower().endswith(".json")
]


# Test assertions.
def assertion_expected_result_counts(assertion: dict, response_json):
    """
    Assert expected result counts.

    :param assertion: The assertion to test.
    :param response_json: The response from Automat-CAM-KP to check the assertion against.
    """

    # We only expect a certain set of keys in the assertion.
    expected_keys = {"type", "description", "min", "max"}
    unexpected_keys = [key for key in assertion if key not in expected_keys]
    assert len(unexpected_keys) == 0, f"ExpectedResultCount contains unexpected keys: {unexpected_keys}"

    # Assert those keys.
    did_we_test_anything = False

    results = response_json["message"]["results"]
    results_count = len(results)
    if "min" in assertion:
        did_we_test_anything = True
        assert results_count >= assertion["min"], f"Expected a minimum of {assertion['min']} results, but got {results_count} results instead."

    if "max" in assertion:
        did_we_test_anything = True
        assert results_count <= assertion["max"], f"Expected a maximum of {assertion['max']} results, but got {results_count} results instead."

    if not did_we_test_anything:
        assert False, f"Effectively empty ExpectedResultCounts assertion {assertion}"


def assertion_expected_node_results(assertion: dict, response_json):
    """
    Assert expected node results.

    :param assertion: The assertion to test.
    :param response_json: The response from Automat-CAM-KP to check the assertion against.
    """

    # We only expect a certain set of keys in the assertion.
    expected_keys = {"type", "description", "node", "resultEquals", "resultIncludes", "resultExcludes"}
    unexpected_keys = [key for key in assertion if key not in expected_keys]
    assert len(unexpected_keys) == 0, f"ExpectedNodeResults contains unexpected keys: {unexpected_keys}"

    # We always have a node we're comparing values to.
    assert "node" in assertion, f"Assertion ExpectedNodeResults does not contain a 'node': {assertion}"
    node_id = assertion["node"]

    # Assert those keys.
    did_we_test_anything = False

    results = response_json["message"]["results"]
    node_results = set()
    for result in results:
        node_bindings = result["node_bindings"]
        assert node_id in node_bindings, f"Node binding does not contain node {node_id}: {node_bindings}"
        node_values = node_bindings[node_id]
        for nv in node_values:
            node_results.add(nv["id"])

    if "resultEquals" in assertion:
        did_we_test_anything = True
        assert node_results == set(assertion["resultEquals"]), f"Results for node {node_id} do not exactly match expected {assertion['resultEquals']}: {node_results}"

    if "resultIncludes" in assertion:
        did_we_test_anything = True
        assert node_results >= set(assertion["resultIncludes"]),\
            f"Results for node {node_id} do not include {assertion['resultIncludes']}: {node_results}"

    if "resultExcludes" in assertion:
        did_we_test_anything = True
        assert node_results.isdisjoint(set(assertion["resultExcludes"])),\
            f"Results for node {node_id} do not exclude {assertion['resultExcludes']}: {node_results}"

    if not did_we_test_anything:
        assert False, f"Effectively empty ExpectedNodeResults assertion {assertion}"


@pytest.mark.parametrize('example_filename', example_files_to_test)
def test_example(example_filename):
    f"""
    Test the example files in the example directory.
    
    Each example file is expected to have three top-level sections:
    - `meta`: a dictionary describing the example.
        - `description`: A human-readable description of this example.
    - `query`: the TRAPI query to be sent to Automat-CAM-KP.
    - `assertions`: A list of assertions to test against the example file. An empty list is an error.
    """

    example_file = os.path.join(script_dir, "examples", example_filename)
    with open(example_file, "r") as f:
        example = json.load(f)

    # Run some checks on the example.
    for section in ["meta", "query", "assertions"]:
        assert section in example, f"No `{section}` section found in example {example_filename}."
        assert example[section], f"Empty `{section}` section found in example {example_filename}."
    assert len(example["assertions"]) > 0, f"No assertions found in example {example_filename}"

    trapi_query = example["query"]
    query_post_url = f"{CAM_KP_API_ENDPOINT}{TRAPI_VERSION}/query"
    response = requests.post(query_post_url, json=trapi_query)
    assert response.ok, f"Got response {response} when attempting to post example TRAPI message to {query_post_url}: {trapi_query}"

    response_json = response.json()
    assert "message" in response_json
    message = response_json["message"]

    assert "query_graph" in message
    assert "knowledge_graph" in message
    assert "results" in message

    # Check the assertions
    for assertion in example["assertions"]:
        match assertion["type"]:
            case "ExpectedResultCounts":
                assertion_expected_result_counts(assertion, response_json)
            case "ExpectedNodeResults":
                assertion_expected_node_results(assertion, response_json)
            case unknown_type:
                assert False, f"Unknown assertion type {unknown_type} in assertion: {assertion}"
