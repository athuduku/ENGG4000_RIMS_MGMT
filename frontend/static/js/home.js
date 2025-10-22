document.addEventListener("DOMContentLoaded", () => {
  const heroText = document.querySelector(".hero h2");
  heroText.style.opacity = "0";
  setTimeout(() => {
    heroText.style.transition = "opacity 1s ease";
    heroText.style.opacity = "1";
  }, 300);
});
