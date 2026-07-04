let imageId = null;
let debounceTimer = null;

const sliders = [
    "k_min",
    "k_max",
    "cluster_scale",
    "min_area_ratio"
];

function updateLabels() {
    document.getElementById("kmin_val").textContent =
        document.getElementById("k_min").value;

    document.getElementById("kmax_val").textContent =
        document.getElementById("k_max").value;

    document.getElementById("cs_val").textContent =
        document.getElementById("cluster_scale").value;

    document.getElementById("mar_val").textContent =
        document.getElementById("min_area_ratio").value;
}

/* ---------------- IMAGE UPLOAD ---------------- */

document.getElementById("imageUpload").onchange = async (e) => {
    const form = new FormData();
    form.append("image", e.target.files[0]);

    const res = await fetch("/upload/", {
        method: "POST",
        body: form
    });

    const json = await res.json();
    imageId = json.image_id;

    scheduleUpdate();
};

/* ---------------- SLIDER HANDLING ---------------- */

sliders.forEach(id => {
    document.getElementById(id).oninput = () => {
        updateLabels();
        scheduleUpdate();
    };
});

function scheduleUpdate() {
    if (!imageId) return;
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(generateSVG, 300);
}

/* ---------------- SVG GENERATION ---------------- */

async function generateSVG() {
    const data = new FormData();
    data.append("image_id", imageId);

    sliders.forEach(id => {
        data.append(id, document.getElementById(id).value);
    });

    const res = await fetch("/generate/", {
        method: "POST",
        body: data
    });

    const json = await res.json();

    const preview = document.getElementById("preview");
    preview.innerHTML = json.svg;

    enableSVGHover();
}

/* ---------------- SVG HOVER LOGIC ---------------- */

function enableSVGHover() {
    const paths = document.querySelectorAll("#preview svg path");

    paths.forEach(path => {
        path.addEventListener("mouseenter", () => {
            const group = path.closest(".svg-layer");
            if (!group) return;

            group.querySelectorAll("path").forEach(p => {
                p.dataset.oldStroke = p.getAttribute("stroke") || "none";
                p.dataset.oldStrokeWidth = p.getAttribute("stroke-width") || "0";

                p.setAttribute("stroke", "#00aaff");
                p.setAttribute("stroke-width", "2");
            });
        });

        path.addEventListener("mouseleave", () => {
            const group = path.closest(".svg-layer");
            if (!group) return;

            group.querySelectorAll("path").forEach(p => {
                p.setAttribute("stroke", p.dataset.oldStroke);
                if (p.dataset.oldStrokeWidth === "0") {
                    p.removeAttribute("stroke-width");
                } else {
                    p.setAttribute("stroke-width", p.dataset.oldStrokeWidth);
                }
            });
        });
    });
}


updateLabels();
