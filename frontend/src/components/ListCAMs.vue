<script setup lang="ts">
import {computed, onMounted, ref, watch} from "vue";

export interface Props {
  automatCAMKPEndpoint?: string,
  changeSelectedModel: Function,
}

const props = withDefaults(defineProps<Props>(), {
  automatCAMKPEndpoint: 'https://automat.renci.org/cam-kp',
});

async function getModels(limit=100) {
  // This picks a hundred models so we have something to display.
  const cypher_endpoint = props.automatCAMKPEndpoint + '/cypher';
  let response = await fetch(cypher_endpoint, {
    'method': 'POST',
    'headers': {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    'body': JSON.stringify({
      'query': 'MATCH (s)-[p]-(o) RETURN DISTINCT p.xref LIMIT ' + limit,
    }),
  });
  let j: any = await response.json();
  const rows = j['results'][0]['data'].flatMap(row => row['row'][0][0]);
  console.log("rows", rows);
  return rows;
}

const listedModels = ref([]);
const selectedModel = ref();

watch(selectedModel, (newlySelectedModel: string) => props.changeSelectedModel(newlySelectedModel));

onMounted(() => {
  getModels(10).then(modelURLs => {
    listedModels.value = modelURLs;
    selectedModel.value = modelURLs[0];
  });
})

</script>

<template>
  <div class="card my-2">
    <div class="card-header">
      <strong>List of CAM Models</strong>
    </div>
    <div class="card-body">
      <ul class="list-group">
        <li
            v-for="modelURL in listedModels" :key="modelURL"
            :class="'list-group-item list- ' + (modelURL == selectedModel ? 'active' : '')"
            @click="selectedModel = modelURL"
        >
          {{modelURL}}
        </li>
      </ul>

      <a @click="updateModelList()" href="#" class="btn btn-primary">Search</a>
    </div>
  </div>
</template>

<style scoped>

</style>