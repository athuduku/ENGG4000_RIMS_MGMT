
const form        = document.getElementById('setPasswordForm');
const msgBox      = document.getElementById('msg-box');
const csrf        = document.querySelector('[name=csrfmiddlewaretoken]').value;
const passwordInput = document.getElementById('new_password');
const strengthDot   = document.getElementById('strengthDot');

function showMsg(text, type) {
  msgBox.textContent = text;
  msgBox.className   = type;
}

// ── Strength indicator ────────────────────────────────────
passwordInput.addEventListener('input', function () {
  const pw = passwordInput.value;
  let strength = 0;
  if (pw.length >= 8)           strength++;
  if (/[A-Z]/.test(pw))         strength++;
  if (/[0-9]/.test(pw))         strength++;
  if (/[^A-Za-z0-9]/.test(pw))  strength++;
  if (pw.length === 0)    strengthDot.style.background = 'transparent';
  else if (strength <= 1) strengthDot.style.background = 'red';
  else if (strength <= 3) strengthDot.style.background = 'orange';
  else                    strengthDot.style.background = 'green';
});

// ── Submit ────────────────────────────────────────────────
form.addEventListener('submit', async function (e) {
  e.preventDefault();
  const tempPw = document.getElementById('temp_password').value;
  const newPw  = document.getElementById('new_password').value;
  const confPw = document.getElementById('confirm_password').value;
  // Client-side validation
  if (!tempPw) {
    showMsg('Please enter your temporary password.', 'error'); return;
  }
  if (newPw.length < 8) {
    showMsg('New password must be at least 8 characters.', 'error'); return;
  }
  if (!/[A-Za-z]/.test(newPw) || !/[0-9]/.test(newPw)) {
    showMsg('Password must contain both letters and numbers.', 'error'); return;
  }
  if (newPw !== confPw) {
    showMsg('New passwords do not match.', 'error'); return;
  }
  if (newPw === tempPw) {
    showMsg('New password cannot be the same as your temporary password.', 'error'); return;
  }
  const btn = form.querySelector('button[type="submit"]');
  btn.disabled    = true;
  btn.textContent = 'Saving…';
  try {
    const res = await fetch('/set-password/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
      body: JSON.stringify({ temp_password: tempPw, new_password: newPw, confirm_password: confPw }),
    });
    const data = await res.json();
    if (data.success) {
      showMsg('Password set! Redirecting…', 'success');
      setTimeout(() => { window.location.href = data.redirect || '/dashboard/'; }, 1200);
    } else {
      const err = Array.isArray(data.error) ? data.error.join(' ') : data.error;
      showMsg(err || 'Something went wrong.', 'error');
      btn.disabled    = false;
      btn.textContent = 'Set Password';
    }
  } catch {
    showMsg('Network error — please try again.', 'error');
    btn.disabled    = false;
    btn.textContent = 'Set Password';
  }
});