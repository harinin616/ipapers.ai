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
  nodes: props.papers.map((p, idx) => ({
    id   : p.id,
    name : p.title,
    val  : Math.max(2, p.size),
    paper: p,
    // ← 引用式标签：序号 + 第一作者姓 + 年份
    line1: String(idx + 1),                               // ① 序号
  line2: `${p.authors[0].split(' ')[0]} ${p.published_date.slice(0,4)}` // ② 姓+年
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
  const mat   = new THREE.SpriteMaterial({ map: tex, transparent: true, depthWrite: false   })
  
  const spr   = new THREE.Sprite(mat)
  spr.userData.offset = radius + 1

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
  const group  = new THREE.Group()

  // 球
  const radius = THREE.MathUtils.mapLinear(n.val, 2, 50, 10, 25)
  const sphere = new THREE.Mesh(
    new THREE.SphereGeometry(radius, 32, 32),
    getSphereMat(new THREE.Color().setHSL(Math.random(), 0.6, 0.5).getStyle())
  )


  sphere.renderOrder = 0
group.add(sphere)

// 标签
const spr = makeLabelSprite(n.line1, n.line2, radius)
spr.renderOrder = 1    // ★ 在本球之后绘制，但仍参与深度测试
group.add(spr)
  return group
})
.nodeThreeObjectExtend(true)   


    // --- 粗实线条 ---
    .linkWidth((l: any) => THREE.MathUtils.mapLinear(l.weight || 1, 1, 5, 0.2, 2))
    .linkColor(() => '#1e3a8a')
    .linkOpacity(0.8)

    // 点击节点打开链接
      .onNodeClick((n: any) => {
        emit('update:modelValue', n.paper || null)
         focusNode(n)
      })
// 让每帧都把标签推到球正前方
graphInst.scene().onBeforeRender = (_, __, camera) => {
  const camPos = camera.position

  graphInst.graphData().nodes.forEach((n: any) => {
    const grp = n.__threeObj           // ForceGraph 给每个节点挂的 Group
    if (!grp) return

    // 找到 Group 里的 Sprite（假定你只有 球 + sprite 两个孩子）
    const sprite = grp.children.find((c: any) => c.isSprite)
    if (!sprite) return

    // 球心的世界坐标
    const worldPos = new THREE.Vector3()
    grp.getWorldPosition(worldPos)

    // 方向：球心 → 相机
    const dir = new THREE.Vector3().subVectors(camPos, worldPos).normalize()

    // 把 sprite 放到球面正向相机处
   const targetW = worldPos.clone().add(dir.multiplyScalar(sprite.userData.offset)) // 世界坐标
const targetL = grp.worldToLocal(targetW)     // ★ 转回 group 局部坐标
sprite.position.copy(targetL)

  })
}

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
</style>
