<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
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
const isDragging = ref(false)
const validationMessage = ref<string | null>(null)
const reviewState = ref<'unreviewed' | 'confirmed' | 'needs-review' | 'not-supported'>('unreviewed')

const confidencePercent = computed(() =>
  prediction.value ? Math.round(prediction.value.evidence.confidence * 100) : 0,
)
const confidenceLabel = computed(() => {
  if (confidencePercent.value >= 80) return 'Strong model signal'
  if (confidencePercent.value >= 55) return 'Review recommended'
  return 'Low confidence'
})
const decisionMessage = computed(() => ({
  confirmed: 'Evidence recorded as supporting the current dispatch recommendation.',
  'needs-review': 'Field verification remains required before acting on this image.',
  'not-supported': 'This image does not support the current dispatch recommendation. Electrical evidence remains unchanged.',
  unreviewed: 'Review the model signal and record an operator decision.',
}[reviewState.value]))

function clearPreview() {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = null
}

function validateFile(file: File): string | null {
  if (!file.type.startsWith('image/')) return 'Choose an image file (JPG, PNG, WebP, or a supported thermal export).'
  if (file.size > 12 * 1024 * 1024) return 'This image is larger than 12 MB. Export a smaller frame and try again.'
  return null
}

function setFile(file: File) {
  const invalid = validateFile(file)
  validationMessage.value = invalid
  if (invalid) return
  selectedFile.value = file
  prediction.value = null
  error.value = null
  reviewState.value = 'unreviewed'
  clearPreview()
  previewUrl.value = URL.createObjectURL(file)
}

function chooseImage(event: Event) {
  const input = event.target as HTMLInputElement

  const file = input.files?.[0]

  if (!file) {
    return
  }

  setFile(file)
}

