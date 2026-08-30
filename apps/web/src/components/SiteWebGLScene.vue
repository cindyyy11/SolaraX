<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import type { InspectionRoute } from '@/types/inspection'

const props = defineProps<{ route: InspectionRoute; activeWaypoint: number; severity: number; scenarioActive: boolean; cameraPreset: 'overview' | 'roof' | 'anomaly' | 'drone' }>()
const host = ref<HTMLDivElement>()
let renderer: THREE.WebGLRenderer | undefined
let scene: THREE.Scene | undefined
let camera: THREE.PerspectiveCamera | undefined
let controls: OrbitControls | undefined
let drone: THREE.Group | undefined
let routeLine: THREE.Line | undefined
let animationFrame = 0
let routeProgress = 0
let lastTime = 0
let resizeObserver: ResizeObserver | undefined

function material(color: number, emissive = 0) {
  return new THREE.MeshStandardMaterial({ color, emissive, roughness:.65, metalness:.15 })
}

function buildScene() {
  if (!host.value) return
  scene = new THREE.Scene()
  scene.background = new THREE.Color(0x07100e)
  scene.fog = new THREE.Fog(0x07100e, 14, 30)
  camera = new THREE.PerspectiveCamera(42, 1, .1, 100)
  camera.position.set(9, 9, 10)
  renderer = new THREE.WebGLRenderer({ antialias:true, alpha:false, powerPreference:'high-performance' })
  renderer.setPixelRatio(Math.min(devicePixelRatio, 1.7))
  renderer.shadowMap.enabled = true
  renderer.outputColorSpace = THREE.SRGBColorSpace
  host.value.appendChild(renderer.domElement)

  scene.add(new THREE.HemisphereLight(0xd7f4ff, 0x11201b, 2.2))
  const sun = new THREE.DirectionalLight(0xffddb0, 3.2); sun.position.set(6,8,9); sun.castShadow = true; scene.add(sun)
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(28,22), material(0x12231e)); ground.rotation.x = -Math.PI/2; ground.receiveShadow = true; scene.add(ground)

  const buildingColor = props.route.building === 'ground-array' ? 0x172a24 : 0x39423f
  if (props.route.building !== 'ground-array') {
    const building = new THREE.Mesh(new THREE.BoxGeometry(props.route.building === 'commercial' ? 11 : 12, 1.5, 7), material(buildingColor)); building.position.y=.75; building.receiveShadow=true; scene.add(building)
  }

  const panelGroup = new THREE.Group()
  const rows = props.route.building === 'ground-array' ? 4 : 3
  const cols = props.route.building === 'commercial' ? 7 : 8
  for (let row=0; row<rows; row++) for (let col=0; col<cols; col++) {
    const affectedCount = Math.max(1, Math.ceil(cols * Math.min(100, Math.max(10, props.severity)) / 100))
    const affected = props.scenarioActive && (props.route.scenarioId === 'string-underperformance' && col === 3 || props.route.scenarioId === 'thermal-hotspot' && row === 1 && col === 4 || props.route.scenarioId === 'storm-damage' && row === 1 && col >= 3 && col <= 5 || props.route.scenarioId === 'soiling' && col < affectedCount || props.route.scenarioId === 'partial-shading' && row === 0 && col < affectedCount)
    const panel = new THREE.Mesh(new THREE.BoxGeometry(1.05,.09,1.2), material(affected ? 0x9b4034 : 0x174b5b, affected ? 0x3d0904 : 0))
    panel.position.set((col-(cols-1)/2)*1.18, props.route.building === 'ground-array' ? .65 : 1.62, (row-(rows-1)/2)*1.38)
    panel.rotation.x = props.route.building === 'ground-array' ? -.18 : 0
    if (props.route.scenarioId === 'storm-damage' && affected) panel.rotation.z = .12
    panel.castShadow=true; panelGroup.add(panel)
  }
  scene.add(panelGroup)

  const inverterAffected = props.scenarioActive && props.route.scenarioId === 'inverter-derating'
  const inverter = new THREE.Mesh(new THREE.BoxGeometry(.8,1.2,.55), material(inverterAffected ? 0xb94d3e : 0x8b9994, inverterAffected ? 0x45110b : 0)); inverter.position.set(5.2,1,0); scene.add(inverter)
  drone = new THREE.Group(); const body = new THREE.Mesh(new THREE.BoxGeometry(.48,.18,.34), material(0xe9f0ed)); drone.add(body)
  for (const [x,z] of [[.38,.32],[-.38,.32],[.38,-.32],[-.38,-.32]] as Array<[number, number]>) { const rotor = new THREE.Mesh(new THREE.CylinderGeometry(.23,.23,.025,16), material(0x8ca099)); rotor.position.set(x,.08,z); drone.add(rotor) }
  scene.add(drone)

  controls = new OrbitControls(camera, renderer.domElement); controls.enableDamping=true; controls.target.set(0,0,0); controls.enabled = true; controls.maxPolarAngle=Math.PI*.48; controls.minDistance=5; controls.maxDistance=22
  rebuildRoute()
  resizeObserver = new ResizeObserver(resize); resizeObserver.observe(host.value); resize()
  renderer.domElement.setAttribute('aria-label', `${props.route.label}, illustrative 3D inspection scene`)
  animate(0)
}

