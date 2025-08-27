<template>
  <div v-if="isLoading" class="summary-progress">
    <div class="progress-header">
      <div class="progress-icon">🤖</div>
      <div class="progress-text">
        <h4>Generating AI Summary...</h4>
        <p>Analyzing {{ paperCount }} papers to create insights</p>
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
.summary-progress {
  background: white;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.progress-header {
  display: flex;
  align-items: center;
  margin-bottom: 1.5rem;
  gap: 1rem;
}

.progress-icon {
  font-size: 2rem;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.1); }
}

.progress-text h4 {
  margin: 0 0 0.25rem 0;
  color: #333;
  font-size: 1.1rem;
}

.progress-text p {
  margin: 0;
  color: #666;
  font-size: 0.9rem;
}

.progress-bar-container {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.progress-bar {
  flex: 1;
  height: 8px;
  background: #f0f0f0;
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #3f51b5, #5c6bc0);
  border-radius: 4px;
  transition: width 0.3s ease;
}

.progress-percentage {
  font-size: 0.85rem;
  color: #666;
  min-width: 40px;
  text-align: right;
}

.progress-steps {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
}

.step {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
  opacity: 0.5;
  transition: opacity 0.3s ease;
}

.step.active {
  opacity: 1;
}

.step.completed {
  opacity: 0.7;
}

.step-number {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #f0f0f0;
  color: #666;
  font-size: 0.8rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
  transition: all 0.3s ease;
}

.step.active .step-number {
  background: #3f51b5;
  color: white;
}

.step.completed .step-number {
  background: #4caf50;
  color: white;
}

.step-text {
  font-size: 0.8rem;
  color: #666;
  text-align: center;
  line-height: 1.2;
}

.summary-error {
  background: #fff5f5;
  border: 1px solid #feb2b2;
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
  display: flex;
  align-items: center;
  gap: 1rem;
}

.error-icon {
  font-size: 1.5rem;
}

.error-content {
  flex: 1;
}

.error-content h4 {
  margin: 0 0 0.5rem 0;
  color: #c53030;
  font-size: 1rem;
}

.error-content p {
  margin: 0 0 1rem 0;
  color: #742a2a;
  font-size: 0.9rem;
}

.retry-btn {
  background: #3f51b5;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.85rem;
  transition: background-color 0.2s;
}

.retry-btn:hover {
  background: #303f9f;
}

@media (max-width: 768px) {
  .progress-steps {
    gap: 0.5rem;
  }
  
  .step-text {
    font-size: 0.75rem;
  }
  
  .progress-header {
    gap: 0.75rem;
  }
  
  .summary-progress {
    padding: 1rem;
  }
}
</style>
