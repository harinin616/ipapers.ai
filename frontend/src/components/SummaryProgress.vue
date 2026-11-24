<template>
  <div v-if="isLoading" class="summary-progress">
    <div class="progress-header">
      <div class="progress-icon">🤖</div>
      <div class="progress-text">
        <h4>Generating AI Summary...</h4>
        <p>Analyzing papers to create summary</p>
      </div>
    </div>
    
    <div class="progress-bar-container">
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: progressWidth + '%' }"></div>
      </div>
      <div class="progress-percentage">{{ Math.round(progressWidth) }}%</div>
    </div>
    
    <div class="progress-steps">
      <div class="step" :class="{ active: currentStep >= 1, completed: currentStep > 1 }">
        <span class="step-number">1</span>
        <span class="step-text">Processing papers</span>
      </div>
      <div class="step" :class="{ active: currentStep >= 2, completed: currentStep > 2 }">
        <span class="step-number">2</span>
        <span class="step-text">Analyzing content</span>
      </div>
      <div class="step" :class="{ active: currentStep >= 3, completed: currentStep > 3 }">
        <span class="step-number">3</span>
        <span class="step-text">Generating insights</span>
      </div>
    </div>
  </div>
  
  <div v-else-if="error" class="summary-error">
    <div class="error-icon">⚠️</div>
    <div class="error-content">
      <h4>Failed to Generate Summary</h4>
      <p>{{ error }}</p>
      <button @click="$emit('retry')" class="retry-btn">Try Again</button>
    </div>
  </div>
</template>

<script>
export default {
  name: 'SummaryProgress',
  props: {
    isLoading: {
      type: Boolean,
      default: false
    },
    paperCount: {
      type: Number,
      default: 0
    },
    error: {
      type: String,
      default: null
    }
  },
  emits: ['retry'],
  data() {
    return {
      progressWidth: 0,
      currentStep: 1,
      animationId: null
    }
  },
  watch: {
    isLoading: {
      immediate: true,
      handler(newValue) {
        if (newValue) {
          this.startProgress()
        } else {
          this.stopProgress()
        }
      }
    }
  },
  beforeUnmount() {
    this.stopProgress()
  },
  methods: {
    startProgress() {
      this.progressWidth = 0
      this.currentStep = 1
      this.animateProgress()
    },
    
    stopProgress() {
      if (this.animationId) {
        cancelAnimationFrame(this.animationId)
        this.animationId = null
      }
    },
    
    animateProgress() {
      const duration = 15000 // 15 seconds total
      const stepDuration = duration / 3
      const startTime = Date.now()
      
      const animate = () => {
        const elapsed = Date.now() - startTime
        const progress = Math.min(elapsed / duration, 1)
        
        // Update progress bar
        this.progressWidth = progress * 100
        
        // Update current step
        if (elapsed < stepDuration) {
          this.currentStep = 1
        } else if (elapsed < stepDuration * 2) {
          this.currentStep = 2
        } else {
          this.currentStep = 3
        }
        
        if (progress < 1 && this.isLoading) {
          this.animationId = requestAnimationFrame(animate)
        }
      }
      
      animate()
    }
  }
}
</script>

<style scoped>
.summary-progress, .summary-error { margin-bottom: var(--sp-4); padding: var(--sp-4) var(--sp-5); background: var(--surface); border: 1px solid var(--border); border-radius: var(--r-lg); box-shadow: var(--shadow-1); }
.summary-error { border-left: 3px solid var(--danger); display: flex; gap: var(--sp-3); }
.progress-header { display: flex; align-items: center; gap: var(--sp-3); }
.progress-icon, .error-icon { font-size: 1.4rem; }
.progress-text h4, .error-content h4 { margin: 0; font-size: var(--fs-md); }
.progress-text p, .error-content p { margin: 2px 0 0; font-size: var(--fs-sm); color: var(--text-2); }
.progress-bar-container { display: flex; align-items: center; gap: var(--sp-3); margin: var(--sp-4) 0 var(--sp-3); }
.progress-bar { flex: 1; height: 6px; background: var(--surface-2); border-radius: var(--r-pill); overflow: hidden; }
.progress-fill { height: 100%; background: var(--accent); border-radius: var(--r-pill); transition: width .4s var(--ease); }
.progress-percentage { min-width: 40px; text-align: right; font-size: var(--fs-xs); color: var(--text-3); }
.progress-steps { display: flex; flex-wrap: wrap; gap: var(--sp-4); }
.step { display: inline-flex; align-items: center; gap: var(--sp-2); font-size: var(--fs-xs); color: var(--text-3); }
.step-number { display: inline-grid; place-items: center; width: 20px; height: 20px; border-radius: 50%; background: var(--surface-2); font-weight: 600; }
.step.active { color: var(--text); }
.step.active .step-number { background: var(--accent); color: var(--accent-ink); }
.step.completed .step-number { background: var(--success); color: #fff; }
.retry-btn { margin-top: var(--sp-2); height: 32px; padding: 0 var(--sp-3); font: 500 var(--fs-xs)/1 var(--font-sans); color: var(--accent-ink); background: var(--accent); border: none; border-radius: var(--r-sm); cursor: pointer; }
</style>
