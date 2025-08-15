<template>
  <div ref="container" class="graph3d"></div>
</template>

<script setup lang="ts">
import ForceGraph3D from '3d-force-graph'
import * as THREE from 'three'
import { onMounted, onBeforeUnmount, ref, watch, nextTick } from 'vue'
import * as d3 from 'd3-force'
import { scaleOrdinal } from 'd3-scale'
import { schemeCategory10 } from 'd3-scale-chromatic'

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

const props = defineProps<{ papers: Paper[]; modelValue: Paper | null }>()
const emit = defineEmits<{
  (e: 'update:modelValue', val: Paper | null): void
  (e: 'node-click', paper: Paper | null): void
}>()

/* ===================== 可调参数 ===================== */
/** 有边的节点，向邻居色靠近的比例（更小 → 更多样） */
const T_EDGE             = 0.50
/** 整体更浅、更柔和 */
const LIGHTEN_BASE       = 0.26
const LIGHTNESS_FLOOR    = 0.80
const SATURATION_DROP    = 0.10
const SAT_ISO_BOOST      = 0.07
/** 颜色多样化：在各自类别色附近再“展开”一圈（±值越大越多彩） */
const HUE_SPREAD_NODE    = 0.28  // 所有节点的基于类别的“分散”半径
const HUE_JITTER_CONN    = 0.008  // 有边时微抖（更小）
const HUE_JITTER_ISO     = 0.028  // 孤立点抖动（更大，拉开差异）
/** 连通分量内的轻微明度起伏（避免一刀切） */
const COMP_LIGHTNESS_JIT = 0.035

/* ===================== 工具函数 ===================== */
const clamp01 = (x: number) => Math.max(0, Math.min(1, x))
function hashStr(s: string) { let h = 5381; for (let i=0;i<s.length;i++) h=((h<<5)+h)+s.charCodeAt(i); return h>>>0 }
function hexToRgb(hex: string) {
  const m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex)
  if (!m) return { r: 0, g: 0, b: 0 }
  return { r: parseInt(m[1],16), g: parseInt(m[2],16), b: parseInt(m[3],16) }
}
function rgbToHex(r: number, g: number, b: number) {
  const toHex = (x: number) => Math.max(0, Math.min(255, Math.round(x))).toString(16).padStart(2,'0')
  return `#${toHex(r)}${toHex(g)}${toHex(b)}`
}
function rgbToHsl(r: number, g: number, b: number) {
  r/=255; g/=255; b/=255
  const max=Math.max(r,g,b), min=Math.min(r,g,b)
  let h=0,s=0,l=(max+min)/2
  if (max!==min) {
    const d=max-min
    s=l>0.5? d/(2-max-min) : d/(max+min)
    switch(max){
      case r: h=(g-b)/d + (g<b?6:0); break
      case g: h=(b-r)/d + 2; break
      case b: h=(r-g)/d + 4; break
    }
    h/=6
  }
  return { h, s, l }
}
function hslToRgb(h:number,s:number,l:number){
  let r:number,g:number,b:number
  if (s===0){ r=g=b=l }
  else{
    const hue2rgb=(p:number,q:number,t:number)=>{
      if(t<0)t+=1; if(t>1)t-=1
      if(t<1/6) return p+(q-p)*6*t
      if(t<1/2) return q
      if(t<2/3) return p+(q-p)*(2/3 - t)*6
      return p
    }
    const q=l<0.5? l*(1+s) : l + s - l*s
    const p=2*l - q
    r=hue2rgb(p,q,h+1/3); g=hue2rgb(p,q,h); b=hue2rgb(p,q,h-1/3)
  }
  return { r:r*255, g:g*255, b:b*255 }
}
function hslToHex(h:number,s:number,l:number){
  const {r,g,b}=hslToRgb(h,s,l); return rgbToHex(r,g,b)
}
/* 圆弧最短路径插值 */
function mixAngle(a:number,b:number,t:number){
  let d=((b-a+1.5)%1)-0.5
  return (a + d*t + 1) % 1
}

/* ===================== 调色：Category10 基色 + 多样化展开 + 轻微邻居靠拢 ===================== */
const baseColorScale = scaleOrdinal<string,string>(schemeCategory10)
const baseHueByNode   = new Map<string, number>() // node -> 类别基 hue
const spreadHueByNode = new Map<string, number>() // node -> 基 hue 上的展开（多样化）
const neighborHueByNode = new Map<string, number>() // node -> 邻居圆均值 hue
const degreeMap = new Map<string, number>()
const compMap = new Map<string, number>()
const adjMap = new Map<string, string[]>()

