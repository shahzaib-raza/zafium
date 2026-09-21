document.addEventListener("DOMContentLoaded", () => {

    const cinematic =
        document.querySelector("#lf-cinematic");

    if (!cinematic) return;


    const steps =
        [...document.querySelectorAll(
            ".lf-scroll-step"
        )];


    const copyStages =
        [...document.querySelectorAll(
            ".lf-copy-stage"
        )];


    const pixels =
        [...document.querySelectorAll(
            ".lf-pixel-art .px"
        )];


    const particles =
        [...document.querySelectorAll(
            ".lf-color-particles i"
        )];


    const vectorPaths =
        [...document.querySelectorAll(
            ".vector-path"
        )];


    const vectorNodes =
        [...document.querySelectorAll(
            ".vector-nodes circle"
        )];


    const scanLine =
        document.querySelector(
            ".lf-scan-line"
        );


    /*
     * -----------------------------------------------------
     * HELPERS
     * -----------------------------------------------------
     */

    const clamp = (
        value,
        min = 0,
        max = 1
    ) => {

        return Math.min(
            Math.max(value, min),
            max
        );

    };


    /*
     * -----------------------------------------------------
     * GET CURRENT SCROLL PROGRESS
     *
     * Returns:
     *
     * 0.0 → beginning
     * 1.0 → end
     * -----------------------------------------------------
     */

    function getProgress() {

        const rect =
            cinematic.getBoundingClientRect();

        const total =
            cinematic.offsetHeight -
            window.innerHeight;

        if (total <= 0) {

            return 0;

        }

        return clamp(
            -rect.top / total
        );

    }


    /*
     * -----------------------------------------------------
     * DETERMINE STAGE
     * -----------------------------------------------------
     */

    function getStage(progress) {

        const totalStages =
            steps.length;

        const scaled =
            progress *
            totalStages;

        return Math.min(
            Math.floor(scaled),
            totalStages - 1
        );

    }


    /*
     * -----------------------------------------------------
     * UPDATE TEXT
     * -----------------------------------------------------
     */

    function updateText(stage) {

        copyStages.forEach(
            (copy, index) => {

                copy.classList.toggle(
                    "active",
                    index === stage
                );

            }
        );

    }


    /*
     * -----------------------------------------------------
     * ANIMATE PIXELS
     * -----------------------------------------------------
     */

    function animatePixels(
        progress,
        stage
    ) {

        pixels.forEach(
            (pixel, index) => {

                /*
                 * Give every pixel a slightly different
                 * departure point.
                 */

                const delay =
                    (index % 10) * 0.012;


                /*
                 * Pixels start breaking apart around
                 * stage 1.
                 */

                const separation =
                    clamp(
                        (
                            progress - .14
                        ) / .22 -
                        delay
                    );


                if (stage >= 1) {

                    const angle =
                        (
                            index /
                            pixels.length
                        ) *
                        Math.PI *
                        2;

                    const direction =
                        index % 2
                            ? 1
                            : -1;

                    const distance =
                        separation *
                        (
                            80 +
                            (index % 6) * 20
                        );


                    const x =
                        Math.cos(angle) *
                        distance *
                        direction;


                    const y =
                        Math.sin(angle) *
                        distance;


                    pixel.style.transform =
                        `translate(
                            ${x}px,
                            ${y}px
                        )`;


                    pixel.style.opacity =
                        `${1 - separation * .9}`;

                } else {

                    pixel.style.transform =
                        "translate(0,0)";

                    pixel.style.opacity =
                        "1";

                }

            }
        );

    }


    /*
     * -----------------------------------------------------
     * COLOR PARTICLES
     * -----------------------------------------------------
     */

    function animateParticles(
        progress
    ) {

        /*
         * Color separation happens between
         * approximately 20% and 45%.
         */

        const separation =
            clamp(
                (progress - .20) / .25
            );


        particles.forEach(
            (particle, index) => {

                const angle =
                    (
                        index /
                        particles.length
                    ) *
                    Math.PI *
                    2;


                const radius =
                    separation *
                    (
                        80 +
                        (index % 5) * 18
                    );


                const x =
                    Math.cos(angle) *
                    radius;


                const y =
                    Math.sin(angle) *
                    radius;


                particle.style.transform =
                    `translate(
                        ${x}px,
                        ${y}px
                    )`;


                particle.style.opacity =
                    `${separation}`;

            }
        );

    }


    /*
     * -----------------------------------------------------
     * LAYER ANIMATION
     * -----------------------------------------------------
     */

    function animateLayers(
        progress
    ) {

        const layerSystem =
            document.querySelector(
                ".lf-layer-system"
            );


        if (!layerSystem) return;


        const layerProgress =
            clamp(
                (progress - .40) / .18
            );


        const x =
            160 -
            layerProgress * 160;


        const scale =
            .65 +
            layerProgress * .35;


        const rotate =
            -30 +
            layerProgress * 30;


        layerSystem.style.transform =
            `
            translateX(${x}px)
            scale(${scale})
            rotateY(${rotate}deg)
            `;

    }


    /*
     * -----------------------------------------------------
     * VECTOR PATH DRAWING
     * -----------------------------------------------------
     */

    function animateVector(
        progress
    ) {

        /*
         * Vector construction starts around 58%.
         */

        const vectorProgress =
            clamp(
                (progress - .55) / .25
            );


        vectorPaths.forEach(
            path => {

                const length =
                    path.getTotalLength();


                path.style.strokeDasharray =
                    length;


                path.style.strokeDashoffset =
                    length *
                    (
                        1 -
                        vectorProgress
                    );

            }
        );


        /*
         * Reveal vector nodes progressively.
         */

        vectorNodes.forEach(
            (node, index) => {

                const nodeProgress =
                    clamp(
                        (
                            vectorProgress -
                            index * .035
                        ) /
                        .35
                    );


                node.style.opacity =
                    nodeProgress;


                const scale =
                    0.7 +
                    nodeProgress * .3;


                node.style.transform =
                    `scale(${scale})`;

            }
        );

    }


    /*
     * -----------------------------------------------------
     * FINAL VECTOR
     * -----------------------------------------------------
     */

    function animateFinal(
        progress
    ) {

        const finalVector =
            document.querySelector(
                ".lf-final-vector"
            );


        if (!finalVector) return;


        const finalProgress =
            clamp(
                (progress - .76) / .18
            );


        const scale =
            .55 +
            finalProgress * .45;


        finalVector.style.opacity =
            finalProgress;


        finalVector.style.transform =
            `scale(${scale})`;

    }


    /*
     * -----------------------------------------------------
     * SCAN LINE
     * -----------------------------------------------------
     */

    function animateScan(
        progress
    ) {

        if (!scanLine) return;


        /*
         * Scan the raster while analyzing.
         */

        const scanProgress =
            clamp(
                (progress - .12) / .22
            );


        scanLine.style.top =
            `${15 + scanProgress * 70}%`;


        scanLine.style.opacity =
            progress >= .10 &&
            progress <= .38
                ? "1"
                : ".25";

    }


    /*
     * -----------------------------------------------------
     * HUD
     * -----------------------------------------------------
     */

    function updateHUD(
        progress
    ) {

        const ui1 =
            document.querySelector(".ui-1");

        const ui2 =
            document.querySelector(".ui-2");

        const ui3 =
            document.querySelector(".ui-3");

        const ui4 =
            document.querySelector(".ui-4");


        if (ui1) {

            ui1.style.opacity =
                progress > .05
                    ? ".9"
                    : ".3";

        }


        if (ui2) {

            ui2.style.opacity =
                progress > .25
                    ? ".9"
                    : ".3";

        }


        if (ui3) {

            ui3.style.opacity =
                progress > .52
                    ? ".9"
                    : ".3";

        }


        if (ui4) {

            ui4.style.opacity =
                progress > .70
                    ? ".9"
                    : ".3";

        }

    }


    /*
     * -----------------------------------------------------
     * MAIN RENDER
     * -----------------------------------------------------
     */

    function render() {

        const progress =
            getProgress();


        const stage =
            getStage(progress);


        /*
         * Tell CSS which major visual state
         * is active.
         */

        cinematic.dataset.stage =
            stage;


        /*
         * Update text.
         */

        updateText(stage);


        /*
         * Animate visual systems.
         */

        animatePixels(
            progress,
            stage
        );


        animateParticles(
            progress
        );


        animateLayers(
            progress
        );


        animateVector(
            progress
        );


        animateFinal(
            progress
        );


        animateScan(
            progress
        );


        updateHUD(
            progress
        );

    }


    /*
     * -----------------------------------------------------
     * REQUEST ANIMATION FRAME
     * -----------------------------------------------------
     */

    let ticking = false;


    function requestRender() {

        if (ticking) return;


        ticking = true;


        requestAnimationFrame(
            () => {

                render();

                ticking = false;

            }
        );

    }


    window.addEventListener(
        "scroll",
        requestRender,
        {
            passive: true
        }
    );


    window.addEventListener(
        "resize",
        requestRender
    );


    /*
     * INITIAL RENDER
     */

    render();

});