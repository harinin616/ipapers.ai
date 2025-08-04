<template> 
  <div ref="container" class="graph3d">
  </div>
</template>

<script setup lang="ts">
import ForceGraph3D from '3d-force-graph'
import * as THREE from 'three'
import { onMounted, onBeforeUnmount, ref, watch, nextTick } from 'vue'
import * as d3 from 'd3-force'
import { scaleOrdinal } from 'd3-scale'
import { schemeCategory10, schemePastel1  } from 'd3-scale-chromatic'
const palette = schemeCategory10  // ['#1f77b4', '#ff7f0e', …]

// 建一个简单的“ID→颜色”映射

const colorScale = scaleOrdinal<string,string>(schemePastel1)
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

let ro: ResizeObserver | null = null
let resizeRaf = 0

function handleResize() {
  if (!graphInst || !container.value) return
  cancelAnimationFrame(resizeRaf)
  resizeRaf = requestAnimationFrame(() => {
    const rect = container.value!.getBoundingClientRect()
    graphInst.width(rect.width).height(rect.height)
    // 可选：同步像素比，避免模糊
    const r = graphInst.renderer?.()
    r?.setPixelRatio?.(Math.min(2, window.devicePixelRatio || 1))
    // 标签重新贴边（你已有的方法）
    updateLabelPositions?.()
  })
}

