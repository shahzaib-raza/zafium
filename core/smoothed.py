import cv2
import numpy as np
import svgwrite
from skimage.restoration import denoise_bilateral
from io import StringIO


def estimate_k_clusters(lab_img, k_min, k_max, CLUSTER_SCALE):
    # Downsample for speed
    small = cv2.resize(
        lab_img,
        None,
        fx=CLUSTER_SCALE,
        fy=CLUSTER_SCALE,
        interpolation=cv2.INTER_AREA
    )
    Z = small.reshape((-1, 3)).astype(np.float32)

    distortions = []

    for k in range(k_min, k_max + 1):
        _, _, centers = cv2.kmeans(
            Z,
            k,
            None,
            (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 1.0),
            3,
            cv2.KMEANS_PP_CENTERS
        )
        diff = Z[:, None, :] - centers[None, :, :]
        dist = np.min(np.sum(diff ** 2, axis=2), axis=1)
        distortions.append(dist.mean())

    distortions = np.array(distortions)
    curvature = np.diff(distortions, 2)
    best_k = np.argmin(curvature) + k_min + 1

    return int(np.clip(best_k, k_min, k_max))


def img_to_svg_smoothed(img):

    # Clustering limits
    K_MIN = 3
    K_MAX = 15

    # Relative minimum shape size (percentage of image area)
    MIN_AREA_RATIO = 0.0003   # 0.03%

    # Downscale factor for clustering only (speed)
    CLUSTER_SCALE = 0.5

    # ============================================================
    # LOAD IMAGE
    # ============================================================
    
    h, w = img.shape[:2]
    image_area = h * w

    # ============================================================
    # EDGE-PRESERVING DENOISE (ANTI-ALIASING CONTROL)
    # ============================================================
    img = denoise_bilateral(
        img,
        sigma_color=0.05,
        sigma_spatial=3,
        channel_axis=2
    )
    img = (img * 255).astype(np.uint8)

    # ============================================================
    # COLOR SPACE
    # ============================================================
    lab = cv2.cvtColor(img, cv2.COLOR_RGB2LAB)

    # ============================================================
    # AUTO-DETECT NUMBER OF COLOR CLUSTERS (FAST ELBOW)
    # ============================================================

    K_CLUSTERS = estimate_k_clusters(lab, K_MIN, K_MAX, CLUSTER_SCALE)

    # ============================================================
    # K-MEANS COLOR SEGMENTATION (FULL RES, SINGLE PASS)
    # ============================================================
    Z = lab.reshape((-1, 3)).astype(np.float32)

    _, labels, _ = cv2.kmeans(
        Z,
        K_CLUSTERS,
        None,
        (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 50, 1.0),
        5,
        cv2.KMEANS_PP_CENTERS
    )

    labels = labels.reshape((h, w))

    # ============================================================
    # DYNAMIC MIN AREA THRESHOLD
    # ============================================================
    MIN_PIXELS = max(20, int(image_area * MIN_AREA_RATIO))

    # ============================================================
    # COLLECT SHAPES (FAST PATH)
    # ============================================================
    shapes = []

    for k in range(K_CLUSTERS):
        color_mask = (labels == k).astype(np.uint8)

        num_cc, cc_labels, stats, _ = cv2.connectedComponentsWithStats(
            color_mask, connectivity=8
        )

        for cc in range(1, num_cc):
            area = stats[cc, cv2.CC_STAT_AREA]
            if area < MIN_PIXELS:
                continue

            x = stats[cc, cv2.CC_STAT_LEFT]
            y = stats[cc, cv2.CC_STAT_TOP]
            w0 = stats[cc, cv2.CC_STAT_WIDTH]
            h0 = stats[cc, cv2.CC_STAT_HEIGHT]

            submask = (cc_labels[y:y+h0, x:x+w0] == cc).astype(np.uint8)

            contours, _ = cv2.findContours(
                submask,
                cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_SIMPLE
            )

            if not contours:
                continue

            # Mean color (localized, fast)
            roi = img[y:y+h0, x:x+w0]
            mean_color = roi[submask.astype(bool)].mean(axis=0).astype(int)

            # Offset contours back to image coordinates
            contours = [cnt + np.array([[x, y]]) for cnt in contours]

            shapes.append({
                "area": area,
                "contours": contours,
                "color": mean_color
            })

    # ============================================================
    # SORT SHAPES BY AREA (BACK → FRONT)
    # ============================================================
    shapes.sort(key=lambda s: s["area"], reverse=True)

    # ============================================================
    # WRITE SVG (DOCUMENT ORDER = Z-ORDER)
    # ============================================================
    buffer = StringIO()
    dwg = svgwrite.Drawing(
        buffer,
        size=(w, h),
        profile="full"
    )

    for idx, shape in enumerate(shapes):
        group = dwg.g(id=f"layer_{idx}", class_="svg-layer")

        fill = svgwrite.rgb(
            int(shape["color"][0]),
            int(shape["color"][1]),
            int(shape["color"][2])
        )

        for cnt in shape["contours"]:
            if cnt.shape[0] < 3:
                continue

            pts = cnt.squeeze()
            d = "M " + " ".join(f"{x},{y}" for x, y in pts) + " Z"

            group.add(
                dwg.path(
                    d=d,
                    fill=fill,
                    stroke="none"
                )
            )

        dwg.add(group)

    dwg.write(buffer)
    return buffer.getvalue()