function rebuildRoute() {
  if (!scene || !drone) return
  if (routeLine) { scene.remove(routeLine); routeLine.geometry.dispose(); (routeLine.material as THREE.Material).dispose() }
  const points = props.route.waypoints.map((point) => new THREE.Vector3(...point.position))
  const curve = new THREE.CatmullRomCurve3(points, props.route.waypoints.length > 2)
  routeLine = new THREE.Line(new THREE.BufferGeometry().setFromPoints(curve.getPoints(80)), new THREE.LineDashedMaterial({ color:0x7be0a5, dashSize:.22, gapSize:.14, transparent:true, opacity:.8 }))
  routeLine.computeLineDistances(); scene.add(routeLine)
  const current = props.route.waypoints[Math.min(props.activeWaypoint, props.route.waypoints.length-1)]!; drone.position.set(...current.position)
  if (camera) { camera.position.set(current.position[0]+4,current.position[1]+3,current.position[2]+4); controls?.target.set(...current.cameraTarget) }
}

function applyCameraPreset() {
  if (!camera || !controls || !drone) return
  const presets = { overview:[9,9,10], roof:[1,8,7], anomaly:[4,4,5], drone:[drone.position.x+3,drone.position.y+2,drone.position.z+3] } as const
  const [x,y,z] = presets[props.cameraPreset]
  camera.position.set(x,y,z); controls.target.copy(props.cameraPreset === 'drone' ? drone.position : new THREE.Vector3(0,0,0)); controls.update()
}

function resize() { if (!host.value || !renderer || !camera) return; const {width,height}=host.value.getBoundingClientRect(); renderer.setSize(width, Math.max(height,360), false); camera.aspect=width/Math.max(height,360); camera.updateProjectionMatrix() }
function animate(time:number) { animationFrame=requestAnimationFrame(animate); const delta=Math.min((time-lastTime)/1000,.05); lastTime=time; if (drone && props.route.waypoints.length>1) { routeProgress=(routeProgress+delta*.06)%1; const curve=new THREE.CatmullRomCurve3(props.route.waypoints.map((p)=>new THREE.Vector3(...p.position)), props.route.waypoints.length>2); drone.position.copy(curve.getPointAt(routeProgress)); } controls?.update(); renderer?.render(scene!,camera!) }

watch(() => [props.route, props.activeWaypoint], rebuildRoute, { deep:true })
watch(() => props.cameraPreset, applyCameraPreset)
onMounted(buildScene)
onBeforeUnmount(() => { cancelAnimationFrame(animationFrame); resizeObserver?.disconnect(); controls?.dispose(); scene?.traverse((item) => { if (item instanceof THREE.Mesh) { item.geometry.dispose(); if (Array.isArray(item.material)) item.material.forEach((m)=>m.dispose()); else item.material.dispose() } }); renderer?.dispose(); renderer?.domElement.remove() })
</script>

<template><div ref="host" class="webgl-scene"></div></template>

<style scoped>
.webgl-scene { position:absolute; inset:0; z-index:2; min-height:360px; }
.webgl-scene :deep(canvas) { display:block; width:100%; height:100%; cursor:grab; }
.webgl-scene :deep(canvas:active) { cursor:grabbing; }
</style>
