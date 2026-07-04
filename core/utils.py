import cv2
import numpy as np
import svgwrite
from skimage.restoration import denoise_bilateral
from io import StringIO
from .smoothed import img_to_svg_smoothed


# ============================================================
# K-MEANS CLUSTER ESTIMATION
# ============================================================
def estimate_k_clusters(lab_img, k_min, k_max, scale):
    small = cv2.resize(lab_img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    Z = small.reshape((-1, 3)).astype(np.float32)

    distortions = []
    for k in range(k_min, k_max + 1):
        _, _, centers = cv2.kmeans(
            Z, k, None,
            (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 1.0),
            3, cv2.KMEANS_PP_CENTERS
        )
        diff = Z[:, None, :] - centers[None, :, :]
        dist = np.min(np.sum(diff ** 2, axis=2), axis=1)
        distortions.append(dist.mean())

    curvature = np.diff(np.array(distortions), 2)
    return int(np.clip(np.argmin(curvature) + k_min + 1, k_min, k_max))


# ============================================================
# FILL HOLES IN MASK (CRITICAL FIX)
# ============================================================
def fill_holes(mask):
    h, w = mask.shape
    flood = mask.copy()
    flood = np.pad(flood, 1, mode="constant")

    cv2.floodFill(flood, None, (0, 0), 1)
    flood = flood[1:-1, 1:-1]

    holes = (flood == 0)
    return mask | holes.astype(np.uint8)


# ============================================================
# CONTOUR SIMPLIFICATION
# ============================================================
def simplify_contour(cnt, area):
    epsilon = max(1.5, np.sqrt(area) * 0.004)
    return cv2.approxPolyDP(cnt, epsilon, True)


# ============================================================
# SVG PATH
# ============================================================
def contour_to_path(cnt):
    cnt = cnt.squeeze()
    d = [f"M {cnt[0][0]:.2f},{cnt[0][1]:.2f}"]
    for p in cnt[1:]:
        d.append(f"L {p[0]:.2f},{p[1]:.2f}")
    d.append("Z")
    return " ".join(d)



# ============================================================
# CONTOUR SMOOTHING (Chaikin)
# ============================================================
def chaikin(points, iterations=2):
    for _ in range(iterations):
        new = []
        for i in range(len(points)):
            p0 = points[i]
            p1 = points[(i + 1) % len(points)]
            q = 0.75 * p0 + 0.25 * p1
            r = 0.25 * p0 + 0.75 * p1
            new.extend([q, r])
        points = np.array(new)
    return points


# ============================================================
# ADAPTIVE SIMPLIFICATION
# ============================================================
def simplify_contour_smooth(cnt, area):
    epsilon = np.sqrt(area) * 0.01
    return cv2.approxPolyDP(cnt, epsilon, True)

# ============================================================
# MAIN PIPELINE
# ============================================================
def _img_array_to_svg(
    img,
    K_MIN=3,
    K_MAX=15,
    CLUSTER_SCALE=0.5,
    MIN_AREA_RATIO=0.0003,
    smooth=False
):
    
    if smooth:
        return img_to_svg_smoothed(img)

    else:

        h, w = img.shape[:2]
        image_area = h * w

        img = denoise_bilateral(
            img,
            sigma_color=0.03,
            sigma_spatial=2,
            channel_axis=2
        )
        img = (img * 255).astype(np.uint8)

        lab = cv2.cvtColor(img, cv2.COLOR_RGB2LAB)
        k = estimate_k_clusters(lab, K_MIN, K_MAX, CLUSTER_SCALE)

        Z = lab.reshape((-1, 3)).astype(np.float32)
        _, labels, _ = cv2.kmeans(
            Z, k, None,
            (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 50, 1.0),
            5, cv2.KMEANS_PP_CENTERS
        )
        labels = labels.reshape((h, w))

        min_pixels = max(40, int(image_area * MIN_AREA_RATIO))
        shapes = []

        for lbl in range(k):
            mask = (labels == lbl).astype(np.uint8)
            if mask.sum() < min_pixels:
                continue

            num_cc, cc_labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)

            for cc in range(1, num_cc):
                area = stats[cc, cv2.CC_STAT_AREA]
                if area < min_pixels:
                    continue

                x, y, w0, h0 = stats[cc, :4]
                submask = (cc_labels[y:y+h0, x:x+w0] == cc).astype(np.uint8)

                # 🔴 CRITICAL FIX: make region solid
                submask = fill_holes(submask)

                contours, _ = cv2.findContours(
                    submask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE
                )

                if not contours:
                    continue

                cnt = max(contours, key=cv2.contourArea)
                cnt = simplify_contour(cnt, area)
                cnt += np.array([[x, y]])

                color = img[labels == lbl].mean(axis=0).astype(int)
                shapes.append((area, cnt, color))

        shapes.sort(key=lambda s: -s[0])
        
        buffer = StringIO()
        dwg = svgwrite.Drawing(buffer, size=(w, h), profile="full")

        for i, (_, cnt, color) in enumerate(shapes):
            g = dwg.g(id=f"layer_{i}", class_="svg-layer")
            g.add(dwg.path(
                d=contour_to_path(cnt),
                fill=svgwrite.rgb(*color),
                stroke="none",
                shape_rendering="crispEdges"
            ))
            dwg.add(g)
        dwg.write(buffer)
        return buffer.getvalue()
