<template>
  <div class="subscription-page">
    <div class="subscription-container">
      <!-- Header with icon -->
      <div class="header-section">
        <div class="icon-section">
          <svg class="mail-icon" viewBox="0 0 24 24" fill="none">
            <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" stroke="currentColor" stroke-width="2"/>
            <polyline points="22,6 12,13 2,6" stroke="currentColor" stroke-width="2"/>
          </svg>
          <svg class="calendar-icon" viewBox="0 0 24 24" fill="none">
            <rect x="3" y="4" width="18" height="18" rx="2" ry="2" stroke="currentColor" stroke-width="2"/>
            <line x1="16" y1="2" x2="16" y2="6" stroke="currentColor" stroke-width="2"/>
            <line x1="8" y1="2" x2="8" y2="6" stroke="currentColor" stroke-width="2"/>
            <line x1="3" y1="10" x2="21" y2="10" stroke="currentColor" stroke-width="2"/>
          </svg>
          <svg class="plus-icon" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/>
            <line x1="12" y1="8" x2="12" y2="16" stroke="currentColor" stroke-width="2"/>
            <line x1="8" y1="12" x2="16" y2="12" stroke="currentColor" stroke-width="2"/>
          </svg>
        </div>
        
        <h1>Subscribe to receive Daily Feed emails.</h1>
        
        <div class="description">
          <p>Emails from iPapers is the best way to find out about the latest research trends, curated papers, and other information that may be of interest to you.</p>
          
          <p>Enter your email address to receive daily feed email from iPapers. You can unsubscribe at any time.</p>
          
          <p>Please refer to <router-link to="/privacy-policy" class="link">Privacy Policy</router-link> or <router-link to="/contact" class="link">contact us</router-link> for more details.</p>
        </div>
      </div>

      <!-- Subscription Form -->
      <div class="form-section">
        <div class="form-container">
          <label for="email" class="email-label">
            Email address <span class="required">*</span>
          </label>
          
          <div class="email-input-container">
            <span class="email-prefix">@</span>
            <input 
              id="email"
              v-model="email"
              type="email"
              placeholder="Enter your email address"
              class="email-input"
              :disabled="isLoading"
            />
          </div>
          
          <div class="button-group">
            <button 
              @click="handleSubscribe"
              :disabled="!isValidEmail || isLoading"
              class="action-btn subscribe-btn"
            >
              <span v-if="isLoading && actionType === 'subscribe'" class="loading-spinner"></span>
              <template v-else>Subscribe to Daily Feed</template>
            </button>
            
            <button 
              @click="handleUnsubscribe"
              :disabled="!isValidEmail || isLoading"
              class="action-btn unsubscribe-btn"
            >
              <span v-if="isLoading && actionType === 'unsubscribe'" class="loading-spinner"></span>
              <template v-else>Unsubscribe from Daily Feed</template>
            </button>
          </div>
          
          <!-- Status Messages -->
          <div v-if="statusMessage" :class="['status-message', statusType]">
            {{ statusMessage }}
          </div>
        </div>
      </div>
      
      <!-- Back to Daily Feed -->
      <div class="back-section">
        <router-link to="/daily-feed" class="back-link">
          ← Back to Daily Feed
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

// Reactive data
const email = ref('')
const isLoading = ref(false)
const actionType = ref<'subscribe' | 'unsubscribe' | null>(null)
const statusMessage = ref('')
const statusType = ref<'success' | 'error'>('success')

// Computed properties
const isValidEmail = computed(() => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return emailRegex.test(email.value)
})

// Check subscription status function
const checkSubscriptionStatus = async (emailToCheck: string) => {
  if (!emailToCheck) return false
  
  try {
    const response = await fetch(`/api/user/subscription-status?email=${encodeURIComponent(emailToCheck)}`)
    if (response.ok) {
      const data = await response.json()
      return data.subscribed
    }
  } catch (err) {
    console.error('Error checking subscription status:', err)
  }
  return false
}

// Subscription management functions
const updateSubscriptionStatus = async (subscribed: boolean) => {
  if (!isValidEmail.value) {
    statusMessage.value = 'Please enter a valid email address.'
    statusType.value = 'error'
    return false
  }
  
  isLoading.value = true
  actionType.value = subscribed ? 'subscribe' : 'unsubscribe'
  statusMessage.value = ''
  
  try {
    const response = await fetch('/api/user/subscription', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ 
        email: email.value.trim().toLowerCase(),
        subscribed 
      })
    })
    
    if (response.ok) {
      const data = await response.json()
      statusMessage.value = subscribed 
        ? 'You have successfully subscribed to the daily feed! You will receive email updates.' 
        : 'You have successfully unsubscribed from the daily feed. You will no longer receive email updates.'
      statusType.value = 'success'
      return true
    } else {
      const errorData = await response.json()
      statusMessage.value = `Failed to update subscription: ${errorData.detail || 'Unknown error'}`
      statusType.value = 'error'
      return false
    }
  } catch (err) {
    console.error('Error updating subscription:', err)
    statusMessage.value = 'Failed to update subscription. Please try again.'
    statusType.value = 'error'
    return false
  } finally {
    isLoading.value = false
    actionType.value = null
  }
}

