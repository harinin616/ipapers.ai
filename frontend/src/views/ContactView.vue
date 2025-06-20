<template>
  <div class="contact-page">
    <h1>Contact Us</h1>

    <!-- ① 用 @submit.prevent -->
    <form id="contactForm" @submit.prevent="onSubmit">
      <div class="form-group">
        <label for="question">Feedback *</label>
        <textarea
          id="question"
          v-model="question"          
          required
          maxlength="500"
          placeholder=""
        ></textarea>
      </div>

      <div class="form-group">
        <label for="email">Your email address (optional)</label>
        <input
          type="email"
          id="email"
          v-model="email"           
          maxlength="100"
          placeholder=""
        />
      </div>

      <div class="form-actions">
        <button type="reset" class="btn-cancel">Reset</button>
        <!-- ③ 发送中禁用 -->
        <button type="submit" class="btn-submit" :disabled="sending">
          {{ sending ? 'Submitting…' : 'Submit' }}
        </button>
      </div>
    </form>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import api from '@/services/api'

const question = ref('')
const email = ref('')
const sending = ref(false)

const onSubmit = async () => {
  if (!question.value.trim()) {
    alert('Please enter your feedback.')
    return
  }
  sending.value = true
  try {
    await api.submitFeedback({
      question: question.value,
      email: email.value.trim() || undefined,
    })
    alert('Thank you! Your feedback has been submitted.')
    question.value = ''
    email.value = ''
  } catch (err) {
    console.error(err)
    alert('Submission failed. Please try again.')
  } finally {
    sending.value = false
  }
}
</script>


<style scoped>
.contact-page {
  max-width: 1000px;
  width: 90%;
  margin: 2rem auto;
  padding: 2rem 1.5rem;
  background-color: #fff;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
  border-radius: 8px;
  display: flex;
  flex-direction: column;
}

.contact-page h1 {
  margin-bottom: 1.5rem;
  font-size: 1.6rem;
  font-weight: 600;
  text-align: center;
  color: #3f51b5;
}

.form-group {
  margin-bottom: 1.25rem;
  display: flex;
  flex-direction: column;
}

.form-group label {
  font-weight: 500;
  margin-bottom: 0.5rem;
  color: #333;
}

.form-group textarea,
.form-group input {
  width: 90%;
  padding: 0.6rem 0.75rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 1rem;
  transition: border-color 0.2s;
}

.form-group textarea:focus,
.form-group input:focus {
  outline: none;
  border-color: #3f51b5;
}

.form-actions {
  display: flex;
  justify-content: center;
  gap: 0.75rem;
  margin-top: 1rem;
}

.btn-submit,
.btn-cancel {
  display: inline-block;
  border: 1px solid #3f51b5;
  background: transparent;
  color: #3f51b5;
  padding: 0.5rem 1rem;
  border-radius: 9999px;
  font-size: 0.95rem;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.2s, color 0.2s;
  text-decoration: none;
}

.btn-submit:hover,
.btn-cancel:hover {
  background-color: #3f51b5;
  color: #fff;
}

.btn-submit {
  background-color: #3f51b5;
  color: #fff;
}

.btn-submit:hover {
  background-color: #2c3e9e;
}
</style>