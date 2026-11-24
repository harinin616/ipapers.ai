<template>
  <div class="ideation-app">
    <div class="bg-gradient" />

    <main class="container">
      <section class="main-left">
        <div class="card">
          <div class="card-header">
            <div class="header-icon">🧠</div>
            <div class="header-text">
              <h2>Research Ideation Studio</h2>
              <p>Search → Ideate → Critique → Revise</p>
            </div>
          </div>
          <div class="card-body">
            <div class="search-row">
              <div class="search-box">
                <span class="search-icon">🔎</span>
                <input
                  class="search-input"
                  type="text"
                  v-model="topic"
                  placeholder="Paste a paper abstract or type a topic…"
                />
                <button class="btn" @click="generate" :disabled="loading">
                  {{ loading ? 'Generating…' : 'Generate ideas' }}
                </button>
              </div>
              <p class="hint">
                Tip: you can paste an abstract and the system will align critique personas automatically (when wired to your backend).
              </p>

              <!-- Streaming panel: progress + logs -->
              <div v-if="loading || logs.length" class="stream-panel">
                <div class="progress">
                  <div class="progress-bar" :style="{ width: Math.min(100, progress) + '%' }"></div>
                </div>
                <ul class="log-list">
                  <li v-for="(m, i) in logs" :key="i">
                    <span class="log-stage">[{{ m.stage }}]</span>
                    <span class="log-msg">{{ m.message }}</span>
                  </li>
                </ul>
              </div>
            </div>

            <div class="grid-3">
              <div class="mini-card">
                <div>
                  <div class="mini-label">#Reviewers (N)</div>
                  <div class="mini-value">{{ reviewers }} people</div>
                  <div class="mini-note">3 is often a sweet spot</div>
                </div>
                <input type="range" min="1" max="6" v-model.number="reviewers" class="range" />
              </div>
              <div class="mini-card">
                <div>
                  <div class="mini-label">#Rounds (L)</div>
                  <div class="mini-value">{{ rounds }} rounds</div>
                  <div class="mini-note">2–3 rounds are usually best</div>
                </div>
                <input type="range" min="1" max="5" v-model.number="rounds" class="range" />
              </div>
              <div class="mini-card kpis">
                <div class="kpi-list">
                  <RingProgress :value="nonDupRef" label="Non-Dup %" />
                  <RingProgress :value="pAt10Ref" label="P@10 %" />
                </div>
                <div class="kpi-note">Estimates from backend; evaluator determines final scores.</div>
              </div>
            </div>
          </div>
        </div>

        <!-- Ideas grid -->
        <div class="ideas-grid">
          <div v-for="idea in ideas" :key="idea.id" class="idea-card">
            <div class="idea-header">
              <div class="idea-title">🚀 {{ idea.title }}</div>
              <div class="idea-tags">
                <span v-for="(t, i) in idea.tags" :key="i" class="tag">{{ t }}</span>
              </div>
            </div>
            <div class="idea-body">
              <p class="summary">{{ idea.summary }}</p>
              <div class="metrics">
                <RingProgress :value="idea.novelty" label="Novelty" />
                <RingProgress :value="idea.feasibility" label="Feasibility" />
                <RingProgress :value="idea.clarity" label="Clarity" />
                <div class="score">
                  <span class="score-icon">📊</span>
                  <span class="score-text">Score {{ idea.score }}</span>
                </div>
              </div>
              <div class="actions">
                <button class="btn" @click="addToShortlist(idea)">Add to shortlist</button>
                <button class="btn btn-outline" @click="togglePlan(idea as any)">
                  <span v-if="(idea as any)._expanded">Hide plan ▴</span>
                  <span v-else>View plan ▾</span>
                </button>
              </div>

              <!-- Expandable detailed plan (inline instead of exporting) -->
              <div v-if="(idea as any)._expanded" class="plan-panel">
                <div class="plan-toolbar">
                  <div class="plan-title">Detailed Plan</div>
                  <div class="plan-spacer" />
                  <button class="btn btn-outline small" @click="copyPlan(idea as any)">Copy</button>
                  <button class="btn btn-outline small" @click="collapseOthers(idea as any)">Collapse others</button>
                </div>

                <div v-if="(idea as any)._planLoading" class="plan-loading">Loading plan…</div>

                <template v-else>
                  <!-- Sections accordion if backend provides structured sections -->
                  <div v-if="(idea as any)._planSections?.length" class="accordion">
                    <div
                      v-for="(sec, si) in (idea as any)._planSections"
                      :key="si"
                      class="acc-item"
                    >
                      <button class="acc-header" @click="sec._open = !sec._open">
                        <span class="acc-title">{{ sec.title || `Section ${si + 1}` }}</span>
                        <span class="chev">{{ sec._open ? '▾' : '▸' }}</span>
                      </button>
                      <div v-show="sec._open" class="acc-body">
                        <p v-if="sec.content" class="md">{{ sec.content }}</p>
                        <ol v-if="sec.steps?.length" class="steps">
                          <li v-for="(s, sj) in sec.steps" :key="sj">{{ s }}</li>
                        </ol>
                      </div>
                    </div>
                  </div>

                  <!-- Fallback: render markdown (as preformatted text) -->
                  <pre v-else class="md-block">{{ (idea as any)._planMd }}</pre>
                </template>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Sidebar -->
      <aside class="main-right">
        <div class="card">
          <div class="card-header">
            <div class="header-text">
              <h3>Personas</h3>
              <p>Toggle critique perspectives</p>
            </div>
          </div>
          <div class="card-body">
            <div class="persona-list">
              <button
                v-for="p in personas"
                :key="p.key"
                @click="togglePersona(p.key)"
                class="persona-chip"
                :class="{ active: p.on }"
                :title="p.desc"
              >
                {{ p.name }}
              </button>
            </div>
            <p class="hint">Reviewer-side diversity tends to improve feasibility; proposer-side diversity can increase novelty.</p>
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <div class="header-text">
              <h3>Progress & Trend</h3>
              <p>Heuristic trend preview</p>
            </div>
          </div>
          <div class="card-body">
            <div class="chart">
              <svg viewBox="0 0 400 160" class="chart-svg">
                <defs>
                  <linearGradient id="gNovelty" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="rgba(0,0,0,0.35)" />
                    <stop offset="100%" stop-color="rgba(0,0,0,0.06)" />
                  </linearGradient>
                  <linearGradient id="gFeas" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="rgba(107, 33, 168, 0.35)" />
                    <stop offset="100%" stop-color="rgba(107, 33, 168, 0.06)" />
                  </linearGradient>
                </defs>
                <path :d="noveltyPath" fill="url(#gNovelty)" stroke="#111" stroke-width="2" />
                <path :d="feasPath" fill="url(#gFeas)" stroke="#6b21a8" stroke-width="2" />
              </svg>
            </div>
            <div class="trend-kpis">
              <div class="trend-card">
                <div class="trend-label">Non-Duplicate Ratio</div>
                <div class="trend-value">{{ nonDupRef }}%</div>
              </div>
              <div class="trend-card">
                <div class="trend-label">Precision@10</div>
                <div class="trend-value">{{ pAt10Ref }}%</div>
              </div>
            </div>
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <div class="header-text">
              <h3>Quick Start</h3>
              <p>How to use</p>
            </div>
          </div>
          <div class="card-body">
            <ol class="quick-list">
              <li>Type a topic or paste an abstract, then click <b>Generate ideas</b>.</li>
              <li>Tune <b>N</b> (reviewers) and <b>L</b> (rounds).</li>
              <li>Toggle personas to balance novelty vs feasibility.</li>
              <li>Add top ideas to shortlist and expand the plan inline.</li>
            </ol>
            <p class="hint">This is wired to your backend; streaming progress is shown above.</p>
          </div>
        </div>
      </aside>
    </main>

    <footer class="footer">
      <span>© {{ new Date().getFullYear() }} Ideation Studio</span>
      <span>·</span>
      <span>Vue 3 + TypeScript</span>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { computed, defineComponent, ref, h } from 'vue'
