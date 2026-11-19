document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".password-toggle").forEach((button) => {
        const wrap = button.closest(".password-wrap");
        const input = wrap?.querySelector("input");
        if (!input) return;
        button.innerHTML = '<svg aria-hidden="true" viewBox="0 0 24 24"><path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></svg>';
        button.addEventListener("click", () => {
            const show = input.type === "password";
            input.type = show ? "text" : "password";
            button.setAttribute("aria-pressed", String(show));
            button.setAttribute("aria-label", show ? "Hide password" : "Show password");
        });
    });

    document.querySelectorAll(".auth-form input:not([type=checkbox]), .auth-form select").forEach((control) => {
        if (!control.getAttribute("placeholder") && control.tagName === "INPUT") {
            const label = document.querySelector(`label[for="${control.id}"]`);
            if (label) control.setAttribute("placeholder", label.textContent.replace(" *", ""));
        }
    });
});
