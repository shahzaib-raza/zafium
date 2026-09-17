/* =========================================================
   ZAFIUM PORTFOLIO
========================================================= */

document.addEventListener("DOMContentLoaded", function () {


    /* =====================================================
       SCROLL REVEAL
    ===================================================== */

    const revealElements = document.querySelectorAll(
        ".featured-project, " +
        ".portfolio-category-card, " +
        ".showcase-project, " +
        ".process-step, " +
        ".tech-content, " +
        ".portfolio-cta-box"
    );


    if ("IntersectionObserver" in window) {

        const observer = new IntersectionObserver(

            function (entries) {

                entries.forEach(function (entry) {

                    if (!entry.isIntersecting) {
                        return;
                    }

                    entry.target.classList.add("portfolio-visible");

                    observer.unobserve(entry.target);

                });

            },

            {
                threshold: 0.12
            }

        );


        revealElements.forEach(function (element) {

            element.classList.add("portfolio-reveal");

            observer.observe(element);

        });

    }


    /* =====================================================
       CATEGORY CARD MOUSE GLOW
    ===================================================== */

    const categoryCards = document.querySelectorAll(
        ".portfolio-category-card"
    );


    categoryCards.forEach(function (card) {

        card.addEventListener("mousemove", function (event) {

            const rect = card.getBoundingClientRect();

            const x = event.clientX - rect.left;
            const y = event.clientY - rect.top;


            card.style.setProperty(
                "--mouse-x",
                `${x}px`
            );


            card.style.setProperty(
                "--mouse-y",
                `${y}px`
            );

        });


        card.addEventListener("mouseleave", function () {

            card.style.removeProperty("--mouse-x");

            card.style.removeProperty("--mouse-y");

        });

    });


    /* =====================================================
       SMOOTH ANCHOR SCROLL
    ===================================================== */

    document.querySelectorAll(
        'a[href^="#"]'
    ).forEach(function (link) {

        link.addEventListener("click", function (event) {

            const targetId =
                this.getAttribute("href");


            if (
                !targetId ||
                targetId === "#"
            ) {
                return;
            }


            const target =
                document.querySelector(targetId);


            if (!target) {
                return;
            }


            event.preventDefault();


            target.scrollIntoView({
                behavior: "smooth",
                block: "start"
            });

        });

    });

});