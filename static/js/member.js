document.addEventListener("DOMContentLoaded", () => {
    const button = document.querySelector(".menu-button");
    const sidebar = document.querySelector(".sidebar");
    const main = document.querySelector(".member-main");
    if (button && sidebar && main) {
        button.addEventListener("click", () => {
            const open = sidebar.classList.toggle("open");
            main.classList.toggle("overlay-open", open);
            button.setAttribute("aria-expanded", String(open));
        });
        sidebar.querySelectorAll("a").forEach((link) => link.addEventListener("click", () => {
            sidebar.classList.remove("open");
            main.classList.remove("overlay-open");
            button.setAttribute("aria-expanded", "false");
        }));
    }
});
