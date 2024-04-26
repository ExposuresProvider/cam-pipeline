<script setup lang="ts">
import { ref } from 'vue'
import DisplayCAM from "./DisplayCAM.vue";
import SearchCAMs from "./SearchCAMs.vue";

// Some editable
const automatCAMKPEndpoint = ref("https://automat.renci.org/cam-kp")
const selectedModelURL = ref('')
const searchIds = ref<Set<string>>(new Set<string>());

function changeSelectedModel(modelURL: string) {
  // Allows other components to change the selected model.
  selectedModelURL.value = modelURL;
}

function changeSearchIds(searchIdList: Set<string>) {
  // Allows other components to change the list of IDs we're searching for.
  searchIds.value = searchIdList;
}

</script>

<template>
  <main>
    <div class="card my-2">
      <div class="card-header">
        <strong>CAM-KP Frontend</strong>
      </div>
      <div class="card-body">
        <p class="card-text">
          The CAM-KP Frontend is intended to provide a frontend to the
          <a href="https://github.com/NCATSTranslator/Translator-All/wiki/CAM-Provider-KG">Causal Activity Models (CAM)
            Knowledge Graph (KG)</a>, as implemented in <a href="https://automat.renci.org/#/cam-kp">Automat CAM-KP</a>.
        </p>
        <p class="card-text">
          <strong>Experimental and under development.</strong>
          Please report any issues to <a href="https://github.com/ExposuresProvider/cam-pipeline/issues">our GitHub repository</a>.
        </p>
      </div>
    </div>

    <div class="row">
      <SearchCAMs :automatCAMKPEndpoint="automatCAMKPEndpoint" :changeSelectedModel="changeSelectedModel" :changeSearchIds="changeSearchIds" />
      <DisplayCAM :selected-model-u-r-l="selectedModelURL" :search-ids="searchIds"></DisplayCAM>
    </div>

    <div class="accordion" id="advancedOptionsAccordion">
      <div class="accordion-item">
        <h2 class="accordion-header" id="advancedOptionsHeader">
          <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#advancedOptions" aria-expanded="false" aria-controls="advancedOptions">
            Advanced options
          </button>
        </h2>
        <div id="advancedOptions" class="accordion-collapse collapse" aria-labelledby="advancedOptionsHeader" data-bs-parent="#advancedOptionsAccordion">
          <div class="accordion-body">
            <form>
              <div class="mb-3">
                <label for="automatCAMKPEndpoint" class="form-label">Automat CAM-KP Endpoint</label>
                <input type="email" class="form-control" id="automatCAMKPEndpoint" aria-describedby="emailHelp" v-model="automatCAMKPEndpoint">
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  </main>
</template>

<style scoped>

</style>
