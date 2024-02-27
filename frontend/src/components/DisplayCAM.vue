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
const modelRows = ref([]);

watch(() => props.selectedModel, (_, modelURL) => {
  modelRows.value = [];
  getModelRows(modelURL).then(rows => { modelRows.value = rows });
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
      'query': `MATCH (s)-[p]-(o) WHERE '${modelURL}' IN p.xref RETURN s, p, o`,
    }),
  });
  let j: any = await response.json();

  downloadInProgress.value = false;

  const rows = j['results'].flatMap(r => r['data']).map(r => r['row']);
  console.log(rows);
  return rows;
}



</script>

<template>
  <div class="card">
    <div class="card-header">
      <strong>Display Selected CAM:</strong> <a target="cam" :href="selectedModel">{{selectedModel}}</a>
    </div>
    <div class="card-body">
      <div class="card my-2" v-if="downloadInProgress">
        <div class="card-header">
          Download in progress ...
        </div>
      </div>
      <table class="table table-bordered mb-2">
        <thead>
          <tr>
            <td>Subject</td>
            <td>Edge</td>
            <td>Object</td>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, index) in modelRows" :key="'row_' + index">
            <td>{{row[0]}}</td>
            <td>{{row[1]}}</td>
            <td>{{row[2]}}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>

</style>