function computeConnectivity(nodes:any[], links:any[]){
  degreeMap.clear(); compMap.clear(); adjMap.clear()
  nodes.forEach(n=>adjMap.set(n.id,[]))
  links.forEach(l=>{
    const a=String(l.source), b=String(l.target)
    if (adjMap.has(a)&&adjMap.has(b)){
      adjMap.get(a)!.push(b); adjMap.get(b)!.push(a)
      degreeMap.set(a,(degreeMap.get(a)||0)+1)
      degreeMap.set(b,(degreeMap.get(b)||0)+1)
    }
  })
  let cid=0
  for(const n of nodes){
    if (compMap.has(n.id)) continue
    cid++
    const q=[n.id]; compMap.set(n.id,cid)
    while(q.length){
      const u=q.pop()!
      for(const v of (adjMap.get(u) || [])) if(!compMap.has(v)){ compMap.set(v,cid); q.push(v) }
    }
  }
}

function precomputeHues(nodes:any[]){
  baseHueByNode.clear(); spreadHueByNode.clear(); neighborHueByNode.clear()

  // 1) 类别 → Category10 hex → hue
  const catHueCache = new Map<string, number>()
  function hexToHue(hex:string){
    const {r,g,b}=hexToRgb(hex); const {h}=rgbToHsl(r,g,b); return h
  }
  for (const n of nodes){
    const p:Paper = n.paper
    const cat = p.categories?.[0] || 'uncategorized'
    const hex = baseColorScale(cat)
    const h = catHueCache.has(hex) ? catHueCache.get(hex)! : (()=>{ const hh=hexToHue(hex); catHueCache.set(hex,hh); return hh })()
    baseHueByNode.set(n.id, h)
  }

  // 2) 在各自类别 hue 附近做“展开”（每个节点都有一点点不同 → 更五彩）
  for (const n of nodes){
    const p:Paper = n.paper
    const hb = baseHueByNode.get(n.id)!
    const spread = (((hashStr('s'+(p.paper_id || n.id))%1000)/1000)-0.5) * 2 * HUE_SPREAD_NODE
    spreadHueByNode.set(n.id, (hb + spread + 1) % 1)
  }

  // 3) 计算邻居圆均值（用于“轻微靠拢”的目标）
  for (const n of nodes){
    const h0 = spreadHueByNode.get(n.id)!  // 用展开后的色相来平均，避免“拉回”到同色
    const nb = adjMap.get(n.id) || []
    if (!nb.length){ neighborHueByNode.set(n.id, h0); continue }
    let sx=Math.cos(2*Math.PI*h0), sy=Math.sin(2*Math.PI*h0)
    for(const v of nb){
      const hv = spreadHueByNode.get(v)
      if (hv!=null){ sx+=Math.cos(2*Math.PI*hv); sy+=Math.sin(2*Math.PI*hv) }
    }
    const ang=Math.atan2(sy,sx)/(2*Math.PI)
    neighborHueByNode.set(n.id, (ang+1)%1)
  }
}

/* 节点颜色：五彩浅色；有边只轻微靠拢 */
function getNodeColor(n:any){
  const id=String(n.id)
  const p:Paper = n.paper
  const deg = degreeMap.get(id)||0
  const compId = compMap.get(id)||0

  const h0 = spreadHueByNode.get(id) ?? 0
  const hn = neighborHueByNode.get(id) ?? h0

  // 只轻微靠拢（避免一片同色）
  const h1 = mixAngle(h0, hn, deg>0 ? T_EDGE : 0)

  // 轻微抖动：有边更小、孤立更大
  const jitter = (((hashStr('h'+(p.paper_id||id))%1000)/1000)-0.5) * 2 * (deg>0? HUE_JITTER_CONN : HUE_JITTER_ISO)
  const h = (h1 + jitter + 1) % 1

  // 取 Category10 的原始 s,l，再做“整体更浅/更柔”
  const baseHex = baseColorScale(p.categories?.[0] || 'uncategorized')
  const {s:sBase, l:lBase} = rgbToHsl(...Object.values(hexToRgb(baseHex)) as unknown as [number,number,number])

  let s = clamp01(sBase - SATURATION_DROP + (deg>0 ? 0 : SAT_ISO_BOOST))
  let l = Math.max(LIGHTNESS_FLOOR, Math.min(0.9, lBase + LIGHTEN_BASE))

  // 分量内明度微起伏
  const dlComp = (((hashStr('L'+compId)%1000)/1000)-0.5) * 2 * COMP_LIGHTNESS_JIT
  l = clamp01(l + dlComp)

  return hslToHex(h, s, l)
}