import api, { type Idea, type Persona } from '@/services/api'

interface ChartPoint { name: string; novelty: number; feasibility: number }

type UIIdea = Idea & {
  _expanded?: boolean
  _planLoading?: boolean
  _planMd?: string
  _planSections?: Array<{ title?: string; content?: string; steps?: string[]; _open?: boolean }>
}

const topic = ref<string>('')
const rounds = ref<number>(3)
const reviewers = ref<number>(3)

const personas = ref<Persona[]>([
  { key: 'phys', name: 'Physics-AI', on: true,  desc: 'Model rigor' } as any,
  { key: 'bio',  name: 'Biology-AI', on: false, desc: 'Data availability' } as any,
  { key: 'fin',  name: 'Finance-AI', on: false, desc: 'Real-world constraints' } as any,
  { key: 'psy',  name: 'Psychology-AI', on: true, desc: 'User studies' } as any,
  { key: 'mlops',name: 'MLOps', on: true, desc: 'Deployability' } as any,
] as unknown as Persona[])

const ideas = ref<UIIdea[]>([])
const nonDupRef = ref<number>(0)
const pAt10Ref = ref<number>(0)
const loading = ref<boolean>(false)

// streaming logs
const logs = ref<{ stage: string; message: string; ts: number }[]>([])
const progress = ref<number>(0)

