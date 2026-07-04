document.addEventListener("DOMContentLoaded", function () {

    const toggle = document.getElementById("menuToggle");
    const menu = document.getElementById("navLinks");

    toggle.addEventListener("click", function () {

        toggle.classList.toggle("active");
        menu.classList.toggle("active");

    });

})