/* ============== 构图（每对仅一条边） ============== */
const buildData = () => {
  const nodes = props.papers.map((p, idx)=>({
    id: p.id,
    name: p.title,
    val: Math.max(2, p.size),
    paper: p,
    line1: String(idx+1),
    line2: `${p.authors.length? p.authors[0].split(' ')[0] : ''} ${p.published_date.slice(0,4)}`
  }))

  const nodeSet = new Set(nodes.map(n=>n.id))
  const seen = new Set<string>()
  const links:Array<{source:string; target:string; weight:number}> = []
  for (const p of props.papers){
    const src=p.id
    for (const tgt of (p.cites??[])){
      if (!nodeSet.has(tgt)) continue
      const a = src<tgt? src:tgt, b = src<tgt? tgt:src
      const key = `${a}|${b}`
      if (seen.has(key)) continue
      seen.add(key)
      links.push({ source:src, target:tgt, weight:1 })
    }
  }

  computeConnectivity(nodes, links)
  precomputeHues(nodes)
  return { nodes, links }
}

/* ===================== Three 材质/标签 ===================== */
const sphereMatCache:Record<string,THREE.MeshPhongMaterial> = {}
function getSphereMat(color:string){
  return sphereMatCache[color] ??= new THREE.MeshPhongMaterial({
    color, shininess: 50, specular: 0x555555 as any
  })
}

/* 标签：黑字更粗、白描边更细（更显眼但不糊） */
function makeLabelSprite(line1:string, line2:string, radius:number){
  const DPR  = window.devicePixelRatio || 2
  const font1 = 60 * DPR   // 黑更粗
  const font2 = 48 * DPR
  const gap   = 10 * DPR

  const cvs  = document.createElement('canvas')
  const ctx  = cvs.getContext('2d')!

  ctx.font = `950 ${font1}px ui-sans-serif, -apple-system, Segoe UI, Inter, Helvetica, Arial`
  const w1 = ctx.measureText(line1).width
  ctx.font = `900 ${font2}px ui-sans-serif, -apple-system, Segoe UI, Inter, Helvetica, Arial`
  const w2 = ctx.measureText(line2).width

  const W = Math.max(w1, w2)
  const H = font1 + gap + font2
  cvs.width = W; cvs.height = H

  ctx.textAlign = 'center'
  ctx.textBaseline = 'top'

  // 行1：更细白描边 + 粗黑字
  ctx.font = `950 ${font1}px ui-sans-serif, -apple-system, Segoe UI, Inter, Helvetica, Arial`
  ctx.lineWidth = 2.2 * DPR
  ctx.strokeStyle = 'rgba(255,255,255,0.72)'
  ctx.strokeText(line1, W/2, 0)
  ctx.fillStyle = '#000'
  ctx.fillText(line1, W/2, 0)

  // 行2：更细
  ctx.font = `900 ${font2}px ui-sans-serif, -apple-system, Segoe UI, Inter, Helvetica, Arial`
  ctx.lineWidth = 1.8 * DPR
  ctx.strokeStyle = 'rgba(255,255,255,0.68)'
  ctx.strokeText(line2, W/2, font1 + gap)
  ctx.fillStyle = '#000'
  ctx.fillText(line2, W/2, font1 + gap)

  const tex = new THREE.CanvasTexture(cvs)
  const mat = new THREE.SpriteMaterial({ map: tex, transparent: true, depthWrite: false, depthTest: true })
  const spr = new THREE.Sprite(mat)
  spr.userData.offset = radius + 1.4

  const scale = radius * 0.75 / DPR
  spr.scale.set(W / font1 * scale, H / font1 * scale, 1)
  spr.position.set(0, radius * 0.5, 0)
  return spr
}

/* ===================== Graph 生命周期 ===================== */
const container = ref<HTMLDivElement>()
let graphInst:any=null, ro:ResizeObserver|null=null
let resizeRaf=0

