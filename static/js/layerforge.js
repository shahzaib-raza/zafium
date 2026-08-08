const preview = document.getElementById("preview");
const svgWrapper = document.getElementById("svgWrapper");
const loader = document.getElementById("loader");
const imageUpload = document.getElementById("imageUpload");
const downloadBtn = document.getElementById("downloadBtn");
const sliders = document.querySelectorAll("input[type=range]");

let currentImage = null;
let currentSVG = null;
let zoomLevel = 1;
const zoomStep = 0.15;

function showLoader() {
    svgWrapper.innerHTML = "";
    loader.classList.remove("hidden");
}

function hideLoader() {
    loader.classList.add("hidden");
}

function debounce(fn, delay = 300) {
    let t;
    return (...args) => {
        clearTimeout(t);
        t = setTimeout(() => fn(...args), delay);
    };
}

function collectParams() {
    return {
        edge_detection_threshold: edge_detection_threshold.value,
        min_anchor_distance: min_anchor_distance.value,
    };
}

function processImage() {
    if (!currentImage) return;

    showLoader();

    const formData = new FormData();
    formData.append("image", currentImage);

    Object.entries(collectParams()).forEach(([k, v]) =>
        formData.append(k, v)
    );

    fetch("/generate/", { method: "POST", body: formData })
        .then(res => res.text())
        .then(svg => {
            hideLoader();
            currentSVG = svg;
            svgWrapper.innerHTML = svg;
            applyZoom();
            downloadBtn.disabled = false;
        })
        .catch(() => {
            hideLoader();
            alert("SVG generation failed.");
        });
}

const debouncedProcess = debounce(processImage);

imageUpload.addEventListener("change", e => {
    currentImage = e.target.files[0];
    processImage();
});

sliders.forEach(slider => {
    slider.addEventListener("input", e => {
        document.getElementById(e.target.id + "_val").textContent = e.target.value;
        debouncedProcess();
    });
});

downloadBtn.addEventListener("click", () => {
    if (!currentSVG) return;
    const blob = new Blob([currentSVG], { type: "image/svg+xml" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "layerforge.svg";
    a.click();
    URL.revokeObjectURL(url);
});

function applyZoom() {
    svgWrapper.style.transform = `scale(${zoomLevel})`;
}

zoomIn.onclick = () => {
    zoomLevel = Math.min(zoomLevel + zoomStep, 4);
    applyZoom();
};

zoomOut.onclick = () => {
    zoomLevel = Math.max(zoomLevel - zoomStep, 0.2);
    applyZoom();
};

zoomReset.onclick = () => {
    zoomLevel = 1;
    applyZoom();
};
