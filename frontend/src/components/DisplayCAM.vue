<script setup lang="ts">
import {computed, ref, watch, withDefaults} from "vue";
import {urlToID} from "./shared.ts";
import lodash from "lodash";
import { mkConfig, generateCsv, download } from "export-to-csv";

export interface Props {
  automatCAMKPEndpoint?: string,
  selectedModelURL: string,
  searchIds: Set<string>,
}

const props = withDefaults(defineProps<Props>(), {
  automatCAMKPEndpoint: 'https://automat.renci.org/cam-kp',
  searchIDs: new Set(),
});

const downloadInProgress = ref(false);
const modelRows = ref([]);
const spos = ref([]);
const labels = ref({});
const descriptions = ref({});

// Display flags
const display_descriptions = ref(false);
const display_information_content = ref(false);
const display_eq_identifiers = ref(false);
const display_xrefs = ref(false);
const display_primary_knowledge_source = ref(false);

const fromIds = computed(() => [...new Set(spos.value.map(spo => spo[0]).sort())]);
const toIds = computed(() => [...new Set(spos.value.map(spo => spo[1]).sort())]);

function getPredicates(fromId: string, toId: string) {
  // TODO: figure out how to do this in the right order.
  return spos.value.filter(spo => spo[0] == fromId && spo[1] == toId).map(spo => {
    if (spo[3]) return `${spo[2]} [${spo[3]}]`;
    return spo[2];
  }).sort();
}

watch(() => props.selectedModelURL, (modelURL, _) => {
  if (!modelURL) return;

  modelRows.value = [];
  spos.value = [];
  labels.value = {};
  descriptions.value = {};

  getModelRows(modelURL).then(rows => {
    modelRows.value = rows;
    rows.forEach(row => {
      spos.value.push([row[0]['id'], row[2]['id'], row[3], row[4]]);

      labels.value[row[0]['id']] = row[0]['name'];
      labels.value[row[2]['id']] = row[2]['name'];

      descriptions.value[row[0]['id']] = row[0]['description'];
      descriptions.value[row[2]['id']] = row[2]['description'];
    });
  });
});