function dropImage(event: DragEvent) {
  isDragging.value = false
  const file = event.dataTransfer?.files?.[0]
  if (file) setFile(file)
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

function resetEvidence() {
  selectedFile.value = null
  prediction.value = null
  error.value = null
  validationMessage.value = null
  reviewState.value = 'unreviewed'
  clearPreview()
}

onBeforeUnmount(clearPreview)
</script>

<template>
  <section class="vision card card--interactive">
    <div class="vision__heading">
      <div><h2 class="vision__title">Does this image support dispatch?</h2><p>Computer vision evidence · {{ props.siteName }}</p></div>
      <span>HUMAN REVIEW REQUIRED</span>
    </div>

    <p class="vision__description">
      Upload a thermal solar-module image to test whether visual evidence supports the current recommendation for {{ props.siteId }}.
    </p>

    <p class="vision__note">
      Corroborating evidence only. The dispatch ranking is
      set by the electrical signal and does not change
      because an image was uploaded.
    </p>


    <div
      class="vision__dropzone"
      :class="{ 'vision__dropzone--active': isDragging, 'vision__dropzone--selected': selectedFile }"
      @dragover.prevent="isDragging = true"
      @dragleave.prevent="isDragging = false"
      @drop.prevent="dropImage"
    >
      <input id="vision-file" type="file" accept="image/*" capture="environment" @change="chooseImage" />
      <label for="vision-file" class="vision__choose">Choose or capture image</label>
      <span>or drag a thermal frame here · max 12 MB</span>
    </div>
    <p v-if="validationMessage" class="vision__validation" role="alert">{{ validationMessage }}</p>

    <div v-if="previewUrl" class="vision__review">
      <div class="vision__image-frame">
        <img :src="previewUrl" class="vision__preview" alt="Selected thermal image for review" />
        <span class="vision__image-badge">Original frame</span>
      </div>
      <div class="vision__review-actions">
        <button class="vision__button" :disabled="isLoading" @click="analyseImage">
          {{ isLoading ? 'Analysing…' : 'Analyse image' }}
        </button>
        <button class="vision__replace" type="button" :disabled="isLoading" @click="resetEvidence">Replace image</button>
      </div>
    </div>
    <ol v-if="isLoading" class="vision__progress" aria-label="Analysis progress">
      <li class="active">Checking image quality</li><li class="active">Running model</li><li>Preparing evidence</li>
    </ol>

    <p v-if="error" class="vision__error">
      {{ error }}
    </p>

   <div v-if="prediction" class="vision__result">
  <div class="vision__result-head"><div><span>ANALYSIS SUMMARY</span><h3>{{ prediction.evidence.defect_class === 'Unknown' ? 'Inconclusive image' : prediction.evidence.defect_class }}</h3></div><strong>{{ confidencePercent }}%<small>{{ confidenceLabel }}</small></strong></div>
  <template v-if="prediction.evidence.defect_class === 'Unknown'">
    <p>
      <strong>Unable to classify image.</strong>
    </p>

    <p>
      Please upload a thermal solar-module image.
    </p>

    <p>
      <strong>Model confidence:</strong> {{ confidencePercent }}%
    </p>
  </template>

  <template v-else>
    <dl class="vision__metadata"><div><dt>Model</dt><dd>{{ prediction.evidence.model_note }}</dd></div><div><dt>Inference mode</dt><dd>{{ prediction.evidence.inference_mode }}</dd></div><div><dt>Data status</dt><dd>{{ prediction.evidence.data_status }}</dd></div></dl>
  </template>
  <div class="vision__confidence" aria-label="Model confidence">
    <span :style="{ transform: `scaleX(${confidencePercent / 100})` }"></span>
  </div>
  <p class="vision__localization">No spatial coordinates returned by the model. This result is shown as corroborating evidence only; no panel location is inferred.</p>
  <div class="vision__decision" aria-label="Evidence review decision">
    <span>Operator review</span>
    <button type="button" :class="{ active: reviewState === 'confirmed' }" @click="reviewState = 'confirmed'">Supports dispatch</button>
    <button type="button" :class="{ active: reviewState === 'needs-review' }" @click="reviewState = 'needs-review'">Needs field verification</button>
    <button type="button" :class="{ active: reviewState === 'not-supported' }" @click="reviewState = 'not-supported'">Does not support</button>
    <p class="vision__decision-message" aria-live="polite">{{ decisionMessage }}</p>
  </div>
</div>
  </section>
</template>

<style scoped>
.vision {
  padding: 1.25rem;
}

.vision__title {
  margin: 0;
  font-family: var(--font-display);
  font-size: clamp(1.15rem, 2vw, 1.45rem);
  letter-spacing: -.025em;
}
.vision__heading { display:flex; align-items:flex-start; justify-content:space-between; gap:1rem; margin-bottom:.8rem; }
.vision__heading p { margin:.3rem 0 0; color:var(--text-muted); font-size:.7rem; }
.vision__heading > span { flex:0 0 auto; padding:.28rem .45rem; color:var(--action-ink); background:var(--action-fill); border-radius:var(--radius-sm); font-size:.55rem; font-weight:800; letter-spacing:.07em; }

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
  position: absolute;
  width: 1px;
  height: 1px;
  opacity: 0;
}

