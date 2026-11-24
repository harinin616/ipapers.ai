<template>
  <main class="max-w-3xl mx-auto py-10 px-4 prose prose-sm sm:prose lg:prose-lg">
    <h1>Terms of Use</h1>

    <p class="text-sm text-gray-500">Effective Date: July&nbsp;4,&nbsp;2025 &nbsp;|&nbsp; Last Updated: July&nbsp;4,&nbsp;2025</p>

    <p>
      Welcome to <strong>iPapers</strong> ("we", "our", or "us"). These Terms of Use ("Terms") govern your
      access to and use of our website and services (collectively, the "Service"). By accessing or using the
      Service, you agree to be bound by these Terms. If you do not agree, please do not use the Service.
    </p>

    <h2>1.&nbsp;Eligibility</h2>
    <p>You must be at least 13&nbsp;years old—or the minimum age in your jurisdiction—to use the Service.</p>

    <h2>2.&nbsp;User Responsibilities</h2>
    <ul>
      <li>Use the Service only for lawful purposes.</li>
      <li>Do not disrupt or interfere with the Service or its security.</li>
      <li>Do not copy, distribute, or exploit any part of the Service without our written permission.</li>
    </ul>

    <h2>3.&nbsp;Intellectual Property</h2>
    <p>
      All content, trademarks, and software on the Service are owned by iPapers or its licensors. You may not use
      our intellectual property without prior written consent.
    </p>

    <h2>4.&nbsp;Privacy</h2>
    <p>
      Your use of the Service is also governed by our <router-link to="/privacy-policy">Privacy&nbsp;Policy</router-link>,
      which explains how we collect, use, and protect your personal data.
    </p>

    <h2>5.&nbsp;Disclaimer of Warranties</h2>
    <p>
      The Service is provided "as is" without warranties of any kind, express or implied. We do not guarantee that
      the Service will be secure, error‑free, or available at all times.
    </p>

    <h2>6.&nbsp;Limitation of Liability</h2>
    <p>
      To the maximum extent permitted by law, we shall not be liable for any indirect, incidental, or consequential
      damages arising out of your use of—or inability to use—the Service.
    </p>

    <h2>7.&nbsp;Termination</h2>
    <p>
      We may suspend or terminate your access to the Service at any time, without notice, for any reason, including
      violation of these Terms.
    </p>

    <h2>8.&nbsp;Changes to These Terms</h2>
    <p>
      We may update these Terms from time to time. Material changes will be posted on this page. Continuing to use
      the Service after changes become effective constitutes acceptance of the revised Terms.
    </p>

    <h2>9.&nbsp;Governing Law</h2>
    <p>
      These Terms are governed by the laws of the State of New&nbsp;Jersey, U.S.A., without regard to conflict‑of‑law
      principles.
    </p>

    <h2>10.&nbsp;Contact Us</h2>
    <p>
      If you have any questions about these Terms, please email us at
      <a href="mailto:ipapers.ai@gmail.com">ipapers.ai@gmail.com</a>.
    </p>
  </main>
</template>

<script setup lang="ts">
// Simple SFC; no reactive state needed for static content.
</script>

<style scoped>
main { max-width: 760px; margin: 0 auto; padding: var(--sp-7) var(--sp-5); box-sizing: border-box; color: var(--text); line-height: 1.75; }
h1 { font-size: clamp(1.8rem, 4vw, 2.4rem); margin: 0 0 var(--sp-3); letter-spacing: -.015em; }
h2 { font-family: var(--font-sans); font-size: var(--fs-xl); margin: var(--sp-6) 0 var(--sp-2); }
p, li { color: var(--text-2); font-size: var(--fs-md); }
p { margin: 0 0 var(--sp-3); }
ul { margin: 0 0 var(--sp-3); padding-left: 1.3rem; }
li { margin-bottom: var(--sp-1); }
strong { color: var(--text); }
a { color: var(--link); }
.text-sm { font-size: var(--fs-sm); }
.text-gray-500 { color: var(--text-3); }
</style>
