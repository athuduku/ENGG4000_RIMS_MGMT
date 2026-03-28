document.getElementById("resetForm").addEventListener("submit", async function (event) {
  event.preventDefault();
  const email = document.getElementById("email").value.trim();

  try {
    const response = await fetch("/forgot_pass/", {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        "X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]").value,
      },
      body: new URLSearchParams({ email }),
    });

    const data = await response.json();

    if (response.ok) {
      alert(data.success || "If that email exists, a reset link was sent!");
      window.location.href = document.querySelector(".button").dataset.loginUrl;
    } else {
      alert(data.error || "Failed to send reset link. Try again later.");
    }
  } catch (err) {
    console.error("Error:", err);
    alert("Something went wrong. Please try again.");
  }
});