.vision__dropzone { position: relative; display: flex; min-height: 7rem; flex-direction: column; align-items: center; justify-content: center; gap: .35rem; padding: 1rem; text-align: center; border: 1px dashed var(--baseline); border-radius: var(--radius-md); background: var(--surface-2); transition: border-color var(--duration-fast) var(--ease-out), background-color var(--duration-fast) var(--ease-out); }
.vision__dropzone--active { border-color: var(--action-text); background: var(--surface-selected); }
.vision__dropzone span { color: var(--text-muted); font-size: .72rem; }
.vision__choose { min-height: 44px; display: inline-flex; align-items: center; padding: .6rem .85rem; color: var(--action-ink); background: var(--action-fill); border-radius: var(--radius-sm); font-size: .8rem; font-weight: 700; cursor: pointer; }
.vision__validation { margin: .6rem 0 0; color: var(--status-critical); font-size: .78rem; }
.vision__review { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 1rem; align-items: end; margin-top: 1rem; }
.vision__image-frame { position: relative; min-width: 0; }
.vision__preview { display: block; width: 100%; max-width: 420px; max-height: 320px; object-fit: contain; border-radius: var(--radius-sm); background: var(--surface-2); }
.vision__image-badge { position: absolute; left: .5rem; bottom: .5rem; padding: .25rem .4rem; color: #fff; background: rgba(11,11,11,.75); border-radius: 3px; font-size: .62rem; }
.vision__review-actions { display: flex; flex-direction: column; gap: .45rem; }
.vision__replace { padding: .3rem; color: var(--text-secondary); background: transparent; border: 0; font: inherit; font-size: .72rem; cursor: pointer; }
.vision__progress { display: flex; gap: 1rem; margin: .8rem 0 0; padding: 0; list-style: none; color: var(--text-muted); font-size: .7rem; }
.vision__progress li.active { color: var(--action-text); font-weight: 700; }

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
.vision__result-head { display:flex; align-items:flex-start; justify-content:space-between; gap:1rem; padding-bottom:.8rem; border-bottom:1px solid var(--border-hairline); }
.vision__result-head span { color:var(--text-muted); font-size:.58rem; font-weight:800; letter-spacing:.08em; }
.vision__result-head h3 { margin:.2rem 0 0; font-family:var(--font-display); font-size:1.2rem; letter-spacing:-.025em; }
.vision__result-head > strong { text-align:right; font-family:var(--font-display); font-size:1.55rem; line-height:1; }
.vision__result-head small { display:block; margin-top:.25rem; color:var(--text-muted); font:600 .62rem var(--font-sans); }
.vision__metadata { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:.5rem; margin:.85rem 0; }
.vision__metadata div { min-width:0; padding:.65rem; background:var(--surface-2); border-radius:var(--radius-sm); }
.vision__metadata dt { color:var(--text-muted); font-size:.62rem; }
.vision__metadata dd { margin:.2rem 0 0; font-size:.72rem; overflow-wrap:anywhere; }

.vision__result p {
  margin: 0.25rem 0;
}
.vision__confidence { height: 6px; margin: .8rem 0; overflow: hidden; background: var(--surface-2); border-radius: var(--radius-full); }
.vision__confidence span { display: block; width: 100%; height: 100%; transform-origin: left center; background: var(--action-fill); transition: transform var(--duration-base) var(--ease-out); }
.vision__localization { color: var(--text-muted); font-size: .74rem; line-height: 1.45; }
.vision__decision { display: flex; flex-wrap: wrap; align-items: center; gap: .45rem; margin-top: .8rem; padding-top: .7rem; border-top: 1px solid var(--border-hairline); }
.vision__decision span { width: 100%; color: var(--text-muted); font-size: .66rem; text-transform: uppercase; letter-spacing: .06em; }
.vision__decision button { min-height: 40px; padding: .45rem .6rem; color: var(--text-secondary); background: transparent; border: 1px solid var(--border-hairline); border-radius: var(--radius-sm); font: inherit; font-size: .7rem; cursor: pointer; }
.vision__decision button.active { color: var(--action-ink); background: var(--action-fill); border-color: var(--action-fill); }
.vision__decision-message { width:100%; margin:.25rem 0 0 !important; color:var(--text-secondary); font-size:.72rem; line-height:1.45; }

.vision__error {
  color: var(--status-critical);
}

@media (max-width: 620px) {
  .vision__heading { flex-direction:column; }
  .vision__review { grid-template-columns: 1fr; }
  .vision__preview { max-width: none; }
  .vision__review-actions { flex-direction: row; align-items: center; }
  .vision__button { flex: 1; justify-content: center; }
  .vision__metadata { grid-template-columns:1fr; }
  .vision__decision button { flex:1 1 100%; }
}
</style>
