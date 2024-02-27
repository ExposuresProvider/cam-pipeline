<script setup lang="ts">
import {ref, watch, withDefaults} from "vue";

export interface Props {
  automatCAMKPEndpoint?: string,
  selectedModel: string,
}

const props = withDefaults(defineProps<Props>(), {
  automatCAMKPEndpoint: 'https://automat.renci.org/cam-kp',
});

const downloadInProgress = ref(false);
const modelResults = ref([]);

watch(() => props.selectedModel, (_, modelURL) => {
  modelResults.value = [];
  getModelRows(modelURL).then(rows => { modelResults.value = rows });
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
      'query': `MATCH (s)-[p]-(o) WHERE '${modelURL}' IN p.xref RETURN DISTINCT s, p, o`,
    }),
  });
  let j: any = await response.json();

  downloadInProgress.value = false;

  const results = j['results'].flatMap(r => r['data']);
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
      <strong>Edges in selected CAM:</strong> <a target="cam" :href="selectedModel">{{selectedModel}}</a>
    </div>
    <div class="card-body">
      <table class="table table-bordered mb-2">
        <thead>
          <tr>
            <td><strong>Subject</strong></td>
            <td><strong>Edge</strong></td>
            <td><strong>Meta</strong></td>
            <td><strong>Object</strong></td>
          </tr>
        </thead>
        <tbody>
          <tr v-for="result in modelResults">
            <td>
              <strong>{{result['row'][0]['id']}}</strong> {{result['row'][0]['name']}}<br/><br/>
              <em>Description</em>: {{result['row'][0]['description']}}<br/>
              <em>Information Content</em>: {{result['row'][0]['information_content']}}<br/>
              <em>Equivalent identifiers</em>: {{result['row'][0]['equivalent_identifiers']}}
            </td>
            <td>
              biolink:primary_knowledge_source: {{result['row'][1]['biolink:primary_knowledge_source']}}
              <ul>
                <li v-for="xref in result['row'][1]['xref']" :key="xref">
                  <a :href="xref" target="xref">{{xref}}</a>
                </li>
              </ul>
            </td>
            <td>
              <ul v-for="meta in result['meta']">
                <li>{{meta}}</li>
              </ul>
            </td>
            <td>
              <strong>{{result['row'][2]['id']}}</strong> {{result['row'][2]['name']}}<br/><br/>
              <em>Description</em>: {{result['row'][2]['description']}}<br/>
              <em>Information Content</em>: {{result['row'][2]['information_content']}}<br/>
              <em>Equivalent identifiers</em>: {{result['row'][2]['equivalent_identifiers']}}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>

</style>