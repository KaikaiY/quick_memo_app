function closeAllMenus() {
  document.querySelectorAll(".memo-menu-button").forEach((button) => {
    button.setAttribute("aria-expanded", "false");
  });

  document.querySelectorAll(".memo-menu-list").forEach((menu) => {
    menu.hidden = true;
  });
}

document.addEventListener("click", (event) => {
  const button = event.target.closest(".memo-menu-button");

  if (button) {
    const menu = button.closest(".memo-menu").querySelector(".memo-menu-list");
    const isOpen = button.getAttribute("aria-expanded") === "true";

    closeAllMenus();

    if (!isOpen) {
      button.setAttribute("aria-expanded", "true");
      menu.hidden = false;
    }

    return;
  }

  if (!event.target.closest(".memo-menu")) {
    closeAllMenus();
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    closeAllMenus();
  }
});
