<script setup lang="ts">
export interface Props {
  automatCAMKPEndpoint?: string,
  changeSelectedModel: Function,
}

const props = withDefaults(defineProps<Props>(), {
  automatCAMKPEndpoint: 'https://automat.renci.org/cam-kp',
});

function updateModelList() {
  props.changeSelectedModel('test');
}
</script>

<template>
  <div class="card my-2">
    <div class="card-header">
      <strong>List of CAM Models</strong>
    </div>
    <div class="card-body">
      <p class="card-text">
        Based on {{ props.automatCAMKPEndpoint }} and {{ props.changeSelectedModel }}.
      </p>
      <a @click="updateModelList()" href="#" class="btn btn-primary">Search</a>
    </div>
  </div>
</template>

<style scoped>

</style>