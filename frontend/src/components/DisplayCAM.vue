<script setup lang="ts">
import {computed, ref, watch, withDefaults} from "vue";

export interface Props {
  automatCAMKPEndpoint?: string,
  selectedModel: string,
}

const props = withDefaults(defineProps<Props>(), {
  automatCAMKPEndpoint: 'https://automat.renci.org/cam-kp',
});

const downloadInProgress = ref(false);
const modelRows = ref([]);
const spos = ref([]);
const labels = ref({});
const descriptions = ref({});

const fromIds = computed(() => [...new Set(spos.value.map(spo => spo[0]).sort())]);
const toIds = computed(() => [...new Set(spos.value.map(spo => spo[1]).sort())]);

function getPredicates(fromId: string, toId: string) {
  // TODO: figure out how to do this in the right order.
  return spos.value.filter(spo => spo[0] == fromId && spo[1] == toId).map(spo => {
    if (spo[3]) return `${spo[2]} [${spo[3]}]`;
    return spo[2];
  }).sort();
}

watch(() => props.selectedModel, (_, modelURL) => {
  modelRows.value = [];
  spos.value = [];
  labels.value = {};
  descriptions.value = {};

  getModelRows(modelURL).then(rows => {
    modelRows.value = rows;
    rows.map(row => {
      spos.value.push([row[0]['id'], row[2]['id'], row[3], row[4]]);

      labels.value[row[0]['id']] = row[0]['name'];
      labels.value[row[2]['id']] = row[2]['name'];

      descriptions.value[row[0]['id']] = row[0]['description'];
      descriptions.value[row[2]['id']] = row[2]['description'];
    });
  });
});

async function getModelRows(modelURL: string) {
  downloadInProgress.value = true;

  const cypher_endpoint = props.automatCAMKPEndpoint + '/cypher';
  let response = await fetch(cypher_endpoint, {
    'method': 'POST',
    'headers': {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    'body': JSON.stringify({
      'query': `MATCH (s)-[p]-(o) WHERE '${modelURL}' IN p.xref RETURN DISTINCT s, p, o, TYPE(p) AS pred_type, CASE
    WHEN startNode(p) = s THEN ''
    WHEN endNode(p) = s THEN 'reverse'
    ELSE ''
  END AS direction;`,
    }),
  });
  let j: any = await response.json();

  downloadInProgress.value = false;

  const results = j['results'].flatMap(r => r['data']).map(r => r['row']);
  console.log(results);
  return results;
}
</script>

<template>

  <div class="card my-2" v-if="downloadInProgress">
    <div class="card-header">
      Download in progress ...
    </div>
  </div>


  <div class="card" v-if="!downloadInProgress">
    <div class="card-header">
      <strong>Relationships in selected CAM:</strong> <a target="cam" :href="selectedModel">{{selectedModel}}</a>
    </div>
    <div class="card-body">
      <div class="table-responsive">
        <table class="table table-bordered table-hover">
          <thead>
            <tr>
              <th scope="col">From CURIE</th>
              <th scope="col" v-for="toId in toIds">
                <span :title="descriptions[toId]">{{toId}}</span><br />{{labels[toId]}}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="fromId in fromIds">
              <td><strong>{{fromId}}</strong> {{labels[fromId]}}<br/>{{descriptions[fromId]}}</td>
              <td v-for="toId in toIds">
                <span v-for="pred in getPredicates(fromId, toId)">{{pred}}<br /></span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <div class="card" v-if="!downloadInProgress">
    <div class="card-header">
      <strong>Edges in selected CAM:</strong> <a target="cam" :href="selectedModel">{{selectedModel}}</a>
    </div>
    <div class="card-body">
      <table class="table table-bordered mb-2">
        <thead>
          <tr>
            <th>Subject</th>
            <th>Edge</th>
            <th>Object</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in modelRows">
            <td>
              <strong>{{row[0]['id']}}</strong> {{row[0]['name']}}<br/><br/>
              <em>Description</em>: {{row[0]['description']}}<br/>
              <em>Information Content</em>: {{row[0]['information_content']}}<br/>
              <em>Equivalent identifiers</em>: {{row[0]['equivalent_identifiers']}}
            </td>
            <td>
              <strong>{{row[3]}}<span v-if="row[4]"> [{{row[4]}}]</span></strong><br/>
              biolink:primary_knowledge_source: {{row[1]['biolink:primary_knowledge_source']}}
              <ul>
                <li v-for="xref in row[1]['xref']" :key="xref">
                  <a :href="xref" target="xref">{{xref}}</a>
                </li>
              </ul>
            </td>
            <td>
              <strong>{{row[2]['id']}}</strong> {{row[2]['name']}}<br/><br/>
              <em>Description</em>: {{row[2]['description']}}<br/>
              <em>Information Content</em>: {{row[2]['information_content']}}<br/>
              <em>Equivalent identifiers</em>: {{row[2]['equivalent_identifiers']}}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.table-responsive {
  overflow-x: auto;
}

/* Ensure the first column is not affected by responsive behavior */
.table-responsive table td:first-child,
.table-responsive table th:first-child {
  position: sticky;
  left: 0;
  z-index: 2;
  background-color: #fff; /* Match table background color */
}
</style>