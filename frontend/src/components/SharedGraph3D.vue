<template>
  <div ref="container" class="graph3d">>
  </div>
</template>

<script setup lang="ts">
import ForceGraph3D from '3d-force-graph'
import * as THREE from 'three'
import { onMounted, onBeforeUnmount, ref, watch, nextTick } from 'vue'
import * as d3 from 'd3-force'

/* Props */
const props = defineProps<{
  papers: { id: string; label: string; size: number; link?: string; cites?: string[] }[]
}>()

/* Refs */
const container = ref<HTMLDivElement>()
let graphInst: any = null

/* Build data */
const buildData = () => ({
  nodes: props.papers.map(p => ({
    id:   p.id,
    name: p.label,
    val:  Math.max(2, p.size),
    link: p.link
  })),
  links: props.papers.flatMap(p =>
    (p.cites ?? []).map(t => ({ source: p.id, target: t, weight: 1 }))
  )
})

/* Sphere material cache */
const sphereMatCache: Record<string, THREE.MeshPhongMaterial> = {}
function getSphereMat(color: string) {
  return sphereMatCache[color] ??= new THREE.MeshPhongMaterial({
    color, shininess: 50, specular: 0x555555
  })
}

function resizeGraph() {
  if (graphInst && container.value) {
    graphInst.width(container.value.offsetWidth)
    graphInst.height(container.value.offsetHeight)
  }
}

onMounted(async () => {
  await nextTick()
  if (!container.value) return

  const FG = (ForceGraph3D as any).default ?? ForceGraph3D

  graphInst = FG()(container.value)
    .graphData(buildData())

    // 设置尺寸，防止全屏
    .width(container.value.offsetWidth)
    .height(container.value.offsetHeight)

    // --- 立体小球节点 ---
    .nodeThreeObject((n: any) => {
      const radius = THREE.MathUtils.mapLinear(n.val, 2, 50, 10, 25)
      const geo = new THREE.SphereGeometry(radius, 128, 128)
      const col = new THREE.Color().setHSL(Math.random(), 0.6, 0.5).getStyle()
      return new THREE.Mesh(geo, getSphereMat(col))
    })

    // --- 粗实线条 ---
    .linkWidth((l: any) => THREE.MathUtils.mapLinear(l.weight || 1, 1, 5, 0.2, 2))
    .linkColor(() => '#1e3a8a')
    .linkOpacity(0.8)

    // 点击节点打开链接
    .onNodeClick((n: any) => n.link && window.open(n.link, '_blank'))

const scene = graphInst.scene()

const canvas = document.createElement('canvas')
canvas.width = 1
canvas.height = 512
const ctx = canvas.getContext('2d')!

const gradient = ctx.createLinearGradient(0, 0, 0, 512)
gradient.addColorStop(0, '#87CEFA')   // 顶部：天蓝色（真实天空色）
gradient.addColorStop(0.7, '#f0f4ff') // 中部：柔和过渡
gradient.addColorStop(1, '#fdf6ec')   // 底部：暖白色，模拟地面反射

ctx.fillStyle = gradient
ctx.fillRect(0, 0, 1, 512)

const texture = new THREE.CanvasTexture(canvas)
scene.background = texture


  // 自动旋转
  const ctrls = graphInst.controls()
  if (ctrls) { ctrls.autoRotate = true; ctrls.autoRotateSpeed = 1.2 }
  ctrls.showDefaultControls = false
  graphInst.showNavInfo(false)
  // 监听窗口 resize
  window.addEventListener('resize', resizeGraph)
   graphInst.d3Force('center', d3.forceCenter(0, 0, 0))
  graphInst.d3Force('gravity', d3.forceRadial(0, 0, 0).strength(0.005))
  
  
})

watch(() => props.papers, () => {
  if (graphInst) graphInst.graphData(buildData())
}, { deep: true })

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeGraph)
  graphInst?.destroy?.()
})
</script>

<style scoped>
.graph3d {
  width: 100%;
  height: 100%;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #ffffff;
}
.graph3d {
  position: relative;  /* 重点：限制子元素绝对定位范围 */
}
</style>
