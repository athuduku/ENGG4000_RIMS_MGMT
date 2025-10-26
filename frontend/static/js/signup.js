document.getElementById("signupForm").addEventListener("submit", async function(event) {
  event.preventDefault();

  const name = document.getElementById("name").value.trim();
  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;
  const confirmPassword = document.getElementById("confirmPassword").value;
  const consent = document.getElementById("consent");
  const loginUrl = document.querySelector(".button").dataset.loginUrl;

  if (password !== confirmPassword) {
    alert("Passwords do not match!");
    return;
  }

  try {
    const response = await fetch("/signup/", {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        "X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]").value
      },
      body: new URLSearchParams({
        name: name,
        email: email,
        password: password,
        consent: consent.checked ? "true" : "false"  // ✅ optional, store value if you want
      })
    });

    const data = await response.json();

    if (response.ok) {
      alert(data.success || "Account created successfully!");
      window.location.href = loginUrl;
    } else {
      alert(data.error || "Signup failed. Please try again.");
    }
  } catch (err) {
    console.error("Signup failed:", err);
    alert("Signup failed. Please try again later.");
  }
});
