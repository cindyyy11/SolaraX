<script setup lang="ts">
import { ref } from 'vue'
import {
  predictVision,
  type VisionPrediction,
} from '@/services/api'
// Which site the reader is looking at. The classifier does not use it — an
// uploaded image never changes detection, economics or ranking (CLAUDE.md
// anti-goal: imagery is corroborating evidence, never a trigger). It is here
// so the result on screen is attributable to a site rather than floating free.
const props = defineProps<{
  siteId: string
  siteName: string
}>()

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
      potential visual evidence of a defect at
      {{ props.siteName }} ({{ props.siteId }}).
    </p>

    <p class="vision__note">
      Corroborating evidence only. The dispatch ranking is
      set by the electrical signal and does not change
      because an image was uploaded.
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
  <template v-if="prediction.evidence.defect_class === 'Unknown'">
    <p>
      <strong>Unable to classify image.</strong>
    </p>

    <p>
      Please upload a thermal solar-module image.
    </p>

    <p>
      <strong>Model confidence:</strong>
      {{ (prediction.evidence.confidence * 100).toFixed(2) }}%
    </p>
  </template>

  <template v-else>
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
  </template>
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

.vision__note {
  margin: 0 0 1rem;
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.vision input[type='file'] {
  display: block;
  width: 100%;
  max-width: 22rem;
  font: inherit;
  font-size: 0.8rem;
  color: var(--text-secondary);
}

.vision input[type='file']::file-selector-button {
  margin-right: 0.6rem;
  padding: 0.4rem 0.7rem;
  background: transparent;
  color: var(--text-primary);
  border: 1px solid var(--baseline);
  border-radius: var(--radius-sm);
  font: inherit;
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
  transition: border-color var(--duration-fast) var(--ease-out);
}

.vision input[type='file']::file-selector-button:hover {
  border-color: var(--action-text);
  color: var(--action-text);
}

.vision__preview {
  display: block;
  max-width: 320px;
  max-height: 320px;
  margin: 1rem 0;
  border-radius: var(--radius-sm);
}

/* Matches the primary action treatment used on Site Detail and the work
   order — this button was previously an unstyled browser default, which is
   the one control in the product that looked like nobody had reached it. */
.vision__button {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  margin-top: 1rem;
  padding: 0.55rem 0.9rem;
  background: var(--action-fill);
  color: var(--action-ink);
  border: none;
  border-radius: var(--radius-sm);
  font: inherit;
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
  transition:
    background-color var(--duration-fast) var(--ease-out),
    transform var(--duration-fast) var(--ease-out);
}

.vision__button:hover:not(:disabled) {
  background: var(--action-fill-hover);
}

.vision__button:active:not(:disabled) {
  transform: scale(0.97);
}

.vision__button:disabled {
  background: var(--baseline);
  color: var(--text-muted);
  cursor: not-allowed;
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
  color: var(--status-critical);
}
</style>