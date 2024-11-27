# CAM Pipeline Test Examples

This directory contains JSON files describing test cases that can be used to test a
CAM Pipeline instance.

## Test example format

Every JSON file in this directory should be in the following format:

```json
{
  "meta": {
    "description": "A description of the test suite goes here."
  }
}
```

The following top-level keys are used. In general keys not listed here will be silently ignored.

| Key                | Description                                                  | Examples                                                                              |
|--------------------|--------------------------------------------------------------|---------------------------------------------------------------------------------------|
| `meta`             | Metadata. In general you can stick whatever you like in here | `{ "description": "Add to them." }`                                                   |
| `meta.description` | A description of this test example.                          | Chemicals decreasing the activity of epidermal growth factor receptor (NCBIGene:1956) |
| `query`            | MUST be a TRAPI query.                                       | `{ "message": { "query_graph": ... }}`                                                |
| `assertions`       | A list of tests that must pass during testing.               | `[]`                                                                                  |

## Supported assertions

These can be included in the `assertions` list.

### ExpectedResultCounts

This assertion tests whether we get back a certain number of results.

* `type`: MUST be `ExpectedResultCounts`.
* `description`: OPTIONAL. A description of what is being tested here.
* `min`: The minimum number of expected results; getting fewer results than this will fail the test.
* `max`: The maximum number of expected results; getting more results than this will fail the test.

Example:

```json
{
  "type": "ExpectedResultCounts",
  "min": 35
}
```

### ExpectedNodeResults

This assertion retrieves the list of all results returned for a particular node, and
asserts whether that list equals, includes or excludes certain identifiers.

* `type`: MUST be `ExpectedNodeResults`.
* `description`: OPTIONAL. A description of what is being tested here.
* `node`: REQUIRED. The node ID being asserted against, e.g. `n1`.
* `resultEquals`: The list of unique identifiers that the node MUST return in the results.
* `resultIncludes`: A list of identifiers that MUST be included in the list of unique identifiers returned for a node.
* `resultExcludes`: A list of identifiers that MUST NOT be included in the list of unique identifiers returned for a node.

```json
{
  "type": "ExpectedNodeResults",
  "node": "n0",
  "resultEquals": ["GO:0005488"],
  "description": "Expected binding (GO:0005488) to have valproic acid (PUBCHEM.COMPOUND:3121) as an input."
}
```