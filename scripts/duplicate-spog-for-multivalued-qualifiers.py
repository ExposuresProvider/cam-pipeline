#!/usr/bin/env python
import json
import logging
from collections import defaultdict
from itertools import product
from sys import argv

logging.basicConfig(level=logging.INFO)

# kg.tsv includes qualifiers as a list of key-value pairs as JSON directories, e.g.
# [{"qualifier_type_id":"biolink:anatomical_context_qualifier","qualifier_value":"GO:0005829"},{"qualifier_type_id":"biolink:anatomical_context_qualifier","qualifier_value":"GO:0005789"}]
#
# Unfortunately, ORION does not currently support this. So instead this little Python script is intended to unwrap
# multivalued qualifiers.

# This program has two arguments: the input file (kg.tsv) and the output file (kg_duplicated_multivalued_qualifiers.tsv).
if len(argv) != 3:
    print("Usage: duplicate-spog-for-multivalued-qualifiers.py <input_file> <output_file>")
    exit(1)
kg_input_tsv = argv[1]
kg_output_tsv = argv[2]

# Loop through the input file, unwrapping multiple qualifiers where they are found.
with open(kg_input_tsv, 'r') as fin, open(kg_output_tsv, 'w') as fout:
    for line in fin:
        columns = line.strip().split('\t')
        if len(columns) == 5:
            # No qualifier? Nothing to do here!
            fout.write(line)
            continue

        if len(columns) != 6:
            raise ValueError("kg.tsv should have 6 tab-delimited columns, but this line has " + str(len(columns)) + " columns: " + line)

        subject = columns[0]
        predicate = columns[1]
        obj = columns[2]
        graph = columns[3]
        infores = columns[4]
        qualifier_string = columns[5]

        logging.debug(f"Processing qualifiers: {qualifier_string} in line: {line}")

        # Load qualifiers into a dictionary.
        # We might as well uniquify these values.
        qualifiers = json.loads(qualifier_string)
        qualifier_values_by_type_id = defaultdict(set)
        for qualifier in qualifiers:
            qualifier_type = qualifier['qualifier_type_id']
            qualifier_value = qualifier['qualifier_value']
            qualifier_values_by_type_id[qualifier_type].add(qualifier_value)

        # Repeat the subject/predicate/object/graph lines for each qualifier value.
        # This is the first time I had one LLM check another LLM's reasoning :)
        keys = list(qualifier_values_by_type_id.keys())
        value_sets = [sorted(qualifier_values_by_type_id[k]) for k in keys]

        # Note that we're calculating the Cartesian product for the value-sets only,
        # so we're picking one set of values for each iteration of this loop.
        # But then we need to put the keys back in, which is why we made sure
        # they were both in the right order.
        for values in product(*value_sets):
            # Put the values back together with their keys.
            output_qualifiers = dict(zip(keys, values))

            # Write out one line for each set of values
            fout.write(f"{subject}\t{predicate}\t{obj}\t{graph}\t{infores}\t{json.dumps(output_qualifiers)}\n")
