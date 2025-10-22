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
      alert(data.error || "Invalid credentials.");
    }
  } catch (err) {
    console.error("Login error:", err);
    alert("Login failed. Please try again later.");
  }
});
