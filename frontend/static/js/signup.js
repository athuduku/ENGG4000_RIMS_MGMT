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

  if (!consent.checked) {
    alert("You must agree to the demographic consent before signing up.");
    return;
  }

  try {

    let users = JSON.parse(localStorage.getItem("users")) || [];
    const exists = users.find(u => u.email === email);

    if (exists) {
      alert("A user with this email already exists!");
      return;
    }

    users.push({ name, email, password });
    localStorage.setItem("users", JSON.stringify(users));

    alert("Account created successfully!");
    window.location.href = loginUrl; 
  } 
  catch (err) {
    console.error("Signup failed:", err);
    alert("Signup failed. Please try again later.");
  }
});