/* Build data */
const buildData = () => ({
  nodes: props.papers.map((p, idx) => ({
    id   : p.id,
    name : p.title,
    val  : Math.max(2, p.size),
    paper: p,
    // ← 引用式标签：序号 + 第一作者姓 + 年份
    line1: String(idx + 1),                               // ① 序号
  line2: `${ p.authors.length > 0
  ? p.authors[0].split(' ')[0]
  : '' } ${p.published_date.slice(0,4)}` // ② 姓+年
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

function makeLabelSprite(line1: string, line2: string, radius: number) {
  const DPR  = window.devicePixelRatio || 2

  // —— 字体大小（行 1 略大，行 2 略小，可自行调整）
  const font1 = 44 * DPR
  const font2 = 32 * DPR
  const gap   = 12 * DPR          // 行间距

  /* ---------- 计算宽高 ---------- */
  const cvs  = document.createElement('canvas')
  const ctx  = cvs.getContext('2d')!

  ctx.font = `600 ${font1}px sans-serif`
  const w1 = ctx.measureText(line1).width

  ctx.font = `500 ${font2}px sans-serif`
  const w2 = ctx.measureText(line2).width

  const W = Math.max(w1, w2)
  const H = font1 + gap + font2

  cvs.width  = W
  cvs.height = H

  /* ---------- 实际绘制 ---------- */
  ctx.textAlign    = 'center'
  ctx.textBaseline = 'top'

  // 行 1
  ctx.font      = `600 ${font1}px sans-serif`
  ctx.fillStyle = '#000'
  ctx.fillText(line1, W / 2, 0)

  // 行 2
  ctx.font      = `500 ${font2}px sans-serif`
  ctx.fillText(line2, W / 2, font1 + gap)

  /* ---------- 转成 Sprite ---------- */
  const tex   = new THREE.CanvasTexture(cvs)
  const mat   = new THREE.SpriteMaterial({ map: tex, transparent: true, depthWrite: false, depthTest : true })
  const spr   = new THREE.Sprite(mat)
  spr.userData.offset = radius + 0.1

  const scale = radius * 0.8 / DPR          // 整体缩放
  spr.scale.set(W / font1 * scale, H / font1 * scale, 1)

  // 贴近球面（比以前低一点点）
  spr.position.set(0, radius * 0.5, 0)

  return spr
}


onMounted(async () => {
    await nextTick()
  if (!container.value) return

  const width  = container.value.offsetWidth
  const height = container.value.offsetHeight


  const FG = (ForceGraph3D as any).default ?? ForceGraph3D

  graphInst = FG()(container.value)
    .graphData(buildData())
    .width(width)
    .height(height)

  

    // ... nodeThreeObject/linkWidth/linkColor 等保持不变 ...
  graphInst.d3Force('center', d3.forceCenter(0, 0, 0))
  graphInst.d3Force('gravity', d3.forceRadial(0, 0, 0).strength(0.005))
  // --- 立体小球节点 ---
.nodeThreeObject((n: any) => {
  const group  = new THREE.Group()

  // 球
  const radius = THREE.MathUtils.mapLinear(n.val, 2, 50, 10, 25)

   const clr = colorScale((n.id).toString())   
  const sphere = new THREE.Mesh(
    new THREE.SphereGeometry(radius, 32, 32),
    getSphereMat(clr)
  )
  group.add(sphere)

   const sprite = makeLabelSprite(n.line1, n.line2, radius)
  // **用真·半径做上方偏移**，比如贴在球顶端稍上
  sprite.position.set(0, 0, 0)
  // 存偏移
  sprite.userData.offset = radius + 2
  group.add(sprite)


  return group
})
.nodeThreeObjectExtend(false)


    // --- 粗实线条 ---
    .linkWidth((l: any) => THREE.MathUtils.mapLinear(l.weight || 1, 1, 5, 0.2, 2))
    .linkColor(() => '#1e3a8a')
    .linkOpacity(0.8)

    // 点击节点打开链接
      .onNodeClick((n: any) => {
        emit('update:modelValue', n.paper || null)
          emit('node-click', n.paper || null)
         focusNode(n)
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

 graphInst.onEngineTick(() => {
  const camPos = graphInst.cameraPosition()!
  graphInst.scene().traverse(obj => {
    if ((obj as any).isSprite) {
      const sprite = obj as THREE.Sprite
      const group = sprite.parent!
      // 球心 world 坐标
      const worldCenter = new THREE.Vector3()
      group.getWorldPosition(worldCenter)
      // 计算摄像机指向球心的向量
      const dir = new THREE.Vector3().subVectors(camPos, worldCenter).normalize()
      // newWorldPos = worldCenter + dir * offset
      const newWorldPos = worldCenter.clone().add(dir.multiplyScalar(sprite.userData.offset))
      // 转回 local
      const newLocal = group.worldToLocal(newWorldPos)
      sprite.position.copy(newLocal)
      // 保证朝向摄像机
       obj.lookAt(camPos.x, camPos.y, camPos.z)
    }
  })
})
const controls = graphInst.controls()
  if (controls) {
    // 每次相机有变动，就重新贴标签
    controls.addEventListener('change', updateLabelPositions)
    // 也可以多贴一次，确保一开始就对齐
    updateLabelPositions()
  }
   window.addEventListener('resize', resizeGraph)
  // 用 ResizeObserver 监听容器尺寸变化
  ro = new ResizeObserver(handleResize)
  ro.observe(container.value)
  // 首次强制同步一次
  handleResize()
})


function updateLabelPositions() {
  const camPos = graphInst.cameraPosition()!
  graphInst.scene().traverse(obj => {
    if ((obj as any).isSprite) {
      const sprite = obj as THREE.Sprite
      const group  = sprite.parent!           // group 内含 sphere + sprite
      const offset = sprite.userData.offset   // 你事先存好的 radius + ε

      // 球心 world 坐标
      const worldCenter = new THREE.Vector3()
      group.getWorldPosition(worldCenter)

      // 计算方向并更新位置
      const dir = new THREE.Vector3()
        .subVectors(camPos, worldCenter)
        .normalize()
      const worldPos = worldCenter.clone().add(dir.multiplyScalar(offset))
      // 转回 local
      const localPos = group.worldToLocal(worldPos)
      sprite.position.copy(localPos)

      // 三维 Sprite 本身就是 billboard，不用自己 lookAt
      // sprite.lookAt(camPos.x, camPos.y, camPos.z)
    }
  })
}
watch(() => props.papers, () => {
  if (graphInst) graphInst.graphData(buildData())
}, { deep: true })

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeGraph)
  graphInst?.destroy?.()
})


const emit = defineEmits<{
  (e: 'update:modelValue', val: Paper|null): void
    (e: 'node-click', paper: Paper|null): void
}>()

// 点击节点时改成：
function onNodeClick(node: Paper) {
  emit('update:modelValue', node)
}

// 如果要取消选中，也可以发 null
function clearSelection() {
  emit('update:modelValue', null)
}

function focusNode(node: any) {
  if (!graphInst || !node) return

  // 距离系数：让相机在目标前方 distance 像素处
  const distance = 200
  const distRatio = 1 + distance / Math.hypot(node.x, node.y, node.z)

  graphInst.cameraPosition(
    {               // 相机位置
      x: node.x * distRatio,
      y: node.y * distRatio,
      z: node.z * distRatio
    },
    node,           // 视线焦点
    2000            // 动画时长（ms）
  )
}


watch(
  () => props.modelValue,
  (p) => {
    if (!p || !graphInst) return

    const key = (p as any).id ?? (p as any).paper_id   // ★ 兼容两种字段
    if (!key) return

    const node = graphInst.graphData().nodes
      .find((n: any) => n.id === key)

    if (node) focusNode(node)
  },
  { immediate: true }
)

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
/* 限制画布不要超出它的父容器高度 */
.graph3d {
  position: relative; /* 已有 */
  overflow: hidden;   /* 新增：隐藏超出的部分 */
}

/* 强制画布铺满容器，而不是保持最初 mount 时的固定像素高度 */
.graph3d canvas {
  display: block;           /* 去掉默认 inline-block 间隙 */
  width: 100%  !important;  /* 强制撑满宽度 */
  height: 100% !important;  /* 强制撑满高度 */
}
.graph3d { width: 100%; height: 100%; min-width: 0; min-height: 0; }


</style>
