<script setup lang="ts">
import { ref, nextTick, watch, onMounted, onBeforeUnmount } from 'vue'
import { Eye } from 'lucide-vue-next'
import Chart from 'chart.js/auto'

interface Metric { total:number; last5:number[] }

const metric   = ref<Metric|null>(null)
const show     = ref(false)

const canvasEl  = ref<HTMLCanvasElement|null>(null)
const wrapperEl = ref<HTMLElement|null>(null)

let   chart: Chart|undefined

// 拉一次数据并更新 metric

async function loadMetric() {
  try {
    const res = await fetch('/api/metrics/site-metric')
    if (!res.ok) throw new Error(res.statusText)
    metric.value = await res.json()
  } catch (e) {
    console.error('metric fetch failed', e)
  }
}

onMounted(() => {
  loadMetric()
})

// 绘图 / 更新
function draw() {
  if (!metric.value || !canvasEl.value) return
  if (chart) {
    chart.data.datasets[0].data = metric.value.last5
    chart.update()
    return
  }
  chart = new Chart(canvasEl.value, {
  type: 'line',
  data: {
    labels: ['', '', '', '', ''],
    datasets: [{
      data: metric.value.last5,
      tension: .4,
      pointRadius: 0,
      borderWidth: 1.5,
      borderColor: '#4ade80'
    }]
  },
  options: {
    responsive: false,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: { enabled: false }
    },
    scales: {
      x: {
        display: false
      },
      y: {
        display: true,               // 显示纵轴
        grid: {
          color: 'rgba(0,0,0,0.05)', // 网格线颜色
        },
        ticks: {
          stepSize: Math.ceil(Math.max(...metric.value.last5) / 3), // 简单分三段
          padding: 4,
          font: { size: 8 },
          color: '#6b7280'
        }
      }
    }
  }
})
}

function handleOutside (e: MouseEvent) {
  if (show.value && wrapperEl.value && !wrapperEl.value.contains(e.target as Node)) {
    show.value = false
  }
}

watch(show, open => {
  if (open) {
    document.addEventListener('click', handleOutside)
  } else {
    document.removeEventListener('click', handleOutside)
  }
})

watch(show, async open => {
  if (open) {
    await loadMetric()
    nextTick(draw)
  } else if (chart) {
    chart.destroy()
    chart = undefined
  }
})
onBeforeUnmount(() => {          // 组件卸载时清理
  document.removeEventListener('click', handleOutside)
})
</script>

<template>
  <div ref="wrapperEl" class="relative inline-block">
    <button
      class="metric-btn flex items-center gap-1 text-xs font-semibold focus:outline-none"
      @click.stop="show = !show"
    >
      <Eye class="w-3 h-3" />
      {{ metric?.total?.toLocaleString() ?? '–' }}
    </button>

    <transition
      enter-active-class="animate-fade-slide-in"
      leave-active-class="animate-fade-slide-out"
    >
      <div v-if="show" class="metric-card">
        <!-- ① 画布高度改成 64px -->
        <canvas ref="canvasEl" width="180" height="64"></canvas>
        <!-- ② 文本下移 -->
        <p class="metric-label">Page Views · Past 5 Days</p>
      </div>
    </transition>
  </div>
</template>