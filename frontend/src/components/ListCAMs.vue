<script setup lang="ts">
import {computed, onMounted, ref, watch} from "vue";

export interface Props {
  automatCAMKPEndpoint?: string,
  camList: string[],
  changeSelectedModel: Function,
}

const props = withDefaults(defineProps<Props>(), {
  automatCAMKPEndpoint: 'https://automat.renci.org/cam-kp'
});

const selectedModel = ref();

watch(selectedModel, (newlySelectedModel: string) => props.changeSelectedModel(newlySelectedModel));

</script>

<template>
  <div class="card my-2">
    <div class="card-header">
      <strong>List of CAM Models ({{camList.length}})</strong>
    </div>
    <div class="card-body">
      <ul class="list-group">
        <li
            v-for="modelURL in camList" :key="modelURL"
            :class="'list-group-item list- ' + (modelURL == selectedModel ? 'active' : '')"
            @click="selectedModel = modelURL"
        >
          {{modelURL}} <span v-if="selectedModel != modelURL">(<a :href="modelURL" target="cam">URL</a>)</span>
        </li>
      </ul>
    </div>
  </div>
</template>

<style scoped>

</style>