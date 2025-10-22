document.getElementById("resetForm").addEventListener("submit", function(event) {
  event.preventDefault();

  const email = document.getElementById("email").value.trim();
  const newPassword = document.getElementById("newPassword").value;
  const confirmPassword = document.getElementById("confirmPassword").value;
  const loginUrl = document.querySelector(".button").dataset.loginUrl;

  if (newPassword !== confirmPassword) {
    alert("Passwords do not match!");
    return;
  }

  // Simulate password update in localStorage
  let users = JSON.parse(localStorage.getItem("users")) || [];
  let user = users.find(u => u.email === email);

  if (!user) {
    alert("No user found with this email!");
    return;
  }

  // Update the user password
  user.password = newPassword;
  localStorage.setItem("users", JSON.stringify(users));

  alert("Password updated successfully! Please log in again.");
  window.location.href = loginUrl; 
});
