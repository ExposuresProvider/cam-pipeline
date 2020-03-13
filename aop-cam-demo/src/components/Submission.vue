<template>
  <div class="submission">
    <!-- <textarea class="col-12" :value="JSON.stringify(queryAsGraph)" rows="7"></textarea> -->
    <div style="float: right">
      <div id="query-cytoscape" style="width: 40em; height: 40em; border: 1px solid black; margin: 1em">
      </div>
      <button class="col-12" @click="this.cy.fit()">Fit</button>
    </div>
    <div class="col-5">
      <h1>Enter query here</h1>
      <textarea class="col-12 text-pre-wrap" id="query" v-model="query" rows="7"></textarea>
      <button class="col-12" id="submission" @click="submitQuery(query)">Submit</button>
    </div>
  </div>
</template>

<script>
const cytoscape = window.cytoscape;

export default {
  name: 'Submission',
  props: {},
  data: () => { return {
    query: `{
      "nodes": [
        {
          "id": "n0",
          "type": "gene",
          "curie": "NCBIGENE:558"
        },
        {
          "id": "n1",
          "type": "biological_process"
        }
      ],
      "edges": [
        {
          "id": "e0",
          "source_id": "n1",
          "target_id": "n0",
          "type": "has_participant"
        }
      ]}`
    }
  },
  computed: {
    cy() { return cytoscape({
      container: document.getElementById('query-cytoscape'),
      style: [
        {
            "selector": "node",
            "style": {
                "label": "data(id)",
                "background-color": "#60f",
                "shape": "round-rectangle"
            }
        },
        {
            "selector": "edge",
            "style": {
                "curve-style": "unbundled-bezier",
                "control-point-distances": [
                    -20,
                    20
                ],
                "control-point-weights": [
                    0.5
                ],
                "content": "data(id)",
                "line-color": "#808080",
                "target-arrow-color": "#808080",
                "target-arrow-shape": "triangle",
                "target-arrow-fill": "filled"
            }
        }
      ],
      layout: {
        name: "breadthfirst",
      }
    })
    },
    queryAsJSON() {
      try {
        return JSON.parse(this.query);
      } catch(err) {
        return {};
      }
    },
    queryAsGraph() {
      return {
        nodes: (this.queryAsJSON["nodes"] || []).map(node => {
          return { id: node.id };
        }),
        edges: (this.queryAsJSON["edges"] || []).map(edge => {
          return {
            id: edge.id,
            source: edge.source_id,
            target: edge.target_id,
          };
        })
      };
    }
  },
  watch: {
    query() {
      console.log("Setting ", this.cy, " with nodes: ", this.queryAsGraph.nodes, " and edges:", this.queryAsGraph.edges);

      // When query is updated, redraw the query graph.
      this.cy.remove('node');
      this.cy.remove('edge');

      this.queryAsGraph.nodes.forEach(node => this.cy.add({ group: 'nodes', data: node }));
      this.queryAsGraph.edges.forEach(edge => this.cy.add({ group: 'edges', data: edge }));
      this.cy.fit();
    },
  },
  methods: {
    submitQuery(query) {
      let parsed = null;


      if (parsed == null) return;

      console.log("Submitting query: ", query);
    }
  }
}
</script>