const handleSubscribe = async () => {
  if (!isValidEmail.value) return
  await updateSubscriptionStatus(true)
}

const handleUnsubscribe = async () => {
  if (!isValidEmail.value) return
  await updateSubscriptionStatus(false)
}

// Handle URL parameters for unsubscribe links
onMounted(() => {
  // Check if there's an email and action in URL parameters
  const urlParams = new URLSearchParams(window.location.search)
  const emailParam = urlParams.get('email')
  const actionParam = urlParams.get('action')
  
  if (emailParam) {
    email.value = emailParam
    
    // If it's an unsubscribe action, automatically perform it
    if (actionParam === 'unsubscribe') {
      handleUnsubscribe()
    }
  }
})
</script>

<style scoped>
.subscription-page {
  min-height: 100vh;
  background: linear-gradient(135deg, var(--surface-2) 0%, #c3cfe2 100%);
  padding: 2rem 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
}

.subscription-container {
  max-width: 800px;
  width: 100%;
  background: var(--surface);
  border-radius: 16px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.header-section {
  padding: 3rem 2rem 2rem;
  text-align: center;
  background: var(--surface-2);
  border-bottom: 1px solid var(--border);
}

.icon-section {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 1rem;
  margin-bottom: 2rem;
}

.mail-icon, .calendar-icon, .plus-icon {
  width: 48px;
  height: 48px;
  color: var(--accent);
}

.subscription-container h1 {
  font-size: 2.2rem;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 1.5rem;
  line-height: 1.3;
}

.description {
  text-align: left;
  max-width: 600px;
  margin: 0 auto;
}

.description p {
  font-size: 1.05rem;
  color: #5a6c7d;
  line-height: 1.6;
  margin-bottom: 1rem;
}

.link {
  color: var(--accent);
  text-decoration: none;
  border-bottom: 1px solid var(--accent);
  transition: all 0.2s ease;
}

.link:hover {
  color: #2c3e9e;
  border-bottom-color: #2c3e9e;
  background: rgba(63, 81, 181, 0.1);
}

.form-section {
  padding: 3rem 2rem;
}

.form-container {
  max-width: 500px;
  margin: 0 auto;
}

.email-label {
  display: block;
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 0.75rem;
}

.required {
  color: #e74c3c;
}

.email-input-container {
  position: relative;
  margin-bottom: 2rem;
}

.email-prefix {
  position: absolute;
  left: 1rem;
  top: 50%;
  transform: translateY(-50%);
  color: #6c757d;
  font-size: 1.1rem;
  z-index: 1;
}

.email-input {
  width: 100%;
  padding: 1rem 1rem 1rem 3rem;
  font-size: 1.1rem;
  border: 2px solid var(--border);
  border-radius: 8px;
  transition: all 0.3s ease;
  background: var(--surface);
}

.email-input:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(63, 81, 181, 0.1);
}

.email-input:disabled {
  background: var(--surface-2);
  color: #6c757d;
  cursor: not-allowed;
}

.button-group {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.action-btn {
  width: 100%;
  padding: 1rem 2rem;
  font-size: 1.05rem;
  font-weight: 600;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  position: relative;
}

.subscribe-btn {
  background: var(--accent);
  color: white;
}

.subscribe-btn:hover:not(:disabled) {
  background: #2c3e9e;
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(63, 81, 181, 0.3);
}

.unsubscribe-btn {
  background: #6c757d;
  color: white;
}

.unsubscribe-btn:hover:not(:disabled) {
  background: #545b62;
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(108, 117, 125, 0.3);
}

.action-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none !important;
  box-shadow: none !important;
}

.loading-spinner {
  width: 20px;
  height: 20px;
  border: 2px solid transparent;
  border-top: 2px solid currentColor;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.status-message {
  padding: 1rem;
  border-radius: 8px;
  font-weight: 500;
  text-align: center;
}

.status-message.success {
  background: #d4edda;
  color: #155724;
  border: 1px solid #c3e6cb;
}

.status-message.error {
  background: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}

.back-section {
  padding: 1.5rem 2rem;
  background: var(--surface-2);
  border-top: 1px solid var(--border);
  text-align: center;
}

.back-link {
  color: var(--accent);
  text-decoration: none;
  font-weight: 500;
  transition: color 0.2s ease;
}

.back-link:hover {
  color: #2c3e9e;
}

@media (max-width: 768px) {
  .subscription-page {
    padding: 1rem 0.5rem;
  }
  
  .subscription-container h1 {
    font-size: 1.8rem;
  }
  
  .header-section {
    padding: 2rem 1.5rem 1.5rem;
  }
  
  .form-section {
    padding: 2rem 1.5rem;
  }
  
  .description p {
    font-size: 1rem;
  }
  
  .icon-section {
    gap: 0.75rem;
  }
  
  .mail-icon, .calendar-icon, .plus-icon {
    width: 36px;
    height: 36px;
  }
}

@media (max-width: 480px) {
  .button-group {
    gap: 0.75rem;
  }
  
  .action-btn {
    padding: 0.875rem 1.5rem;
    font-size: 1rem;
  }
}
</style> 