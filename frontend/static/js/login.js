document.getElementById("loginForm").addEventListener("submit", async function(event) {
  event.preventDefault();

  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value.trim();
  const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

  try {
    const response = await fetch("/login/", {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        "X-CSRFToken": csrfToken
      },
      body: new URLSearchParams({ email, password })
    });

    const data = await response.json();

    if (data.redirect) {
      window.location.href = data.redirect;
    } else {
      showError(data.error || "Invalid credentials.");
    }
  } catch (err) {
    console.error("Login error:", err);
    showError("Login failed. Please try again later.");
  }
});

function showForgotAlert() {
  showInfo('To reset your password, please contact your IBME administrator.');
}

function showError(message) {
  const errorDiv = document.getElementById("loginError");
  errorDiv.textContent = message;
  errorDiv.style.display = "block";
  errorDiv.style.background = "#fee2e2";
  errorDiv.style.color = "#991b1b";
  errorDiv.style.borderColor = "#fca5a5";
}

function showInfo(message) {
  const errorDiv = document.getElementById("loginError");
  errorDiv.textContent = message;
  errorDiv.style.display = "block";
  errorDiv.style.background = "#eff6ff";
  errorDiv.style.color = "#1e40af";
  errorDiv.style.borderColor = "#bfdbfe";
}