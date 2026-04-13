const form   = document.getElementById('changePasswordForm');
const msgBox = document.getElementById('msg-box');
const csrf   = document.querySelector('[name=csrfmiddlewaretoken]').value;

function showMsg(text, type) {
  msgBox.textContent = text;
  msgBox.className   = type;
}

form.addEventListener('submit', async function (e) {
  e.preventDefault();

  const tempPw = document.getElementById('temp_password').value;
  const newPw  = document.getElementById('new_password').value;
  const confPw = document.getElementById('confirm_password').value;


  if (!tempPw) {
    showMsg('Please enter your temporary password.', 'error');
    return;
  }

  if (newPw.length < 8) {
    showMsg('New password must be at least 8 characters.', 'error');
    return;
  }

  if (newPw !== confPw) {
    showMsg('New passwords do not match.', 'error');
    return;
  }    

  if (tempPw === newPw) {
    showMsg('Your new password cannot be the same as your temporary password.', 'error');
    return;
  }    

  const btn = form.querySelector('button[type="submit"]');
  btn.disabled    = true;
  btn.textContent = 'Saving…';

  try {
    const res = await fetch('/set-password/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken':  csrf,
      },
      body: JSON.stringify({
        temp_password:    tempPw,
        new_password:     newPw,
        confirm_password: confPw,
      }),
    });

    const data = await res.json();

    if (data.success) {
      showMsg('Password set! Redirecting…', 'success');
      setTimeout(() => { window.location.href = data.redirect || '/login/'; }, 1200);
    } else {
      const err = Array.isArray(data.error) ? data.error.join(' ') : data.error;
      showMsg(err || 'Something went wrong.', 'error');
      btn.disabled    = false;
      btn.textContent = 'Set Password';
    }

  } catch (err) {
    showMsg('Network error — please try again.', 'error');
    btn.disabled    = false;
    btn.textContent = 'Set Password';
  }
});