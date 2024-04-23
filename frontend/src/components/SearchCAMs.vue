<script setup lang="ts">
/*
 * SearchCAMs: search for CAMs with a set of criteria.
 */
import {ref} from "vue";

export interface Props {
  automatCAMKPEndpoint?: string,
  changeSelectedModel: Function,
}

const props = withDefaults(defineProps<Props>(), {
  automatCAMKPEndpoint: 'https://automat.renci.org/cam-kp',
});

// We need to track the selected model (as well as letting the caller know via changeSelectedModel()
const selectedModel = ref({});

// Store results.
const results = ref([]);

// Search criteria
const subjectOrObjectCURIEsCSV = ref('');
const subjectCURIEsCSV = ref('');
const objectCURIEsCSV = ref('');
const predicateCURIEsCSV = ref('');
const limit = ref(100);

const errors = ref([]);
const inProgress = ref(false);

// Search functions
async function updateModelList() {
  inProgress.value = true;
  errors.value = [];

  try {
    const camList = await searchModels(
        subjectOrObjectCURIEsCSV.value.split(/\s*,\s*/).filter(s => s),
        subjectCURIEsCSV.value.split(/\s*,\s*/).filter(s => s),
        predicateCURIEsCSV.value.split(/\s*,\s*/).filter(s => s),
        objectCURIEsCSV.value.split(/\s*,\s*/).filter(s => s),
        limit.value
    );

    console.log(`Got ${camList.length} CAM models: `, camList);
    results.value = camList;
  } catch (exception) {
    errors.value = exception.message.split('\n');
  }

  inProgress.value = false;
}

