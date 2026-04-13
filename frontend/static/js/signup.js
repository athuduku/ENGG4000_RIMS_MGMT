const passwordInput = document.getElementById("password");
const strengthDot = document.getElementById("strengthDot");

passwordInput.addEventListener("input", function () {
  const password = passwordInput.value;

  let strength = 0;

  if (password.length >= 8) strength++;
  if (/[A-Z]/.test(password)) strength++;
  if (/[0-9]/.test(password)) strength++;
  if (/[^A-Za-z0-9]/.test(password)) strength++;

  if (password.length === 0) {
    strengthDot.style.background = "transparent";
  } else if (strength <= 1) {
    strengthDot.style.background = "red";
  } else if (strength <= 3) {
    strengthDot.style.background = "orange";
  } else {
    strengthDot.style.background = "green";
  }
});

document.getElementById("signupForm").addEventListener("submit", async function (event) {
  event.preventDefault();

  const name            = document.getElementById("name").value.trim();
  const email           = document.getElementById("email").value.trim();
  const password        = document.getElementById("password").value;
  const confirmPassword = document.getElementById("confirmPassword").value;
  const consent         = document.getElementById("consent");
  const loginUrl        = document.querySelector(".button").dataset.loginUrl;

  if (password !== confirmPassword) {
    alert("Passwords do not match!");
    return;
  }

  if (password.length < 8) {
    alert("Password must be at least 8 characters.");
    return;
  }

  if (!/[A-Za-z]/.test(password) || !/[0-9]/.test(password)) {
    alert("Password must contain both letters and numbers.");
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
        name,
        email,
        password,
        confirm_password: confirmPassword,
        consent: consent.checked ? "true" : "false"
      })
    });

    const data = await response.json();

    if (response.ok) {
      alert(data.message || "Account created successfully!");
      window.location.href = loginUrl;
    } else {
      alert(data.error || "Signup failed. Please try again.");
    }
  } catch (err) {
    console.error("Signup failed:", err);
    alert("Signup failed. Please try again later.");
  }
});