function togglePersona (key: string) {
  personas.value = personas.value.map(p => (p.key === key ? { ...p, on: !p.on } as any : p))
}

function addToShortlist (idea: Idea) {
  alert(`Added to shortlist: ${idea.title}`)
}

async function togglePlan (idea: UIIdea) {
  idea._expanded = !idea._expanded
  if (idea._expanded && !idea._planMd && !idea._planSections) {
    idea._planLoading = true
    try {
      const res = await (api as any).expandProposal(idea.id)
      // Prefer structured sections if provided by backend
      if (res?.sections?.length) {
        idea._planSections = (res.sections as any[]).map(s => ({ ...s, _open: true }))
      }
      const md = res?.markdown ?? `# Proposal: ${idea.title}\n\n${idea.summary}\n`
      idea._planMd = md
    } catch (e) {
      console.error(e)
      alert('Failed to load plan. Please try again.')
      idea._expanded = false
    } finally {
      idea._planLoading = false
    }
  }
}

function collapseOthers (keep: UIIdea) {
  ideas.value.forEach(it => {
    if (it !== keep) it._expanded = false
  })
}

async function copyPlan (idea: UIIdea) {
  const text = idea._planSections?.length
    ? idea._planSections.map((s, i) => `## ${s.title || `Section ${i + 1}`}\n` + (s.content || '') + (s.steps?.length ? `\n\nSteps:\n- ` + s.steps.join('\n- ') : '')).join('\n\n')
    : (idea._planMd || '')
  try {
    await navigator.clipboard.writeText(text)
    alert('Plan copied to clipboard!')
  } catch (e) {
    console.error(e)
    alert('Copy failed. Select text and copy manually.')
  }
}

