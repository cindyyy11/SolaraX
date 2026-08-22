<script setup lang="ts">
import { ref } from 'vue'
import {
  predictVision,
  type VisionPrediction,
} from '@/services/api'

const selectedFile = ref<File | null>(null)
const previewUrl = ref<string | null>(null)

const prediction = ref<VisionPrediction | null>(null)

const isLoading = ref(false)
const error = ref<string | null>(null)

function chooseImage(event: Event) {
  const input = event.target as HTMLInputElement

  const file = input.files?.[0]

  if (!file) {
    return
  }

  selectedFile.value = file
  prediction.value = null
  error.value = null

  if (previewUrl.value) {
    URL.revokeObjectURL(previewUrl.value)
  }

  previewUrl.value = URL.createObjectURL(file)
}

async function analyseImage() {
  if (!selectedFile.value) {
    return
  }

  isLoading.value = true
  error.value = null
  prediction.value = null

  try {
    prediction.value =
      await predictVision(selectedFile.value)
  } catch (err) {
    error.value =
      err instanceof Error
        ? err.message
        : 'Prediction failed'
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <section class="vision">
    <h2 class="vision__title">
      Computer vision evidence
    </h2>

    <p class="vision__description">
      Upload a thermal solar-module image to classify
      potential visual evidence of a defect.
    </p>

    <input
      type="file"
      accept="image/*"
      @change="chooseImage"
    />

    <img
      v-if="previewUrl"
      :src="previewUrl"
      class="vision__preview"
      alt="Uploaded thermal image"
    />

    <button
      class="vision__button"
      :disabled="!selectedFile || isLoading"
      @click="analyseImage"
    >
      {{ isLoading ? 'Analysing…' : 'Analyse image' }}
    </button>

    <p v-if="error" class="vision__error">
      {{ error }}
    </p>

    <div
  v-if="prediction"
  class="vision__result"
>
  <p>
    <strong>Predicted class:</strong>
    {{ prediction.evidence.defect_class }}
  </p>

  <p>
    <strong>Confidence:</strong>
    {{ (prediction.evidence.confidence * 100).toFixed(2) }}%
  </p>

  <p>
    <strong>Model:</strong>
    {{ prediction.evidence.model_note }}
  </p>

  <p>
    <strong>Inference mode:</strong>
    {{ prediction.evidence.inference_mode }}
  </p>

  <p>
    <strong>Data status:</strong>
    {{ prediction.evidence.data_status }}
  </p>
</div>
  </section>
</template>

<style scoped>
.vision {
  padding: 1.25rem;
  background: var(--surface-1);
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-md);
}

.vision__title {
  margin: 0 0 0.5rem;
  font-size: 1rem;
}

.vision__description {
  margin: 0 0 1rem;
  color: var(--text-secondary);
}

.vision__preview {
  display: block;
  max-width: 320px;
  max-height: 320px;
  margin: 1rem 0;
  border-radius: var(--radius-sm);
}

.vision__button {
  display: block;
  margin-top: 1rem;
  padding: 0.55rem 0.9rem;
  cursor: pointer;
}

.vision__button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.vision__result {
  margin-top: 1rem;
  padding: 1rem;
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-sm);
}

.vision__result p {
  margin: 0.25rem 0;
}

.vision__error {
  color: var(--status-danger);
}
</style>