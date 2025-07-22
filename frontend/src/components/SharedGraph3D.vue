<template>
  <div ref="container" class="graph3d">>
  </div>
</template>

<script setup lang="ts">
import ForceGraph3D from '3d-force-graph'
import * as THREE from 'three'
import { onMounted, onBeforeUnmount, ref, watch, nextTick } from 'vue'
import * as d3 from 'd3-force'

export interface Paper {
  link?: string
  cites?: string[] 

  id: string
  size: number
  paper_id: string
  title: string
  pdf_url: string
  abstract: string
  authors: string[]
  categories: string[]
  published_date: string

}
/* Props */
const props = defineProps<{
  papers: Paper[]
  modelValue: Paper | null
}>()

/* Refs */
const container = ref<HTMLDivElement>()
let graphInst: any = null

/* Build data */
const buildData = () => ({
  nodes: props.papers.map(p => ({
    id:    p.id,
    name:  p.title,
    val:   Math.max(2, p.size),
    paper: p      // ← 这里把整条 Paper 绑到 node 上
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

  const width  = container.value.offsetWidth
  const height = container.value.offsetHeight
  const centerX = width  / 2
  const centerY = height / 2

  const FG = (ForceGraph3D as any).default ?? ForceGraph3D

  graphInst = FG()(container.value)
    .graphData(buildData())
    .width(width)
    .height(height)
    // ... nodeThreeObject/linkWidth/linkColor 等保持不变 ...

  // 1. 让布局中心是容器正中央
  graphInst.d3Force(
    'center',
    d3.forceCenter(centerX, centerY, 0)
  )

  // 2. 可选：如果你还想让 radial 力也以容器中心为圆心，
  //    且半径是容器最小边长的一半：
  graphInst.d3Force(
    'gravity',
    d3.forceRadial(
      Math.min(width, height) / 2,
      centerX,
      centerY
    ).strength(0.005)
  )

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
      .onNodeClick((n: any) => {
        emit('update:modelValue', n.paper || null)
      })

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

const emit = defineEmits<{
  (e: 'update:modelValue', val: Paper|null): void
}>()

// 点击节点时改成：
function onNodeClick(node: Paper) {
  emit('update:modelValue', node)
}

// 如果要取消选中，也可以发 null
function clearSelection() {
  emit('update:modelValue', null)
}
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