async function generate () {
  loading.value = true
  logs.value = []
  progress.value = 0
  ideas.value = []
  nonDupRef.value = 0
  pAt10Ref.value = 0

  const pushLog = (stage: string, message: string) => {
    logs.value.push({ stage, message, ts: Date.now() })
  }

  try {
    const resp: Response = await (api as any).streamIdeasGenerate({
      topic: topic.value,
      rounds: rounds.value,
      reviewers: reviewers.value,
      personas: personas.value,
    })

    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    if (!resp.body) throw new Error('No stream body')

    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    const upsertIdea = (incoming: any) => {
      const idx = ideas.value.findIndex(x => x.id === incoming.id)
      if (idx === -1) ideas.value.push(incoming)
      else ideas.value[idx] = { ...ideas.value[idx], ...incoming }
    }

    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      let idx
      while ((idx = buffer.indexOf('\n\n')) !== -1) {
        const chunk = buffer.slice(0, idx)
        buffer = buffer.slice(idx + 2)

        if (!chunk.trim().length || chunk.startsWith(':')) continue

        let eventType = 'message'
        let dataStr = ''
        for (const line of chunk.split('\n')) {
          if (line.startsWith('event:')) eventType = line.slice(6).trim()
          if (line.startsWith('data:')) dataStr += line.slice(5).trim()
        }
        if (!dataStr) continue

        let payload: any = {}
        try { payload = JSON.parse(dataStr) } catch { /* ignore */ }

        switch (eventType) {
          case 'phase':
            if (payload.message) pushLog(payload.stage || 'phase', payload.message)
            if (typeof payload.progress === 'number') {
              progress.value = Math.max(progress.value, Math.min(99, payload.progress))
            }
            break

          case 'seed':
            ideas.value = (payload.ideas || []) as any[]
            pushLog('seed', `Received ${ideas.value.length} seeds`)
            progress.value = Math.max(progress.value, 35)
            break

          case 'idea_update':
            upsertIdea(payload.idea)
            pushLog('refine', `Updated: ${payload.idea?.title ?? payload.idea?.id}`)
            progress.value = Math.max(progress.value, Math.min(90, progress.value + 5))
            break

          case 'kpis':
            if (payload.kpis) {
              if (typeof payload.kpis.nonDup === 'number') nonDupRef.value = payload.kpis.nonDup
              if (typeof payload.kpis.pAt10 === 'number') pAt10Ref.value = payload.kpis.pAt10
            }
            pushLog('kpis', 'KPIs updated')
            progress.value = Math.max(progress.value, 96)
            break

          case 'complete':
            if (payload.ideas) ideas.value = payload.ideas
            if (payload.kpis) {
              if (typeof payload.kpis.nonDup === 'number') nonDupRef.value = payload.kpis.nonDup
              if (typeof payload.kpis.pAt10 === 'number') pAt10Ref.value = payload.kpis.pAt10
            }
            pushLog('complete', 'Done')
            progress.value = 100
            break
        }
      }
    }
  } catch (e) {
    console.error(e)
    pushLog('error', 'Streaming failed, falling back to non-streaming')
    // fallback
    try {
      const res = await (api as any).generateIdeas({
        topic: topic.value,
        rounds: rounds.value,
        reviewers: reviewers.value,
        personas: personas.value,
      })
      ideas.value = res.ideas || []
      if (res.kpis) {
        if (typeof res.kpis.nonDup === 'number') nonDupRef.value = res.kpis.nonDup
        if (typeof res.kpis.pAt10 === 'number') pAt10Ref.value = res.kpis.pAt10
      }
      progress.value = 100
    } catch (err2) {
      console.error(err2)
      alert('Failed to generate ideas. Please try again.')
    }
  } finally {
    loading.value = false
  }
}

// init a trend chart (fake visual)
const chartData = ref<ChartPoint[]>(
  Array.from({ length: 12 }, (_, i) => ({
    name: `R${i + 1}`,
    novelty: 50 + Math.random() * 40,
    feasibility: 48 + Math.random() * 35,
  }))
)

function buildAreaPath (key: 'novelty' | 'feasibility') {
  const w = 400, h = 160
  const pad = 6
  const baseY = h - pad
  const points = chartData.value
  const step = (w - pad * 2) / (points.length - 1)
  const vals = points.map((p, i) => {
    const x = pad + i * step
    const y = baseY - ((Math.max(40, Math.min(100, (p as any)[key])) - 40) / 60) * (h - pad * 2)
    return [x, y]
  })
  const d = ['M', vals[0][0], vals[0][1]]
    .concat(vals.slice(1).flatMap(([x, y]) => ['L', x, y]))
    .join(' ')
  return `${d} L ${pad + (points.length - 1) * step} ${baseY} L ${pad} ${baseY} Z`
}

const noveltyPath = computed(() => buildAreaPath('novelty'))
const feasPath = computed(() => buildAreaPath('feasibility'))

// Local subcomponent: no JSX
const RingProgress = defineComponent({
  name: 'RingProgress',
  props: {
    value: { type: Number, required: true },
    label: { type: String, default: '' },
  },
  setup (props) {
    const angle = computed(() =>
      Math.round((Math.max(0, Math.min(100, props.value)) / 100) * 360)
    )
    return () =>
      h('div', { class: 'ring' }, [
        h(
          'div',
          {
            class: 'ring-outer',
            style: {
              background: `conic-gradient(#111 ${angle.value}deg, rgba(0,0,0,.06) ${angle.value}deg 360deg)`,
            },
          },
          [h('div', { class: 'ring-inner' }, String(props.value))]
        ),
        h('div', { class: 'ring-label' }, props.label || ''),
      ])
  },
})
</script>