function updateLabelPositions(){
  if (!graphInst) return
  const camPos = graphInst.cameraPosition()
  if (!camPos) return
  graphInst.scene().traverse(obj=>{
    if ((obj as any).isSprite){
      const sprite = obj as THREE.Sprite
      const group  = sprite.parent!
      const offset = sprite.userData.offset
      const worldCenter = new THREE.Vector3()
      group.getWorldPosition(worldCenter)
      const dir = new THREE.Vector3().subVectors(camPos, worldCenter).normalize()
      const worldPos = worldCenter.clone().add(dir.multiplyScalar(offset))
      const localPos = group.worldToLocal(worldPos)
      sprite.position.copy(localPos)
    }
  })
}
function handleResize(){
  if (!graphInst || !container.value) return
  cancelAnimationFrame(resizeRaf)
  resizeRaf = requestAnimationFrame(()=>{
    const rect = container.value!.getBoundingClientRect()
    graphInst.width(rect.width).height(rect.height)
    graphInst.renderer?.()?.setPixelRatio?.(Math.min(2, window.devicePixelRatio || 1))
    updateLabelPositions()
  })
}
function resizeGraph(){
  if (graphInst && container.value){
    graphInst.width(container.value.offsetWidth)
    graphInst.height(container.value.offsetHeight)
  }
}
function focusNode(node:any){
  if (!graphInst || !node) return
  const distance = 200
  const distRatio = 1 + distance/Math.hypot(node.x,node.y,node.z)
  graphInst.cameraPosition(
    { x:node.x*distRatio, y:node.y*distRatio, z:node.z*distRatio },
    node, 2000
  )
}

onMounted(async ()=>{
  await nextTick()
  if (!container.value) return

  const width = container.value.offsetWidth
  const height= container.value.offsetHeight
  const FG = (ForceGraph3D as any).default ?? ForceGraph3D

  graphInst = FG()(container.value)
    .graphData(buildData())
    .width(width).height(height)
    .nodeThreeObject((n:any)=>{
      const group = new THREE.Group()
      const radius = THREE.MathUtils.mapLinear(n.val, 2, 50, 10, 25)
      const clr = getNodeColor(n)
      const sphere = new THREE.Mesh(new THREE.SphereGeometry(radius,32,32), getSphereMat(clr))
      group.add(sphere)
      const sprite = makeLabelSprite(n.line1, n.line2, radius)
      sprite.userData.offset = radius + 2
      group.add(sprite)
      return group
    })
    .nodeThreeObjectExtend(false)
    .linkWidth((l:any)=>THREE.MathUtils.mapLinear(l.weight||1,1,5,0.2,2))
    .linkColor(()=> '#1e3a8a')
    .linkOpacity(0.8)
    .linkCurvature(0)
    .onNodeClick((n:any)=>{ emit('update:modelValue', n.paper||null); emit('node-click', n.paper||null); focusNode(n) })

  graphInst.d3Force('center', d3.forceCenter(0,0,0))
  graphInst.d3Force('gravity', d3.forceRadial(0,0,0).strength(0.005))

  // ✅ 恢复可见的柔和天空渐变背景（不会突兀，也不会“看不见”）
  {
    const canvas=document.createElement('canvas')
    canvas.width=1; canvas.height=512
    const ctx=canvas.getContext('2d')!
    const g=ctx.createLinearGradient(0,0,0,512)
    g.addColorStop(0,'#CFE6FF')  // 顶部稍亮的天蓝
    g.addColorStop(0.6,'#EAF3FF') // 过渡
    g.addColorStop(1,'#FFFFFF')   // 底部白
    ctx.fillStyle=g; ctx.fillRect(0,0,1,512)
    graphInst.scene().background = new THREE.CanvasTexture(canvas)
  }

  const ctrls = graphInst.controls()
  if (ctrls){
    ctrls.autoRotate = true
    ctrls.autoRotateSpeed = 1.0
    ctrls.enableDamping = true
    ctrls.dampingFactor = 0.06
    ctrls.rotateSpeed = 0.35
    ctrls.addEventListener('change', updateLabelPositions)
  }
  graphInst.onEngineTick(updateLabelPositions)
  graphInst.showNavInfo(false)
  graphInst.renderer?.()?.setPixelRatio?.(Math.min(2, window.devicePixelRatio || 1))

  window.addEventListener('resize', resizeGraph)
  ro = new ResizeObserver(handleResize)
  ro.observe(container.value)
  handleResize()
})

watch(()=>props.modelValue, (p)=>{
  if (!p || !graphInst) return
  const key = (p as any).id ?? (p as any).paper_id
  if (!key) return
  const node = graphInst.graphData().nodes.find((n:any)=>n.id===key)
  if (node) focusNode(node)
},{ immediate:true })

watch(()=>props.papers, ()=>{
  if (graphInst) graphInst.graphData(buildData())
},{ deep:true })

onBeforeUnmount(()=>{
  window.removeEventListener('resize', resizeGraph)
  ro?.disconnect()
  graphInst?.destroy?.()
})
</script>

<style scoped>
.graph3d{
  width:100%; height:100%;
  min-width:0; min-height:0;
  position:relative; overflow:hidden;
  border:1px solid #e5e7eb; border-radius:12px;
  background:#fff; box-shadow:0 6px 18px rgba(15,23,42,.05);
}
.graph3d canvas{ display:block; width:100% !important; height:100% !important; }
</style>