async function searchModels(subjectOrObjectCURIEs: string[] = [], subjectCURIEs: string[] = [], predicateCURIEs: string[] = [], objectCURIEs: string[] = [], limit=100): Promise<string[]> {
  /*
   * Search for models using the search criteria provided. Any search criteria that is empty is ignored. Search criteria with multiple values are ORed,
   * but the overall query is ANDed (i.e. a particular predicate type and a object node).
   * - subjectOrObjectCURIEs: CURIEs in either the subject or object slot. Cannot be combined with subjectCURIEs or objectCURIEs.
   * - subjectCURIEs: CURIEs in the subject slot.
   * - predicateCURIEs: CURIEs in the predicate slot.
   * - objectCURIEs: CURIEs in the object slot.
   */

  // Set up node selects.
  const subject_selects = <string[]>[];
  const object_selects = <string[]>[];
  if (subjectOrObjectCURIEs.length > 0 && (subjectCURIEs.length > 0 || objectCURIEs.length > 0)) {
    throw new Error(
        `searchModels() cannot be called with both subjectOrObjectCURIEs (${subjectOrObjectCURIEs.length}) and either ` +
        `subjectCURIEs (${subjectCURIEs.length}) or objectCURIEs (${objectCURIEs.length}).`)
  }

  if(subjectCURIEs) {
    subject_selects.push(...subjectCURIEs.map(curie => `'${curie}' IN s.equivalent_identifiers`));
  }

  if(objectCURIEs) {
    object_selects.push(...objectCURIEs.map(curie => `'${curie}' IN o.equivalent_identifiers`));
  }

  if(subjectOrObjectCURIEs) {
    subject_selects.push(...subjectOrObjectCURIEs.map(curie => `'${curie}' IN s.equivalent_identifiers OR '${curie}' IN o.equivalent_identifiers`));
  }

  // Set up predicate selects.
  const predicate_selects = <string[]>[];
  if (predicateCURIEs) {
    predicate_selects.push(...predicateCURIEs.map(predicate => `TYPE(p) = '${predicate}'`))
  }

  // Combine all selects into a string.
  const selects = [];
  if(subject_selects.length > 0) {
    selects.push(subject_selects.map(select => `(${select})`).join(' OR '));
  }
  if(object_selects.length > 0) {
    selects.push(object_selects.map(select => `(${select})`).join(' OR '));
  }
  if(predicate_selects.length > 0) {
    selects.push(predicate_selects.map(select => `(${select})`).join(' OR '));
  }
  const select_query = selects.join(' AND ');

  // Generate query.
  let query = `MATCH (s)-[p]-(o) RETURN DISTINCT p.xref LIMIT ${limit}`;
  if (select_query.length > 0) {
    query = `MATCH (s)-[p]-(o) WHERE ${select_query} RETURN DISTINCT p.xref LIMIT ${limit}`
  }
  console.log(`Querying Cypher:`, query);

  // Post query.
  const cypher_endpoint = props.automatCAMKPEndpoint + '/cypher';
  let response = await fetch(cypher_endpoint, {
    'method': 'POST',
    'headers': {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    'body': JSON.stringify({
      'query': query
    }),
  });
  let j: any = await response.json();

  if(j['errors'].length > 0) {
    throw Error(j['errors'].map(e => e['message']).join('\n'));
  }

  const rows = j['results'][0]['data'].flatMap(row => ({url: row['row'][0][0]}));
  console.log("rows", rows);
  return rows;
}
</script>

<template>
  <div class="col-4">
    <div class="card my-2">
      <div class="card-header">
        <strong>Search CAM models</strong>
      </div>
      <div class="card-body">
        <div v-if="errors.length > 0" class="mb-3 p-1 border-1 bg-danger-subtle">
          <ul>
            <li v-for="error in errors">{{error}}</li>
          </ul>
        </div>
        <div class="mb-3">
          <label for="predicateCURIEs" class="form-label">Predicate CURIEs</label>
          <input type="text" class="form-control" id="predicateCURIEs" placeholder="biolink:affects, biolink:affected_by" v-model="predicateCURIEsCSV">
        </div>
        <div class="mb-3">
          <label for="subjectOrObjectCURIEs" class="form-label">Subject or Object CURIEs</label>
          <input type="text" class="form-control" id="subjectOrObjectCURIEs" placeholder="PUBCHEM.COMPOUND:5865, CHEBI:8382" v-model="subjectOrObjectCURIEsCSV">
        </div>
        <div class="mb-3">
          <label for="subjectCURIEs" class="form-label">Subject CURIEs</label>
          <input type="text" class="form-control" id="subjectCURIEs" placeholder="CHEMBL.COMPOUND:CHEMBL158, PUBCHEM.COMPOUND:5742832" v-model="subjectCURIEsCSV">
        </div>
        <div class="mb-3">
          <label for="objectCURIEs" class="form-label">Object CURIEs</label>
          <input type="text" class="form-control" id="objectCURIEs" placeholder="CHEMBL.COMPOUND:CHEMBL158, PUBCHEM.COMPOUND:5742832" v-model="objectCURIEsCSV">
        </div>
        <div class="mb-3">
          <label for="limit" class="form-label">Limit</label>
          <input type="text" class="form-control" id="limit" v-model="limit">
        </div>

        <template v-if="inProgress">
          <a @click="updateModelList()" class="btn btn-primary"><em>Search in progress</em></a>
        </template>
        <template v-else>
          <a @click="updateModelList()" class="btn btn-primary">Search</a>
        </template>

      </div>
    </div>

    <div class="card my-2">
      <div class="card-header">
        <strong>List CAM models ({{results.length}})</strong>
      </div>
      <div class="card-body">
        <table class="table table-bordered mb-2">
          <thead>
          <tr>
            <th>Model URL</th>
          </tr>
          </thead>
          <tbody>
          <tr v-for="result in results" @click="selectedModel = result; changeSelectedModel(result)" :class="(selectedModel == result) ? 'table-active' : ''">
            <td>
              {{result.url}} <span @if="selectedModel !== result">(<a :href="result.url" target="model-url">URL</a>)</span>
            </td>
          </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<style scoped>

</style>