<style scoped>
.ideation-app { position: relative; min-height: 100vh; color: var(--text); }
.bg-gradient { position: fixed; inset: 0; z-index: -1; background: linear-gradient(180deg, #c7d2fe 0%, #f5f3ff 50%, #ffe4e6 100%); }

.container { max-width: 1200px; margin: 0 auto; padding: 24px 16px; display: grid; gap: 20px; grid-template-columns: 1fr; }
@media (min-width: 1024px) { .container { grid-template-columns: 2fr 1fr; } }

.card { border: 1px solid rgba(0,0,0,0.05); border-radius: 16px; background: rgba(255,255,255,0.7); box-shadow: 0 10px 30px rgba(0,0,0,0.06); overflow: hidden; }
.card-header { display: flex; align-items: center; gap: 12px; padding: 16px; border-bottom: 1px solid rgba(0,0,0,0.06); }
.header-icon { width: 40px; height: 40px; display: grid; place-items: center; border-radius: 12px; background: #111; color: #fff; font-size: 18px; }
.header-text h2, .header-text h3 { margin: 0; font-size: 18px; font-weight: 800; }
.header-text p { margin: 2px 0 0; font-size: 12px; color: var(--text-2); }
.card-body { padding: 16px; }

.btn { border: 1px solid #111; background: #111; color: #fff; padding: 10px 14px; border-radius: 14px; font-weight: 600; cursor: pointer; transition: transform .15s, box-shadow .15s, background .15s; }
.btn:hover { transform: translateY(-1px); box-shadow: 0 8px 22px rgba(0,0,0,0.12); }
.btn-outline { background: transparent; color: #111; border-color: rgba(0,0,0,0.2); }
.btn-outline:hover { background: #111; color: #fff; }
.btn.small { padding: 6px 10px; border-radius: 10px; font-size: 12px; }

.search-row { margin-bottom: 12px; }
.search-box { display: flex; align-items: center; gap: 10px; border: 1px solid rgba(0,0,0,0.1); background: var(--surface); padding: 8px; border-radius: 16px; }
.search-icon { margin-left: 6px; }
.search-input { flex: 1; background: transparent; border: 0; outline: none; font-size: 15px; }
.hint { margin: 6px 4px; font-size: 12px; color: var(--text-2); }

.grid-3 { display: grid; grid-template-columns: 1fr; gap: 10px; }
@media (min-width: 640px) { .grid-3 { grid-template-columns: repeat(3, 1fr); } }
.mini-card { display: flex; align-items: center; justify-content: space-between; gap: 12px; border: 1px solid rgba(0,0,0,0.05); background: rgba(255,255,255,0.7); border-radius: 14px; padding: 12px; }
.mini-label { font-size: 12px; color: var(--text-2); }
.mini-value { font-size: 16px; font-weight: 700; }
.mini-note { font-size: 11px; color: var(--text-2); }
.range { width: 150px; }
.kpis { align-items: center; }
.kpi-list { display: flex; align-items: center; gap: 16px; }
.kpi-note { font-size: 11px; color: var(--text-2); text-align: right; }

.ring { display: flex; align-items: center; gap: 10px; }
.ring-outer { width: 48px; height: 48px; border-radius: 999px; display: grid; place-items: center; }
.ring-inner { width: 36px; height: 36px; border-radius: 999px; background: var(--surface); display: grid; place-items: center; font-size: 12px; font-weight: 800; }
.ring-label { font-size: 12px; color: var(--text-2); }

.ideas-grid { margin-top: 16px; display: grid; grid-template-columns: 1fr; gap: 12px; }
@media (min-width: 768px) { .ideas-grid { grid-template-columns: repeat(2, 1fr); } }
.idea-card { border: 1px solid rgba(0,0,0,0.05); border-radius: 16px; background: rgba(255,255,255,0.75); box-shadow: 0 10px 30px rgba(0,0,0,0.06); transition: transform .15s, box-shadow .15s; }
.idea-card:hover { transform: translateY(-1px); box-shadow: 0 16px 36px rgba(0,0,0,0.12); }
.idea-header { display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid rgba(0,0,0,0.06); padding: 12px 16px; }
.idea-title { font-weight: 800; }
.idea-tags { display: flex; align-items: center; gap: 6px; }
.tag { border: 1px solid rgba(0,0,0,0.12); padding: 4px 8px; border-radius: 999px; font-size: 12px; background: var(--surface); }
.idea-body { padding: 12px 16px; }
.summary { font-size: 14px; color: #334155; margin-bottom: 10px; }
.metrics { display: flex; align-items: center; gap: 16px; }
.score { margin-left: auto; display: flex; align-items: center; gap: 6px; font-weight: 700; }
.score-icon { font-size: 16px; }
.actions { margin-top: 12px; display: flex; gap: 8px; }

/* Inline plan panel */
.plan-panel { margin-top: 12px; border: 1px solid rgba(0,0,0,0.08); background: var(--surface); border-radius: 12px; padding: 12px; }
.plan-toolbar { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.plan-title { font-weight: 800; font-size: 14px; }
.plan-spacer { flex: 1; }
.plan-loading { font-size: 13px; color: var(--text-2); padding: 6px 0; }

/* Accordion */
.accordion { display: grid; gap: 8px; }
.acc-item { border: 1px solid rgba(0,0,0,0.06); border-radius: 10px; overflow: hidden; background: var(--surface); }
.acc-header { width: 100%; text-align: left; background: transparent; border: 0; padding: 10px 12px; display: flex; align-items: center; justify-content: space-between; cursor: pointer; font-weight: 700; }
.acc-body { padding: 10px 12px; border-top: 1px solid rgba(0,0,0,0.06); }
.acc-title { font-size: 13px; }
.chev { font-size: 14px; }
.steps { margin: 6px 0 0 18px; }

/* Markdown fallback */
.md-block { white-space: pre-wrap; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; background: rgba(248,250,252,.7); border-radius: 8px; padding: 10px; font-size: 12px; color: var(--text); }
.md { white-space: pre-wrap; }

.persona-list { display: flex; flex-wrap: wrap; gap: 8px; }
.persona-chip { border: 1px solid rgba(0,0,0,0.12); background: var(--surface); padding: 8px 12px; border-radius: 999px; font-size: 13px; cursor: pointer; transition: background .15s, color .15s, border .15s; }
.persona-chip.active { background: #111; color: #fff; border-color: #111; }

.chart { height: 160px; border-radius: 12px; overflow: hidden; border: 1px solid rgba(0,0,0,0.06); background: rgba(255,255,255,0.7); }
.chart-svg { width: 100%; height: 100%; display: block; }
.trend-kpis { margin-top: 10px; display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.trend-card { border: 1px solid rgba(0,0,0,0.06); background: rgba(255,255,255,0.7); border-radius: 12px; padding: 10px; }
.trend-label { font-size: 12px; color: var(--text-2); }
.trend-value { font-size: 18px; font-weight: 800; }

.quick-list { margin-left: 16px; color: #334155; }
.footer { display: flex; gap: 8px; align-items: center; justify-content: center; padding: 16px; color: var(--text-2); font-size: 12px; }

/* Streaming UI */
.stream-panel { margin-top: 10px; border: 1px dashed rgba(0,0,0,0.15); border-radius: 12px; padding: 10px; background: rgba(255,255,255,0.6); }
.progress { height: 8px; background: rgba(0,0,0,0.06); border-radius: 999px; overflow: hidden; }
.progress-bar { height: 8px; width: 0%; background: #111; transition: width .2s ease; }
.log-list { margin-top: 8px; max-height: 140px; overflow: auto; font-size: 12px; color: #334155; display: grid; gap: 4px; }
.log-stage { font-weight: 700; margin-right: 6px; }
.log-msg { opacity: .9; }
</style>
