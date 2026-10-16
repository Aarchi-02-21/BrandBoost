function toggleMenu() {
    const nav = document.getElementById("mainNav");

    if (nav) {
        nav.classList.toggle("open");
    }
}

document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".flash").forEach((element) => {
        setTimeout(() => element.remove(), 5500);
    });

    document.querySelectorAll("form").forEach((form) => {
        form.addEventListener("submit", () => {
            const button = form.querySelector("button");

            if (button) {
                setTimeout(() => {
                    button.disabled = true;
                    button.style.opacity = "0.7";
                    button.innerText = "Processing...";
                }, 10);
            }
        });
    });
});
