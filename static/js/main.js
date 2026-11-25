document.addEventListener("DOMContentLoaded", () => {
  // Filtro istantaneo sulle schede visibili nella pagina /entries
  const liveSearch = document.getElementById("liveSearch");
  const cards = document.querySelectorAll(".entry-card");

  if (liveSearch && cards.length > 0) {
    liveSearch.addEventListener("input", () => {
      const term = liveSearch.value.trim().toLowerCase();
      cards.forEach((card) => {
        const name = card.dataset.name || "";
        const lore = card.dataset.lore || "";
        const matches = name.includes(term) || lore.includes(term);
        card.style.display = matches ? "flex" : "none";
      });
    });
  }

  // Controllo semplice prima dell'invio del form commenti
  const commentForm = document.getElementById("commentForm");
  if (commentForm) {
    commentForm.addEventListener("submit", (event) => {
      const author = document.getElementById("authorInput")?.value.trim();
      const message = document.getElementById("messageInput")?.value.trim();

      if (!author || !message) {
        event.preventDefault();
        alert("Inserisci sia il nickname sia il commento prima di inviare.");
      }
    });
  }
});