async function getModelRows(modelURL: string) {
  if (!modelURL) return [];

  downloadInProgress.value = true;

  const cypher_endpoint = props.automatCAMKPEndpoint + '/cypher';
  let response = await fetch(cypher_endpoint, {
    'method': 'POST',
    'headers': {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    'body': JSON.stringify({
      'query': `MATCH (s)-[p]-(o) WHERE '${modelURL}' IN p.xref RETURN DISTINCT s, properties(p) AS p, o, TYPE(p) AS pred_type, CASE
    WHEN startNode(p) = s THEN ''
    WHEN endNode(p) = s THEN 'reverse'
    ELSE ''
  END AS direction;`,
    }),
  });
  let j: any = await response.json();

  downloadInProgress.value = false;

  console.log("response = ", j);

  const results = j['results'].flatMap(r => r['data']).map(r => r['row']);

  // Reverse any 'reverse' rows.
  const reversedResults = lodash.uniqWith(results.map(row => {
    if (row[4] === 'reverse') {
      // If this row is "reversed", reverse the subject and the object.
      const subj = {...row[0]};
      row[0] = row[2];
      row[2] = subj;
      row[4] = '';
    }

    return row;
  }), lodash.isEqual);

  console.log("reversedResults = ", reversedResults);
  return reversedResults;
}

// Download model rows as CSV.
function downloadModelRowsAsCSV() {
  if (!modelRows.value) return;

  const modelFilename = new URL(props.selectedModelURL).pathname.split('/').at(-1);

  const csvConfig = mkConfig({
    filename: modelFilename,
    useKeysAsHeaders: true,
    columnHeaders: [
      'subject_id',
      'subject_label',
      'predicate',
      'primary_knowledge_source',
      'object_id',
      'object_label'
    ]
  });

  console.log("modelRows.value = ", modelRows.value);

  const csvData = modelRows.value.map(row => {
    return {
      'subject_id': row[0]['id'],
      'subject_label': row[0]['name'],
      'predicate': row[3],
      'primary_knowledge_source': row[1]['primary_knowledge_source'],
      'object_id': row[2]['id'],
      'object_label': row[2]['name'],
    };
  });

  const csv = generateCsv(csvConfig)(csvData);
  download(csvConfig)(csv);
}
</script>

<template>

  <div class="col-8">
    <div id="edges" class="card my-2">
      <div class="card-header">Display</div>
      <div class="card-body">
        <div class="form-check">
          <input class="form-check-input" type="checkbox" v-model="display_descriptions" id="displayDescription">
          <label class="form-check-label" for="displayDescription">
            Display node descriptions
          </label>
        </div>
        <div class="form-check">
          <input class="form-check-input" type="checkbox" v-model="display_eq_identifiers" id="displayEquivalentIdentifiers">
          <label class="form-check-label" for="displayEquivalentIdentifiers">
            Display equivalent identifiers
          </label>
        </div>
        <div class="form-check">
          <input class="form-check-input" type="checkbox" v-model="display_information_content" id="displayInformationContent">
          <label class="form-check-label" for="displayInformationContent">
            Display information content
          </label>
        </div>
        <div class="form-check">
          <input class="form-check-input" type="checkbox" v-model="display_primary_knowledge_source" id="displayPrimaryKnowledgeSource">
          <label class="form-check-label" for="displayPrimaryKnowledgeSource">
            Display primary knowledge source
          </label>
        </div>
        <div class="form-check">
          <input class="form-check-input" type="checkbox" v-model="display_xrefs" id="displayXrefs">
          <label class="form-check-label" for="displayXrefs">
            Display other models with this edge (Xrefs)
          </label>
        </div>
      </div>
    </div>

    <div class="card my-2" v-if="!selectedModelURL">
      <div class="card-header">
        No model selected. Please search for one using the controls on the left.
      </div>
    </div>

    <div class="card my-2" v-if="downloadInProgress">
      <div class="card-header">
        Download of CAM <a target="cam" :href="selectedModelURL">{{ selectedModelURL }}</a> in progress ...
      </div>
    </div>

    <div id="edges" class="card my-2">
      <div class="card-header">
        <button class="float-end" @click="downloadModelRowsAsCSV()">Download as CSV</button>
        <strong>Edges in selected CAM:</strong> <a target="cam" :href="selectedModelURL">{{ selectedModelURL }}</a> (<a href="#relationships">Relationships</a>)
      </div>
      <div class="card-body" v-if="!downloadInProgress">
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
              <td :class="(row[0]['equivalent_identifiers'].some(v => searchIds.has(v))) ? 'bg-success-subtle' : ''">
                <strong>{{row[0]['id']}}</strong> {{row[0]['name']}}
                <p v-if="display_descriptions"><em>Description</em>: {{row[0]['description']}}</p>
                <p v-if="display_information_content"><em>Information Content</em>: {{row[0]['information_content']}}</p>
                <p v-if="display_eq_identifiers"><em>Equivalent identifiers</em>: {{row[0]['equivalent_identifiers']}}</p>
              </td>
              <td>
                <div>{{row[3]}}<span v-if="row[4]"> [{{row[4]}}]</span></div>
                <p v-if="display_primary_knowledge_source"><em>Primary knowledge source</em>: {{row[1]['primary_knowledge_source']}}</p>
                <ul v-if="display_xrefs" class="overflow-auto" style="max-height: 20em">
                  <li v-for="xref in row[1]['xref']" :key="xref">
                    <a :href="xref" target="xref">{{urlToID(xref)}}</a>
                  </li>
                </ul>
              </td>
              <td :class="(row[2]['equivalent_identifiers'].some(v => searchIds.has(v))) ? 'bg-success-subtle' : ''">
                <strong>{{row[2]['id']}}</strong> {{row[2]['name']}}
                <p v-if="display_descriptions"><em>Description</em>: {{row[2]['description']}}</p>
                <p v-if="display_information_content"><em>Information Content</em>: {{row[2]['information_content']}}</p>
                <p v-if="display_eq_identifiers"><em>Equivalent identifiers</em>: {{row[2]['equivalent_identifiers']}}</p>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- This view is hard to compress, so let's give it the whole screen -->
  <div class="col-12">
    <div id="relationships" class="card my-2">
      <div class="card-header">
        <strong>Relationships in selected CAM:</strong> <a target="cam" :href="selectedModelURL">{{ selectedModelURL }}</a> (<a href="#edges">Edges</a>)
      </div>
      <div class="card-body" v-if="!downloadInProgress">
        <div class="table-responsive">
          <table class="table table-bordered table-hover">
            <thead>
            <tr>
              <th scope="col">From CURIE</th>
              <th scope="col" v-for="toId in toIds" :class="(searchIds.has(toId)) ? 'bg-success-subtle' : ''">
                <span :title="descriptions[toId]">{{toId}}</span><br />{{labels[toId]}}
              </th>
            </tr>
            </thead>
            <tbody>
            <tr v-for="fromId in fromIds">
              <td :class="(searchIds.has(fromId)) ? 'bg-success-subtle' : ''"><strong>{{fromId}}</strong> {{labels[fromId]}}<br/>{{descriptions[fromId]}}</td>
              <td v-for="toId in toIds" :class="(searchIds.has(toId) || searchIds.has(fromId)) ? 'bg-success-subtle' : ''">
                <span v-for="pred in getPredicates(fromId, toId)">{{pred}}<br /></span>
              </td>
            </tr>
            </tbody>
          </table>
        </div>
      </div>
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
