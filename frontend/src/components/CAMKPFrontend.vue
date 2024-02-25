<script setup lang="ts">

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

    <div class="accordion" id="advancedOptionsAccordion">
      <div class="accordion-item">
        <h2 class="accordion-header" id="advancedOptionsHeader">
          <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#advancedOptions" aria-expanded="false" aria-controls="advancedOptions">
            Advanced options
          </button>
        </h2>
        <div id="advancedOptions" class="accordion-collapse collapse" aria-labelledby="advancedOptionsHeader" data-bs-parent="#advancedOptionsAccordion">
          <div class="accordion-body">
            <strong>This is the first item's accordion body.</strong> It is shown by default, until the collapse plugin adds the appropriate classes that we use to style each element. These classes control the overall appearance, as well as the showing and hiding via CSS transitions. You can modify any of this with custom CSS or overriding our default variables. It's also worth noting that just about any HTML can go within the <code>.accordion-body</code>, though the transition does limit overflow.
          </div>
        </div>
      </div>
    </div>
  </main>
</template>

<style scoped>

</style>