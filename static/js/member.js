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

    document.querySelectorAll(".mpesa-pay-form").forEach((form) => {
        form.addEventListener("submit", async (event) => {
            event.preventDefault();
            const submitButton = form.querySelector("button[type='submit']");
            const feedback = form.parentElement.querySelector(".mpesa-feedback");
            submitButton.disabled = true;
            submitButton.textContent = "Sending...";
            feedback.textContent = "";

            try {
                const response = await fetch(form.action, {
                    method: "POST",
                    headers: {"X-CSRFToken": form.querySelector("[name=csrfmiddlewaretoken]").value},
                    body: new FormData(form),
                });
                const data = await response.json();
                if (!response.ok) {
                    throw new Error(data.error || "Unable to start M-Pesa payment.");
                }

                feedback.textContent = "Check your phone and enter your M-Pesa PIN.";
                const statusUrl = `${form.dataset.statusUrl}${data.id}/`;
                let attempts = 0;
                const poll = window.setInterval(async () => {
                    attempts += 1;
                    const statusResponse = await fetch(statusUrl);
                    if (!statusResponse.ok) return;
                    const status = await statusResponse.json();
                    if (status.status !== "pending") {
                        window.clearInterval(poll);
                        submitButton.disabled = false;
                        submitButton.textContent = "Pay";
                        feedback.textContent =
                            status.status === "success"
                                ? `Payment successful${status.mpesa_receipt ? `. Receipt: ${status.mpesa_receipt}` : "."}`
                                : status.result_description || "Payment was not completed.";
                        if (status.status === "success") window.setTimeout(() => window.location.reload(), 1500);
                    } else if (attempts >= 60) {
                        window.clearInterval(poll);
                        submitButton.disabled = false;
                        submitButton.textContent = "Pay";
                        feedback.textContent = "Payment is still pending. Refresh to check again.";
                    }
                }, 3000);
            } catch (error) {
                submitButton.disabled = false;
                submitButton.textContent = "Pay";
                feedback.textContent = error.message;
            }
        });
    });
});
