document.addEventListener("DOMContentLoaded", function () {

    /* ==========================
       COUNTERS
    ========================== */

    const counters = document.querySelectorAll(".counter");

    let counterAnimated = false;

    function animateCounters(){

        if(counterAnimated) return;

        counters.forEach(counter=>{

            const target = Number(counter.dataset.target);

            let current = 0;

            const step = Math.ceil(target/100);

            function update(){

                current += step;

                if(current >= target){

                    counter.textContent = target + "+";

                }

                else{

                    counter.textContent = current;

                    requestAnimationFrame(update);

                }

            }

            update();

        });

        counterAnimated = true;

    }

    const hero = document.querySelector(".hero-stats");

    if(hero){

        const observer = new IntersectionObserver(entries=>{

            entries.forEach(entry=>{

                if(entry.isIntersecting){

                    animateCounters();

                }

            });

        },{

            threshold:.4

        });

        observer.observe(hero);

    }



    /* ==========================
       FADE UP
    ========================== */

    const cards = document.querySelectorAll(".portfolio-card");

    const cardObserver = new IntersectionObserver(entries=>{

        entries.forEach(entry=>{

            if(entry.isIntersecting){

                entry.target.classList.add("fade-up");

            }

        });

    },{

        threshold:.1

    });

    cards.forEach(card=>cardObserver.observe(card));



    /* ==========================
       PROGRESS BARS
    ========================== */

    document.querySelectorAll(".progress-fill").forEach(bar=>{

        const width = bar.dataset.progress;

        bar.style.width = "0";

        requestAnimationFrame(()=>{

            bar.style.width = width + "%";

        });

    });

});