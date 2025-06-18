<!-- src/views/ProfileView.vue -->
<template>
  <section class="profile-page">
    <div class="profile-card">
      <!-- 头像与姓名 -->
      <div class="header">
        <img :src="user?.picture || fallbackAvatar" class="avatar" />
        <div class="basic-info">
          <h2 class="name">{{ user?.name || 'Guest User' }}</h2>
          <p class="email">{{ user?.email || 'example@mail.com' }}</p>
        </div>
      </div>

      <!-- 统计信息 -->
      <div class="stats">
        <div class="stat">
          <span class="value">{{ metric.total }}</span>
          <span class="label">Total Views</span>
        </div>
        <div class="stat">
          <span class="value">{{ metric.today }}</span>
          <span class="label">Today</span>
        </div>
        <div class="stat">
          <span class="value">{{ files }}</span>
          <span class="label">Files</span>
        </div>
      </div>

      <!-- 操作按钮 -->
      <div class="actions">
        <button class="btn" @click="gotoFiles">My Files</button>
        <button class="btn outline" @click="logout">Logout</button>
      </div>
    </div>
  </section>
</template>

<script>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/services/api'

export default {
  name: 'ProfileView',
  setup () {
    const router = useRouter()
    const user   = ref(null)
    const metric = ref({ total: '–', today: '–' })
    const files  = ref('–')
    const fallbackAvatar =
      'https://avatars.githubusercontent.com/u/9919?s=200&v=4'

    function loadUser () {
      try { user.value = JSON.parse(localStorage.getItem('user')) } catch {}
    }

    async function fetchStats () {
      try {
        const m = await (await fetch('/api/metrics/site-metric')).json()
        metric.value.total = m.total
        metric.value.today = m.last5.at(-1) ?? 0
      } catch {}
      try {
        const list = await api.get_user_files()
        files.value = list.length
      } catch {}
    }

    function gotoFiles () {
      router.push('/')
    }

    function logout () {
      localStorage.removeItem('user')
      localStorage.removeItem('X-User-ID')
      window.location.href = '/'
    }

    onMounted(() => {
      loadUser()
      fetchStats()
    })

    return { user, metric, files, fallbackAvatar, gotoFiles, logout }
  }
}
</script>

<style scoped>
/* 整页容器 —— 让卡片水平垂直都居中 */
.profile-page {
  min-height: calc(100vh - 4rem);   /* 去掉 header 高度 */
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 2rem 1rem;
  background: #f8f9fa;
}

/* 卡片本体 */
.profile-card {
  max-width: 480px;
  width: 100%;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.08);
  padding: 2rem 1.75rem 2.5rem;
  display: flex;
  flex-direction: column;
  gap: 1.75rem;
}

/* 头像 + 姓名 */
.header {
  display: flex;
  gap: 1.25rem;
  align-items: center;
}
.avatar {
  width: 96px;
  height: 96px;
  border-radius: 50%;
  object-fit: cover;
  border: 4px solid #fff;
  background: #ddd;
  box-shadow: 0 2px 6px rgba(0,0,0,0.12);
}
.basic-info .name   { font-size: 1.5rem; font-weight: 600; color: #333 }
.basic-info .email  { margin-top: .25rem; color: #555; font-size: .9rem; }

/* 统计网格 */
.stats {
  display: grid;
  grid-template-columns: repeat(3,1fr);
  text-align: center;
  gap: .5rem;
  border-top: 1px solid #eee;
  padding-top: 1.5rem;
}
.stat .value  { font-size: 1.6rem; font-weight: 600; color: #333 }
.stat .label  {
  margin-top: .15rem;
  font-size: .72rem;
  text-transform: uppercase;
  color: #777;
  letter-spacing: .05em;
}

/* 按钮区 */
.actions {
  margin-top: .5rem;
  display: flex;
  gap: .75rem;
  justify-content: center;
}
.btn {
  min-width: 120px;
  padding: .55rem 0;
  background: #3f51b5;
  color: #fff;
  font-weight: 500;
  border: 1px solid #3f51b5;
  border-radius: 9999px;
  cursor: pointer;
  transition: .2s;
}
.btn:hover     { background: #32409b }
.btn.outline   {
  background: transparent;
  color: #3f51b5;
}
.btn.outline:hover {
  background: #3f51b5;
  color: #fff;
}
</style>
