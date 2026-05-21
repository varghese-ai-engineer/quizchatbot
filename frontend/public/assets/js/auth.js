/* =============================================================
   QuizChatbot — Auth Pages JavaScript
   Airbnb JS style
   ============================================================= */

'use strict';

// ── Toggle password visibility ────────────────────────────────
function togglePassword(inputId, btn) {
  const input = document.getElementById(inputId);
  const icon = btn.querySelector('i');
  if (!input || !icon) return;

  if (input.type === 'password') {
    input.type = 'text';
    icon.classList.replace('bi-eye', 'bi-eye-slash');
  } else {
    input.type = 'password';
    icon.classList.replace('bi-eye-slash', 'bi-eye');
  }
}

// ── Password strength meter ───────────────────────────────────
(function initStrengthMeter() {
  const passwordInput = document.getElementById('password');
  const bar = document.getElementById('strength-bar');
  const label = document.getElementById('strength-label');

  if (!passwordInput || !bar || !label) return;

  const levels = [
    { width: '0%',   color: 'transparent',          text: '' },
    { width: '25%',  color: '#ff5c7c',               text: 'Weak' },
    { width: '50%',  color: '#f59e0b',               text: 'Fair' },
    { width: '75%',  color: '#6c63ff',               text: 'Good' },
    { width: '100%', color: '#22c55e',               text: 'Strong' },
  ];

  function getStrength(value) {
    let score = 0;
    if (value.length >= 6) score += 1;
    if (value.length >= 10) score += 1;
    if (/[A-Z]/.test(value)) score += 1;
    if (/[0-9!@#$%^&*]/.test(value)) score += 1;
    return Math.min(score, 4);
  }

  passwordInput.addEventListener('input', () => {
    const strength = getStrength(passwordInput.value);
    bar.style.width = levels[strength].width;
    bar.style.background = levels[strength].color;
    label.textContent = levels[strength].text;
    label.style.color = levels[strength].color;
  });
}());

// ── Show spinner on form submit ───────────────────────────────
(function initSubmitSpinner() {
  const forms = [
    { formId: 'login-form',  btnId: 'login-submit-btn',  loaderId: 'login-loader' },
    { formId: 'signup-form', btnId: 'signup-submit-btn', loaderId: 'signup-loader' },
  ];

  forms.forEach(({ formId, btnId, loaderId }) => {
    const form = document.getElementById(formId);
    const btn = document.getElementById(btnId);
    const loader = document.getElementById(loaderId);

    if (!form || !btn || !loader) return;

    form.addEventListener('submit', () => {
      const btnText = btn.querySelector('.btn-text');
      if (btnText) btnText.classList.add('d-none');
      loader.classList.remove('d-none');
      btn.disabled = true;
    });
  });
}());

// ── Confirm password match highlight ─────────────────────────
(function initConfirmMatch() {
  const password = document.getElementById('password');
  const confirm = document.getElementById('confirm');

  if (!password || !confirm) return;

  function check() {
    if (confirm.value === '') {
      confirm.style.borderColor = '';
      return;
    }
    if (confirm.value === password.value) {
      confirm.style.borderColor = '#22c55e';
      confirm.style.boxShadow = '0 0 0 3px rgba(34,197,94,0.2)';
    } else {
      confirm.style.borderColor = '#ff5c7c';
      confirm.style.boxShadow = '0 0 0 3px rgba(255,92,124,0.2)';
    }
  }

  confirm.addEventListener('input', check);
  password.addEventListener('input', check);
}());
