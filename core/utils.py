import cv2
import numpy as np
import svgwrite
from skimage.restoration import denoise_bilateral
from skimage.morphology import skeletonize
from io import StringIO


def extract_regions(edge_image):
    """
    Convert closed edge map into filled regions.

    Returns
    -------
    labels
        Label image.

    masks
        List of binary masks.
    """

    h, w = edge_image.shape

    # Invert:
    # edges -> black
    # interiors -> white
    inverted = cv2.bitwise_not(edge_image)

    num_labels, labels = cv2.connectedComponents(
        inverted,
        connectivity=8
    )

    masks = []

    for label in range(1, num_labels):

        mask = np.uint8(labels == label)

        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE,
            (3, 3)
        )

        mask = cv2.dilate(
            mask,
            kernel,
            iterations=1
        )

        area = np.count_nonzero(mask)

        if area < 30:
            continue

        # Ignore regions touching image border
        ys, xs = np.where(mask)
        """
        if (
            xs.min() == 0 or
            ys.min() == 0 or
            xs.max() == w - 1 or
            ys.max() == h - 1
        ):
            continue
        """

        masks.append(mask)

    coverage = np.zeros_like(edge_image)

    for m in masks:
        coverage |= (m > 0).astype(np.uint8)

    return labels, masks


def assign_edges_to_regions(labels, masks, max_distance=2):
    """
    Assign edge pixels to neighboring regions.

    Edge pixels in `labels` have value 0 because they were
    black in the inverted edge image.

    Instead of dilating shapes, this function assigns an
    edge pixel to the closest neighboring region.

    Parameters
    ----------
    labels : ndarray
        Output from cv2.connectedComponents().

    masks : list
        Original region masks.

    max_distance : int
        Maximum distance from an edge pixel to a region.

    Returns
    -------
    render_masks : list of uint8 masks
        Masks containing the original regions plus assigned
        edge pixels.
    """

    h, w = labels.shape

    # --------------------------------------------------
    # Start with EXACT copies of original masks
    # --------------------------------------------------

    render_masks = [
        mask.copy()
        for mask in masks
    ]

    # --------------------------------------------------
    # Build mapping:
    #
    # connectedComponents label -> mask index
    # --------------------------------------------------

    label_to_shape = {}

    for shape_idx, mask in enumerate(masks):

        values = labels[mask > 0]

        if len(values) == 0:
            continue

        values = values[values > 0]

        if len(values) == 0:
            continue

        label = np.bincount(values).argmax()

        label_to_shape[label] = shape_idx

    # --------------------------------------------------
    # Edge pixels are label == 0
    # --------------------------------------------------

    edge_pixels = labels == 0

    # --------------------------------------------------
    # Find connected components of edge pixels
    #
    # We process edge segments rather than blindly
    # dilating the entire image.
    # --------------------------------------------------

    edge_uint8 = (
        edge_pixels.astype(np.uint8)
    )

    num_edges, edge_labels = cv2.connectedComponents(
        edge_uint8,
        connectivity=8
    )

    # --------------------------------------------------
    # Process each edge segment
    # --------------------------------------------------

    for edge_id in range(1, num_edges):

        edge_mask = (
            edge_labels == edge_id
        )

        area = np.count_nonzero(edge_mask)

        if area == 0:
            continue

        ys, xs = np.where(edge_mask)

        # --------------------------------------------------
        # Determine neighboring region labels.
        #
        # Look around the edge segment.
        # --------------------------------------------------

        y0 = max(0, ys.min() - max_distance)
        y1 = min(h, ys.max() + max_distance + 1)

        x0 = max(0, xs.min() - max_distance)
        x1 = min(w, xs.max() + max_distance + 1)

        nearby_labels = labels[
            y0:y1,
            x0:x1
        ]

        nearby_labels = nearby_labels[
            nearby_labels > 0
        ]

        # --------------------------------------------------
        # Which actual shapes are nearby?
        # --------------------------------------------------

        neighboring_shapes = []

        for label in np.unique(nearby_labels):

            if label in label_to_shape:

                neighboring_shapes.append(
                    label_to_shape[label]
                )

        neighboring_shapes = list(
            dict.fromkeys(neighboring_shapes)
        )

        if len(neighboring_shapes) == 0:
            continue

        # --------------------------------------------------
        # If only one shape borders this edge,
        # assign the entire edge to that shape.
        # --------------------------------------------------

        if len(neighboring_shapes) == 1:

            shape_idx = neighboring_shapes[0]

            render_masks[
                shape_idx
            ][edge_mask] = 1

            continue

        # --------------------------------------------------
        # If multiple shapes border the edge,
        # assign each edge pixel to the nearest one.
        # --------------------------------------------------

        distances = []

        for shape_idx in neighboring_shapes:

            dist = cv2.distanceTransform(
                (
                    render_masks[shape_idx] == 0
                ).astype(np.uint8),
                cv2.DIST_L2,
                5
            )

            distances.append(
                dist[ys, xs]
            )

        distances = np.stack(
            distances,
            axis=1
        )

        nearest = np.argmin(
            distances,
            axis=1
        )

        for local_idx, shape_position in enumerate(nearest):

            shape_idx = neighboring_shapes[
                shape_position
            ]
            """
            render_masks[
                shape_idx,
                # this syntax won't work for list indexing
            ] if False else None
            """
            render_masks[
                shape_idx
            ][
                ys[local_idx],
                xs[local_idx]
            ] = 1

    return render_masks


def detect_color_edges(
    img,
    blur_sigma=1.0,
    threshold=10,
    close_iterations=0
):
    """
    Detect edges using all three LAB channels.

    This is much better than grayscale Canny because
    color transitions are preserved.
    """

    # ---------------------------------------
    # RGB -> LAB
    # ---------------------------------------
    lab = cv2.cvtColor(img, cv2.COLOR_RGB2LAB)

    L = lab[:, :, 0].astype(np.float32)
    A = lab[:, :, 1].astype(np.float32)
    B = lab[:, :, 2].astype(np.float32)

    # ---------------------------------------
    # Blur each channel
    # ---------------------------------------
    L = cv2.GaussianBlur(L, (0, 0), blur_sigma)
    A = cv2.GaussianBlur(A, (0, 0), blur_sigma)
    B = cv2.GaussianBlur(B, (0, 0), blur_sigma)

    # ---------------------------------------
    # Sobel gradients
    # ---------------------------------------
    def gradient(channel):

        gx = cv2.Sobel(
            channel,
            cv2.CV_32F,
            1,
            0,
            ksize=3
        )

        gy = cv2.Sobel(
            channel,
            cv2.CV_32F,
            0,
            1,
            ksize=3
        )

        return cv2.magnitude(gx, gy)

    gL = gradient(L)
    gA = gradient(A)
    gB = gradient(B)

    # ---------------------------------------
    # Combine gradients
    # ---------------------------------------
    magnitude = np.sqrt(
        gL**2 +
        gA**2 +
        gB**2
    )

    # ---------------------------------------
    # Normalize
    # ---------------------------------------
    magnitude = cv2.normalize(
        magnitude,
        None,
        0,
        255,
        cv2.NORM_MINMAX
    ).astype(np.uint8)

    # ---------------------------------------
    # Threshold
    # ---------------------------------------
    _, edges = cv2.threshold(
        magnitude,
        threshold,
        255,
        cv2.THRESH_BINARY
    )

    # ---------------------------------------
    # Morphological closing
    # ---------------------------------------
    kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE,
        (3, 3)
    )

    edges = cv2.morphologyEx(
        edges,
        cv2.MORPH_CLOSE,
        kernel,
        iterations=close_iterations
    )

    # ---------------------------------------
    # Remove tiny blobs
    # ---------------------------------------
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
        edges,
        connectivity=8
    )

    cleaned = np.zeros_like(edges)

    for i in range(1, num_labels):

        if stats[i, cv2.CC_STAT_AREA] > 10:
            cleaned[labels == i] = 255

    return cleaned

def skeletonize_edges(edges):
    """
    Convert thick binary edges into a 1-pixel-wide skeleton.

    Parameters
    ----------
    edges : uint8
        Binary edge image (0 / 255)

    Returns
    -------
    uint8
        Skeletonized edge image (0 / 255)
    """

    binary = edges > 0

    skeleton = skeletonize(binary)

    skeleton = (skeleton.astype(np.uint8)) * 255

    return skeleton

def contour_to_svg_path(contour):
    """
    Convert an OpenCV contour directly into an SVG path.

    No simplification.
    No Bezier fitting.
    Uses the detected outline exactly as it is.
    """

    pts = contour[:, 0, :]

    # Remove duplicated closing point
    if len(pts) > 1 and np.array_equal(pts[0], pts[-1]):
        pts = pts[:-1]

    # Remove consecutive duplicates
    cleaned = [pts[0]]

    for p in pts[1:]:
        if not np.array_equal(p, cleaned[-1]):
            cleaned.append(p)

    if len(cleaned) < 3:
        return None

    path = []

    x, y = cleaned[0]
    path.append(f"M {x},{y}")

    for x, y in cleaned[1:]:
        path.append(f"L {x},{y}")

    path.append("Z")

    return " ".join(path)


def extract_shape_data(contour, image, region_mask):
    """
    Extract everything required for one detected shape.

    Parameters
    ----------
    contour : ndarray
        OpenCV contour

    image : ndarray
        RGB image

    Returns
    -------
    dict
    """

    h, w = image.shape[:2]

    # -------------------------------------------------
    # Create full-size mask
    # -------------------------------------------------

    mask = region_mask.copy()

    # -------------------------------------------------
    # SVG path using every contour point
    # -------------------------------------------------

    pts = contour[:, 0, :]

    commands = [
        f"M {pts[0,0]} {pts[0,1]}"
    ]

    for p in pts[1:]:
        commands.append(
            f"L {p[0]} {p[1]}"
        )

    commands.append("Z")

    svg_path = " ".join(commands)

    # -------------------------------------------------
    # Bounding box
    # -------------------------------------------------

    x, y, bw, bh = cv2.boundingRect(contour)

    # -------------------------------------------------
    # Coordinates of pixels inside contour
    # -------------------------------------------------

    # -------------------------------------------------
    # Coordinates of pixels belonging ONLY to this shape
    # -------------------------------------------------

    ys, xs = np.where(mask > 0)

    # -------------------------------------------------
    # Get RGB values
    # -------------------------------------------------

    rgb = image[ys, xs].astype(np.int16)

    # -------------------------------------------------
    # Remove near-white background
    # -------------------------------------------------

    background = np.all(rgb > 245, axis=1)

    foreground = ~background

    ys, xs = np.where(mask > 0)

    colors = image[ys, xs]

    # -------------------------------------------------
    # Safety check
    # -------------------------------------------------

    MIN_FOREGROUND_PIXELS = 1

    if len(colors) < MIN_FOREGROUND_PIXELS:
        return None

    # -------------------------------------------------
    # Return everything
    # -------------------------------------------------

    shape = {

        "contour": contour,

        "path": svg_path,

        "mask": mask,

        "bbox": (x, y, bw, bh),

        "x": xs,

        "y": ys,

        "colors": colors

    }

    return shape

def lab_to_rgb(lab):
    """
    Convert one LAB color (L,A,B) -> RGB tuple.
    """

    lab = np.asarray(lab, float)

    lab[0] = np.clip(lab[0], 0, 255)
    lab[1] = np.clip(lab[1], 0, 255)
    lab[2] = np.clip(lab[2], 0, 255)

    rgb = cv2.cvtColor(
        lab.reshape(1,1,3).astype(np.uint8),
        cv2.COLOR_LAB2RGB
    )[0,0]

    return tuple(rgb.astype(int))


def rgb_rmse(original_rgb, predicted_lab):
    """
    Compute RMSE in RGB space.
    """

    rgb_pred = cv2.cvtColor(

        predicted_lab.reshape(-1,1,3).astype(np.uint8),

        cv2.COLOR_LAB2RGB

    ).reshape(-1,3).astype(float)

    return np.sqrt(

        np.mean(

            (original_rgb-rgb_pred)**2

        )

    )


def fit_solid(data):

    colors = data["rgb"].astype(float)

    median_color = np.median(
        colors,
        axis=0
    )

    errors = colors - median_color

    rmse = np.sqrt(
        np.mean(
            errors ** 2
        )
    )

    return {

        "type": "solid",

        "rmse": float(rmse),

        "params": {

            "color": tuple(
                int(np.clip(x, 0, 255))
                for x in median_color
            )

        }

    }

def fit_linear(data, angle_step=5):
    """
    Fit an SVG-compatible linear gradient.

    IMPORTANT:
    The gradient direction is determined from COLOR variation,
    not from the geometric PCA direction of the shape.

    Multiple directions are tested and the direction producing
    the lowest RGB RMSE is selected.
    """

    xs = data["x"].astype(float)
    ys = data["y"].astype(float)

    colors = data["lab"].astype(float)

    pts = np.column_stack((xs, ys))

    # ---------------------------------------------------------
    # Center coordinates
    # ---------------------------------------------------------

    mean = pts.mean(axis=0)

    pts0 = pts - mean

    # ---------------------------------------------------------
    # Search possible gradient directions
    # ---------------------------------------------------------

    best_result = None

    for angle in np.arange(
        0,
        180,
        angle_step
    ):

        theta = np.radians(angle)

        direction = np.array([
            np.cos(theta),
            np.sin(theta)
        ])

        # -----------------------------------------------------
        # Project every pixel onto this direction
        # -----------------------------------------------------

        projection = pts0 @ direction

        pmin = projection.min()
        pmax = projection.max()

        if pmax - pmin < 8:
            continue

        t = (
            projection - pmin
        ) / (
            pmax - pmin
        )

        # -----------------------------------------------------
        # Fit quadratic LAB model
        # -----------------------------------------------------

        predicted = np.zeros_like(colors)

        coeffs = []

        for c in range(3):

            p = np.polyfit(
                t,
                colors[:, c],
                2
            )

            coeffs.append(p)

            predicted[:, c] = np.polyval(
                p,
                t
            )

        # -----------------------------------------------------
        # Measure REAL RGB error
        # -----------------------------------------------------

        rmse = rgb_rmse(
            data["rgb"],
            predicted
        )

        # -----------------------------------------------------
        # Keep best direction
        # -----------------------------------------------------

        if (
            best_result is None
            or rmse < best_result["rmse"]
        ):

            best_result = {

                "rmse": float(rmse),

                "direction": direction.copy(),

                "projection_min": float(pmin),

                "projection_max": float(pmax),

                "coeffs": coeffs,

                "t": t.copy()

            }

    # ---------------------------------------------------------
    # No usable gradient
    # ---------------------------------------------------------

    if best_result is None:

        return fit_solid(data)

    # ---------------------------------------------------------
    # Extract best result
    # ---------------------------------------------------------

    direction = best_result["direction"]

    pmin = best_result["projection_min"]
    pmax = best_result["projection_max"]

    coeffs = best_result["coeffs"]

    rmse = best_result["rmse"]

    # ---------------------------------------------------------
    # Actual SVG gradient endpoints
    # ---------------------------------------------------------

    start = (
        mean +
        direction * pmin
    )

    end = (
        mean +
        direction * pmax
    )

    # ---------------------------------------------------------
    # Generate gradient stops
    # ---------------------------------------------------------

    stops = []

    positions = np.linspace(
        0,
        1,
        9
    )

    for s in positions:

        lab = []

        for p in coeffs:

            value = np.polyval(
                p,
                s
            )

            lab.append(value)

        rgb = lab_to_rgb(lab)

        stops.append(
            (
                float(s),
                rgb
            )
        )

    # ---------------------------------------------------------
    # Gradient angle
    # ---------------------------------------------------------

    angle = np.degrees(
        np.arctan2(
            direction[1],
            direction[0]
        )
    )

    return {

        "type": "linear",

        "rmse": float(rmse),

        "params": {

            "start": (
                float(start[0]),
                float(start[1])
            ),

            "end": (
                float(end[0]),
                float(end[1])
            ),

            "angle": float(angle),

            "stops": stops

        }

    }

def fit_radial(data):

    xs = data["x"]
    ys = data["y"]

    colors = data["lab"]

    cx = xs.mean()
    cy = ys.mean()

    r = np.sqrt(
        (xs-cx)**2 +
        (ys-cy)**2
    )

    radius = r.max()

    if radius < 8:
        return fit_solid(data)
    elif radius > 0:
        r = r / radius

    predicted = np.zeros_like(colors)

    coeffs = []

    for c in range(3):

        p = np.polyfit(
            r,
            colors[:, c],
            2
        )

        coeffs.append(p)

        predicted[:, c] = np.polyval(
            p,
            r
        )

    rmse = rgb_rmse(
        data["rgb"],
        predicted
    )

    stops = []

    for s in np.linspace(0, 1, 5):

        lab = []

        for p in coeffs:

            lab.append(
                np.polyval(
                    p,
                    s
                )
            )

        stops.append(

            (

                float(s),

                lab_to_rgb(lab)

            )

        )

    return {

        "type": "radial",

        "rmse": float(rmse),

        "params": {

            "center": (
                float(cx),
                float(cy)
            ),

            "radius": float(radius),

            "stops": stops

        }

    }

def fit_bilinear(data):

    xs = data["x"]
    ys = data["y"]

    colors = data["lab"]

    x = (xs - xs.min())

    if x.max() > 0:
        x /= x.max()

    y = (ys - ys.min())

    if y.max() > 0:
        y /= y.max()

    A = np.column_stack((

        np.ones_like(x),

        x,

        y,

        x*y,

        x*x,

        y*y

    ))

    predicted = np.zeros_like(colors)

    coeffs = []

    for c in range(3):

        coef, *_ = np.linalg.lstsq(
            A,
            colors[:, c],
            rcond=None
        )

        coeffs.append(coef)

        predicted[:, c] = A @ coef

    rmse = rgb_rmse(
        data["rgb"],
        predicted
    )

    return {

        "type": "bilinear",

        "rmse": float(rmse),

        "params": {

            "coefficients": coeffs

        }

    }


def prepare_fill_data(shape):
    """
    Prepare pixel data once for all fitting algorithms.
    """

    rgb = np.asarray(
        shape["colors"],
        dtype=float
    ).reshape(-1, 1, 3)

    lab = cv2.cvtColor(
        rgb.astype(np.uint8),
        cv2.COLOR_RGB2LAB
    ).reshape(-1, 3).astype(float)

    return {

        "rgb": rgb.reshape(-1, 3),

        "lab": lab,

        "x": shape["x"].astype(float),

        "y": shape["y"].astype(float),

        "bbox": shape["bbox"],

        "mask": shape["mask"]

    }


def analyze_fill(shape):

    data = prepare_fill_data(shape)

    area = len(data["x"])

    # ---------------------------------------------------------
    # Solid model
    # ---------------------------------------------------------

    solid = fit_solid(data)

    # ---------------------------------------------------------
    # Very small shapes
    # ---------------------------------------------------------

    if area < 50:

        return {
            "best": solid,
            "candidates": {
                "solid": solid
            }
        }

    # ---------------------------------------------------------
    # Linear gradient
    # ---------------------------------------------------------

    linear = fit_linear(
        data,
        # num_stops=12
    )

    # ---------------------------------------------------------
    # Radial gradient
    # ---------------------------------------------------------

    radial = fit_radial(data)

    # ---------------------------------------------------------
    # Bilinear
    #
    # Keep calculating it for comparison, but DO NOT let it
    # silently become a solid fill later.
    # ---------------------------------------------------------

    if area >= 300:

        bilinear = fit_bilinear(data)

    else:

        bilinear = {
            "type": "bilinear",
            "rmse": 1e9,
            "params": {}
        }

    candidates = {

        "solid": solid,

        "linear": linear,

        "radial": radial,

        "bilinear": bilinear

    }

    # ---------------------------------------------------------
    # Determine whether the shape actually contains
    # meaningful color variation.
    # ---------------------------------------------------------

    solid_rmse = solid["rmse"]

    best = solid

    # ---------------------------------------------------------
    # Linear gradient
    # ---------------------------------------------------------

    if linear["rmse"] < solid_rmse * 0.90:

        best = linear

    # ---------------------------------------------------------
    # Radial gradient
    # ---------------------------------------------------------

    if radial["rmse"] < best["rmse"]:

        # Require meaningful improvement over solid
        if radial["rmse"] < solid_rmse * 0.90:

            best = radial

    # ---------------------------------------------------------
    # Bilinear
    #
    # For now, don't use it as an SVG fill because SVG 1.1
    # does not provide a native bilinear/mesh gradient.
    #
    # We keep it as a candidate for diagnostics.
    # ---------------------------------------------------------

    return {

        "best": best,

        "candidates": candidates

    }


def rgb_to_svg(rgb):
    return svgwrite.rgb(
        int(rgb[0]),
        int(rgb[1]),
        int(rgb[2])
    )


def create_svg_fill(dwg, fill_result):
    """
    Parameters
    ----------
    dwg : svgwrite.Drawing

    fill_result :
        output of analyze_fill()["best"]

    Returns
    -------
    SVG fill object that can be passed directly to
    fill=
    """

    fill_type = fill_result["type"]
    params = fill_result["params"]

    ##########################################################
    # SOLID
    ##########################################################

    if fill_type == "solid":

        c = params["color"]

        return rgb_to_svg(c)

    ##########################################################
    # LINEAR
    ##########################################################

    elif fill_type == "linear":

        x1, y1 = params["start"]
        x2, y2 = params["end"]

        grad = dwg.linearGradient(
            start=(float(x1), float(y1)),
            end=(float(x2), float(y2)),
            gradientUnits="userSpaceOnUse"
        )

        for offset, color in params["stops"]:

            grad.add_stop_color(
                offset=float(offset),
                color=rgb_to_svg(color)
            )

        dwg.defs.add(grad)

        return grad.get_paint_server()

    ##########################################################
    # RADIAL
    ##########################################################

    elif fill_type == "radial":

        cx, cy = params["center"]
        r = params["radius"]

        grad = dwg.radialGradient(
            center=(float(cx), float(cy)),
            r=float(r),
            gradientUnits="userSpaceOnUse"
        )

        for offset, color in params["stops"]:

            grad.add_stop_color(
                offset=float(offset),
                color=rgb_to_svg(color)
            )

        dwg.defs.add(grad)

        return grad.get_paint_server()

    ##########################################################
    # BILINEAR
    ##########################################################

    else:

        # SVG 1.1 has no mesh gradients.
        # For now just render the average color.

        coeffs = params["coefficients"]

        x = 0.5
        y = 0.5

        A = np.array([
            1,
            x,
            y,
            x*y,
            x*x,
            y*y
        ])

        lab = [
            float(A @ coeffs[0]),
            float(A @ coeffs[1]),
            float(A @ coeffs[2])
        ]

        rgb = lab_to_rgb(lab)

        return rgb_to_svg(rgb)


def fit_cubic_bezier(points):
    """
    Fit a single cubic Bezier curve to an ordered sequence of
    contour points.

    The first and last points are treated as fixed anchors.

    Returns
    -------
    p0, p1, p2, p3
        Cubic Bezier control points.
    """

    points = np.asarray(points, dtype=float)

    if len(points) < 4:
        return None

    p0 = points[0]
    p3 = points[-1]

    # ---------------------------------------------------------
    # Parameterize original contour points by cumulative
    # distance along the contour.
    # ---------------------------------------------------------

    distances = np.linalg.norm(
        np.diff(points, axis=0),
        axis=1
    )

    cumulative = np.concatenate([
        [0],
        np.cumsum(distances)
    ])

    total_length = cumulative[-1]

    if total_length <= 0:
        return None

    t = cumulative / total_length

    # ---------------------------------------------------------
    # Cubic Bezier basis functions
    # ---------------------------------------------------------

    B0 = (1 - t) ** 3
    B1 = 3 * (1 - t) ** 2 * t
    B2 = 3 * (1 - t) * t ** 2
    B3 = t ** 3

    # ---------------------------------------------------------
    # We know p0 and p3.
    #
    # Solve for p1 and p2.
    # ---------------------------------------------------------

    rhs = (
        points
        - B0[:, None] * p0
        - B3[:, None] * p3
    )

    A = np.column_stack([
        B1,
        B2
    ])

    # Solve independently for X and Y.
    control_1 = []
    control_2 = []

    for dimension in range(2):

        solution, _, _, _ = np.linalg.lstsq(
            A,
            rhs[:, dimension],
            rcond=None
        )

        control_1.append(solution[0])
        control_2.append(solution[1])

    p1 = np.asarray(control_1)
    p2 = np.asarray(control_2)

    return p0, p1, p2, p3

def bezier_points(p0, p1, p2, p3, n=100):

    t = np.linspace(0, 1, n)

    points = (
        ((1 - t) ** 3)[:, None] * p0
        + (3 * (1 - t) ** 2 * t)[:, None] * p1
        + (3 * (1 - t) * t ** 2)[:, None] * p2
        + (t ** 3)[:, None] * p3
    )

    return points

def bezier_fit_error(
    original_points,
    p0,
    p1,
    p2,
    p3
):

    curve = bezier_points(
        p0,
        p1,
        p2,
        p3,
        n=max(100, len(original_points))
    )

    original = np.asarray(
        original_points,
        dtype=float
    )

    # For every original contour point,
    # find the closest point on the generated curve.

    distances = np.linalg.norm(
        original[:, None, :] -
        curve[None, :, :],
        axis=2
    )

    min_distances = distances.min(axis=1)

    return {
        "max_error": float(
            min_distances.max()
        ),

        "mean_error": float(
            min_distances.mean()
        ),

        "rmse": float(
            np.sqrt(
                np.mean(
                    min_distances ** 2
                )
            )
        )
    }

def fit_bezier_recursive(
    points,
    max_error=1.0,
    min_points=8,
    depth=0,
    max_depth=10
):
    """
    Represent an original contour section using the minimum
    number of cubic Bezier segments necessary to stay close
    to the original contour.

    The original contour is never simplified.

    If one cubic cannot represent the section accurately enough,
    the section is recursively divided.

    Returns
    -------
    list of dict
        Each dictionary contains:
            p0
            p1
            p2
            p3
            error
    """

    points = np.asarray(
        points,
        dtype=float
    )

    # ---------------------------------------------------------
    # Too few points
    # ---------------------------------------------------------

    if len(points) < 4:

        return None

    # ---------------------------------------------------------
    # Try ONE cubic first
    # ---------------------------------------------------------

    result = fit_cubic_bezier(points)

    if result is None:

        return None

    p0, p1, p2, p3 = result

    error = bezier_deformation_error(
        points,
        p0,
        p1,
        p2,
        p3
    )

    # ---------------------------------------------------------
    # If the cubic is good enough, STOP.
    #
    # This is the important part:
    #
    # A smooth region may become ONE cubic even if it contains
    # hundreds of original contour pixels.
    # ---------------------------------------------------------

    safe_controls = bezier_control_point_safety(
        p0,
        p1,
        p2,
        p3,
        max_handle_ratio=0.75
    )

    curve_is_safe = (
        safe_controls
        and
        error["max_error"] <= max_error
    )

    if curve_is_safe:

        return [{
            "p0": p0,
            "p1": p1,
            "p2": p2,
            "p3": p3,
            "error": error
        }]

    # ---------------------------------------------------------
    # Cubic wasn't accurate enough.
    #
    # Find the point where the error is greatest.
    # ---------------------------------------------------------

    curve = bezier_points(
        p0,
        p1,
        p2,
        p3,
        n=max(100, len(points))
    )

    distances = np.linalg.norm(
        points[:, None, :] -
        curve[None, :, :],
        axis=2
    )

    nearest_distances = distances.min(axis=1)

    split_idx = int(
        np.argmax(nearest_distances)
    )

    # ---------------------------------------------------------
    # Prevent pathological splits
    # ---------------------------------------------------------

    if split_idx < min_points // 2:

        split_idx = len(points) // 2

    if (
        len(points) - split_idx
        < min_points // 2
    ):

        split_idx = len(points) // 2

    if split_idx <= 0 or split_idx >= len(points) - 1:

        return [{
            "p0": p0,
            "p1": p1,
            "p2": p2,
            "p3": p3,
            "error": error
        }]

    # ---------------------------------------------------------
    # IMPORTANT:
    #
    # Keep the split point in BOTH sections.
    #
    # This guarantees continuity.
    # ---------------------------------------------------------

    left_points = points[
        :split_idx + 1
    ]

    right_points = points[
        split_idx:
    ]

    # ---------------------------------------------------------
    # Recursively fit left and right
    # ---------------------------------------------------------

    left_segments = fit_bezier_recursive(
        left_points,
        max_error=max_error,
        min_points=min_points,
        depth=depth + 1,
        max_depth=max_depth
    )

    right_segments = fit_bezier_recursive(
        right_points,
        max_error=max_error,
        min_points=min_points,
        depth=depth + 1,
        max_depth=max_depth
    )

    if left_segments is None:

        return right_segments

    if right_segments is None:

        return left_segments

    return (
        left_segments +
        right_segments
    )


def can_remove_anchor(
    points,
    prev_idx,
    candidate_idx,
    next_idx,
    max_error=1.0,
    max_handle_ratio=0.75
):
    """
    Test whether candidate_idx can be removed.

    The contour between the previous and next anchors is fitted
    using ONE cubic Bezier.

    If the cubic stays within max_error of the original contour
    and the control points remain geometrically safe, the
    candidate anchor can be removed.

    Returns
    -------
    bool
        True  -> anchor can safely be removed
        False -> anchor should be kept
    """

    n = len(points)

    # ---------------------------------------------------------
    # Build the section from prev anchor -> next anchor.
    #
    # This section includes the candidate anchor.
    # ---------------------------------------------------------

    if prev_idx < next_idx:

        section = points[
            prev_idx:next_idx + 1
        ]

    else:

        # Wrap around contour
        section = np.concatenate([
            points[prev_idx:],
            points[:next_idx + 1]
        ])

    # ---------------------------------------------------------
    # Need enough points to fit a cubic
    # ---------------------------------------------------------

    if len(section) < 4:
        return True

    # ---------------------------------------------------------
    # Fit ONE cubic
    # ---------------------------------------------------------

    result = fit_cubic_bezier(section)

    if result is None:
        return False

    p0, p1, p2, p3 = result

    # ---------------------------------------------------------
    # Check deformation
    # ---------------------------------------------------------

    error = bezier_fit_error(
        section,
        p0,
        p1,
        p2,
        p3
    )

    # ---------------------------------------------------------
    # Check control point safety
    # ---------------------------------------------------------

    safe = bezier_control_point_safety(
        p0,
        p1,
        p2,
        p3,
        max_handle_ratio=max_handle_ratio
    )

    # ---------------------------------------------------------
    # Candidate can be removed only if BOTH conditions pass.
    # ---------------------------------------------------------

    return (
        safe
        and
        error["max_error"] <= max_error
    )


def simplify_anchors_by_bezier(
    contour,
    anchor_indices,
    max_error=1.0,
    max_handle_ratio=0.75,
    max_passes=20
):
    """
    Iteratively remove anchors that are not geometrically
    necessary.

    An anchor is removed only when the contour between its
    neighboring anchors can be represented by ONE cubic
    Bezier within max_error.

    Parameters
    ----------
    contour : ndarray
        OpenCV contour.

    anchor_indices : list[int]
        Existing anchor indices.

    max_error : float
        Maximum allowed contour deviation in pixels.

    max_handle_ratio : float
        Safety limit for Bezier control handles.

    max_passes : int
        Maximum number of optimization passes.

    Returns
    -------
    list[int]
        Simplified anchor indices.
    """

    points = contour[:, 0, :].astype(float)

    n = len(points)

    anchors = sorted(
        set(
            int(i)
            for i in anchor_indices
            if 0 <= int(i) < n
        )
    )

    if len(anchors) <= 2:
        return anchors

    # ---------------------------------------------------------
    # Iteratively try removing anchors.
    # ---------------------------------------------------------

    for pass_number in range(max_passes):

        changed = False

        # -----------------------------------------------------
        # We don't want to modify the list while iterating over
        # it, so make a snapshot.
        # -----------------------------------------------------

        current = anchors.copy()

        # -----------------------------------------------------
        # Evaluate every anchor.
        #
        # We prefer removing anchors that have weaker curvature
        # first.
        # -----------------------------------------------------

        candidates = []

        for i, idx in enumerate(current):

            if len(current) <= 2:
                break

            prev_idx = current[
                (i - 1) % len(current)
            ]

            next_idx = current[
                (i + 1) % len(current)
            ]

            # -------------------------------------------------
            # Calculate local turning angle.
            #
            # Smaller angle change = more likely to be
            # redundant.
            # -------------------------------------------------

            v1 = points[idx] - points[prev_idx]
            v2 = points[next_idx] - points[idx]

            norm1 = np.linalg.norm(v1)
            norm2 = np.linalg.norm(v2)

            if norm1 < 1e-8 or norm2 < 1e-8:

                curvature_strength = 0.0

            else:

                v1 = v1 / norm1
                v2 = v2 / norm2

                dot = np.clip(
                    np.dot(v1, v2),
                    -1.0,
                    1.0
                )

                angle = np.degrees(
                    np.arccos(dot)
                )

                curvature_strength = abs(
                    180.0 - angle
                )

            candidates.append(
                (
                    curvature_strength,
                    i,
                    idx
                )
            )

        # -----------------------------------------------------
        # Test weakest curvature anchors first.
        # -----------------------------------------------------

        candidates.sort(
            key=lambda x: x[0]
        )

        # -----------------------------------------------------
        # Try removing anchors.
        # -----------------------------------------------------

        for _, position, idx in candidates:

            if idx not in anchors:
                continue

            if len(anchors) <= 2:
                break

            position = anchors.index(idx)

            prev_idx = anchors[
                (position - 1) % len(anchors)
            ]

            next_idx = anchors[
                (position + 1) % len(anchors)
            ]

            # -------------------------------------------------
            # Ask the important question:
            #
            # Can previous -> next be represented by ONE cubic?
            # -------------------------------------------------

            removable = can_remove_anchor(
                points,
                prev_idx,
                idx,
                next_idx,
                max_error=max_error,
                max_handle_ratio=max_handle_ratio
            )

            if removable:

                anchors.remove(idx)

                changed = True

        # -----------------------------------------------------
        # Stop if this pass didn't remove anything.
        # -----------------------------------------------------

        if not changed:
            break

    return sorted(anchors)


def calculate_safe_bezier_handles(
    contour,
    anchor_indices,
    handle_scale=0.20,
    max_handle_ratio=0.25
):
    """
    Calculate Bézier handles from the ORIGINAL contour.

    The tangent direction comes from actual contour points,
    rather than from the line between distant anchors.

    Handles are clamped to prevent overshooting/dips.
    """

    pts = contour[:, 0, :].astype(float)

    n = len(pts)

    handles = []

    for i, idx in enumerate(anchor_indices):

        prev_anchor = anchor_indices[i - 1]
        next_anchor = anchor_indices[
            (i + 1) % len(anchor_indices)
        ]

        # --------------------------------------------------
        # Local tangent from ORIGINAL contour
        # --------------------------------------------------

        local_radius = min(
            10,
            max(
                3,
                (next_anchor - prev_anchor) % n // 8
            )
        )

        local_radius = int(local_radius)

        before = pts[
            (idx - local_radius) % n
        ]

        after = pts[
            (idx + local_radius) % n
        ]

        tangent = after - before

        tangent_length = np.linalg.norm(tangent)

        if tangent_length < 1e-6:

            tangent = np.array([1.0, 0.0])

        else:

            tangent /= tangent_length

        # --------------------------------------------------
        # Distance to neighboring anchors
        # --------------------------------------------------

        d_prev = np.linalg.norm(
            pts[idx] - pts[prev_anchor]
        )

        d_next = np.linalg.norm(
            pts[next_anchor] - pts[idx]
        )

        # --------------------------------------------------
        # Handle length
        # --------------------------------------------------

        h_prev = min(
            d_prev * handle_scale,
            d_prev * max_handle_ratio
        )

        h_next = min(
            d_next * handle_scale,
            d_next * max_handle_ratio
        )

        # --------------------------------------------------
        # Handles
        # --------------------------------------------------

        control_in = (
            pts[idx] -
            tangent * h_prev
        )

        control_out = (
            pts[idx] +
            tangent * h_next
        )

        handles.append(
            (
                control_in,
                control_out
            )
        )

    return handles


def reconstruct_path_from_anchors(
    contour,
    anchor_indices,
    max_error=1.0,
    min_points=8,
    max_depth=10
):

    points = contour[:, 0, :].astype(float)

    n = len(points)

    if n < 4:
        return None

    # ---------------------------------------------------------
    # Clean anchor indices
    # ---------------------------------------------------------

    anchor_indices = sorted(
        set(
            int(i)
            for i in anchor_indices
            if 0 <= int(i) < n
        )
    )

    if len(anchor_indices) < 2:

        return None

    # ---------------------------------------------------------
    # Start SVG path
    # ---------------------------------------------------------

    first = points[
        anchor_indices[0]
    ]

    path = [
        f"M {first[0]:.3f},{first[1]:.3f}"
    ]

    all_segments = []

    # ---------------------------------------------------------
    # Process every anchor-to-anchor section
    # ---------------------------------------------------------

    for i in range(
        len(anchor_indices)
    ):

        start_idx = anchor_indices[i]

        # -----------------------------------------------------
        # Last anchor wraps around to first anchor
        # -----------------------------------------------------

        if i == len(anchor_indices) - 1:

            end_idx = anchor_indices[0]

            section = np.concatenate([
                points[start_idx:],
                points[:end_idx + 1]
            ])

        else:

            end_idx = anchor_indices[i + 1]

            section = points[
                start_idx:end_idx + 1
            ]

        if len(section) < 4:

            continue

        # -----------------------------------------------------
        # Recursively fit the ORIGINAL contour
        # -----------------------------------------------------

        segments = fit_bezier_recursive(
            section,
            max_error=max_error,
            min_points=min_points,
            max_depth=max_depth
        )

        if segments is None:

            continue

        # -----------------------------------------------------
        # Add every generated Bezier segment
        # -----------------------------------------------------

        for segment in segments:

            p1 = segment["p1"]
            p2 = segment["p2"]
            p3 = segment["p3"]

            path.append(
                "C "
                f"{p1[0]:.3f},{p1[1]:.3f} "
                f"{p2[0]:.3f},{p2[1]:.3f} "
                f"{p3[0]:.3f},{p3[1]:.3f}"
            )

            all_segments.append({
                "start_anchor": start_idx,
                "end_anchor": end_idx,
                "p0": segment["p0"],
                "p1": segment["p1"],
                "p2": segment["p2"],
                "p3": segment["p3"],
                "error": segment["error"]
            })

    path.append("Z")

    return {
        "path": " ".join(path),
        "segments": all_segments,
        "anchor_indices": anchor_indices
    }


def consolidate_nearby_anchors(
    anchors,
    angles,
    n,
    min_anchor_distance=15
):
    """
    Consolidate anchors that are very close together along
    the ORIGINAL contour.

    Only the anchor list is modified.

    The original contour is NEVER modified.

    Among nearby anchors, keep the point with the strongest
    turning angle.

    This is specifically intended to prevent multiple anchors
    being placed around the same physical corner.
    """

    if len(anchors) <= 1:
        return sorted(set(anchors))

    anchors = sorted(
        set(int(i) for i in anchors)
    )

    # ---------------------------------------------------------
    # We need to handle the contour as circular.
    #
    # Example:
    #
    # [5, 10, 20, 100, 110, 230]
    #
    # and if 230 and 5 are close through the contour wrap,
    # they should also be considered one group.
    # ---------------------------------------------------------

    groups = []
    current = [anchors[0]]

    for idx in anchors[1:]:

        distance = idx - current[-1]

        if distance <= min_anchor_distance:

            current.append(idx)

        else:

            groups.append(current)
            current = [idx]

    groups.append(current)

    # ---------------------------------------------------------
    # Handle circular first/last group.
    #
    # Example:
    #
    # [5, 10] ........ [n-8, n-3]
    #
    # These are actually close because the contour wraps.
    # ---------------------------------------------------------

    if len(groups) > 1:

        first_group = groups[0]
        last_group = groups[-1]

        circular_distance = (
            first_group[0]
            + n
            - last_group[-1]
        )

        if circular_distance <= min_anchor_distance:

            merged = (
                last_group +
                first_group
            )

            groups = (
                groups[1:-1]
            )

            groups.insert(
                0,
                merged
            )

    # ---------------------------------------------------------
    # Pick ONE anchor from each group.
    #
    # Strongest curvature wins.
    # ---------------------------------------------------------

    consolidated = []

    for group in groups:

        best = max(
            group,
            key=lambda idx: angles[idx]
        )

        consolidated.append(best)

    return sorted(set(consolidated))



def bezier_deformation_error(
    original_points,
    p0,
    p1,
    p2,
    p3,
    samples=None
):
    """
    Measure geometric deviation of a Bézier curve from the
    ORIGINAL contour in both directions.

    This is effectively a bidirectional Hausdorff-style
    distance.

    Returns
    -------
    dict
        original_to_curve
        curve_to_original
        max_error
        mean_error
    """

    original = np.asarray(
        original_points,
        dtype=float
    )

    if samples is None:
        samples = max(
            200,
            len(original) * 2
        )

    curve = bezier_points(
        p0,
        p1,
        p2,
        p3,
        n=samples
    )

    # ---------------------------------------------------------
    # ORIGINAL -> BEZIER
    # ---------------------------------------------------------

    distances_original = np.linalg.norm(
        original[:, None, :] -
        curve[None, :, :],
        axis=2
    )

    original_to_curve = (
        distances_original.min(axis=1)
    )

    # ---------------------------------------------------------
    # BEZIER -> ORIGINAL
    # ---------------------------------------------------------

    distances_curve = np.linalg.norm(
        curve[:, None, :] -
        original[None, :, :],
        axis=2
    )

    curve_to_original = (
        distances_curve.min(axis=1)
    )

    return {

        "original_to_curve": float(
            original_to_curve.max()
        ),

        "curve_to_original": float(
            curve_to_original.max()
        ),

        "max_error": float(
            max(
                original_to_curve.max(),
                curve_to_original.max()
            )
        ),

        "mean_error": float(
            (
                original_to_curve.mean() +
                curve_to_original.mean()
            ) / 2
        )
    }


def bezier_control_point_safety(
    p0,
    p1,
    p2,
    p3,
    max_handle_ratio=0.75
):
    """
    Check whether Bézier control points are reasonably
    positioned relative to their endpoints.

    This is a deformation guard, not a curve classifier.
    """

    p0 = np.asarray(p0, dtype=float)
    p1 = np.asarray(p1, dtype=float)
    p2 = np.asarray(p2, dtype=float)
    p3 = np.asarray(p3, dtype=float)

    chord = np.linalg.norm(
        p3 - p0
    )

    if chord < 1e-6:
        return False

    h1 = np.linalg.norm(
        p1 - p0
    )

    h2 = np.linalg.norm(
        p2 - p3
    )

    if h1 > chord * max_handle_ratio:
        return False

    if h2 > chord * max_handle_ratio:
        return False

    return True



def detect_curve_anchors(
    contour,
    corner_threshold=35,
    min_anchor_distance=15,
    smooth_window=8,
    curve_midpoints=True
):
    """
    Detect meaningful anchor points from the ORIGINAL contour.

    The original contour is never simplified.

    Anchors are placed at:
        1. Strong corners
        2. Middle sections of long smooth curves

    Parameters
    ----------
    contour : ndarray
        OpenCV contour, shape (N, 1, 2)

    corner_threshold : float
        Minimum turning angle, in degrees, to classify
        a point as a corner.

    min_anchor_distance : int
        Minimum contour-index distance between anchors.

    smooth_window : int
        Number of original contour points used to estimate
        local tangent.

    curve_midpoints : bool
        Add midpoint anchors to long smooth sections.

    Returns
    -------
    anchors : list of int
        Indices into the ORIGINAL contour.
    """

    pts = contour[:, 0, :].astype(float)

    n = len(pts)

    if n < 6:
        return list(range(n))

    # ---------------------------------------------------------
    # Calculate turning angle at every original contour point
    # ---------------------------------------------------------

    angles = np.zeros(n)

    for i in range(n):

        p_prev = pts[(i - smooth_window) % n]
        p = pts[i]
        p_next = pts[(i + smooth_window) % n]

        v1 = p_prev - p
        v2 = p_next - p

        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)

        if norm1 < 1e-6 or norm2 < 1e-6:
            continue

        v1 /= norm1
        v2 /= norm2

        dot = np.clip(
            np.dot(v1, v2),
            -1.0,
            1.0
        )

        angle = np.degrees(
            np.arccos(dot)
        )

        # Straight line = ~180 degrees
        #
        # Convert to turning angle.
        turning_angle = 180.0 - angle

        angles[i] = turning_angle

    # ---------------------------------------------------------
    # Find corner candidates
    # ---------------------------------------------------------

    corner_candidates = np.where(
        angles >= corner_threshold
    )[0]

    # ---------------------------------------------------------
    # Group nearby corner candidates
    #
    # A single physical corner may produce many neighboring
    # high-angle pixels.
    # ---------------------------------------------------------

    groups = []

    if len(corner_candidates) > 0:

        current = [corner_candidates[0]]

        for idx in corner_candidates[1:]:

            if idx - current[-1] <= min_anchor_distance:

                current.append(idx)

            else:

                groups.append(current)
                current = [idx]

        groups.append(current)

    # ---------------------------------------------------------
    # Select strongest point from each corner group
    # ---------------------------------------------------------

    anchors = []

    for group in groups:

        best_idx = max(
            group,
            key=lambda i: angles[i]
        )

        anchors.append(best_idx)

    # ---------------------------------------------------------
    # Sort anchors around contour
    # ---------------------------------------------------------

    anchors = sorted(set(anchors))

    # ---------------------------------------------------------
    # If there are no corners, create a small number of
    # anchors around the curve.
    # ---------------------------------------------------------

    if len(anchors) == 0:

        if curve_midpoints:

            # Four anchors for a smooth closed shape.
            #
            # This is particularly useful for circles.
            anchors = [
                0,
                n // 4,
                n // 2,
                (3 * n) // 4
            ]

        else:

            anchors = [0]

        return sorted(set(anchors))

    # ---------------------------------------------------------
    # Add midpoint anchors between corners
    #
    # This is the important part for smooth curves.
    #
    # Example:
    #
    # corner -------- smooth curve -------- corner
    #
    # becomes:
    #
    # corner -------- midpoint -------- corner
    # ---------------------------------------------------------

    if curve_midpoints:

        additional = []

        sorted_anchors = sorted(anchors)

        for i in range(len(sorted_anchors)):

            a = sorted_anchors[i]

            b = sorted_anchors[
                (i + 1) % len(sorted_anchors)
            ]

            if i == len(sorted_anchors) - 1:

                distance = (
                    b + n - a
                )

                midpoint = (
                    a + distance // 2
                ) % n

            else:

                distance = b - a

                midpoint = (
                    a + distance // 2
                )

            # Only add a midpoint if the section is
            # sufficiently long.

            if distance >= min_anchor_distance * 3:

                additional.append(midpoint)

        anchors.extend(additional)

    # ---------------------------------------------------------
    # Remove anchors that are too close together
    # ---------------------------------------------------------

    anchors = consolidate_nearby_anchors(
        anchors=anchors,
        angles=angles,
        n=n,
        min_anchor_distance=min_anchor_distance
    )

    anchors = simplify_anchors_by_bezier(
        contour,
        anchors,
        max_error=5.0,
        max_handle_ratio=0.75
    )

    return anchors


def calculate_svg_bounds(vector_shapes, image_width, image_height, padding=5):
    """
    Calculate the complete bounding box of all generated SVG geometry.

    Includes:
        - original contour points
        - Bézier control points
        - Bézier anchor/end points
        - original image/background

    Returns
    -------
    min_x, min_y, max_x, max_y
    """

    min_x = 0.0
    min_y = 0.0
    max_x = float(image_width)
    max_y = float(image_height)

    for shape in vector_shapes:

        # --------------------------------------------------
        # Original contour
        # --------------------------------------------------

        contour = shape.get("contour")

        if contour is not None:

            pts = np.asarray(
                contour[:, 0, :],
                dtype=float
            )

            if len(pts) > 0:

                min_x = min(
                    min_x,
                    np.min(pts[:, 0])
                )

                min_y = min(
                    min_y,
                    np.min(pts[:, 1])
                )

                max_x = max(
                    max_x,
                    np.max(pts[:, 0])
                )

                max_y = max(
                    max_y,
                    np.max(pts[:, 1])
                )

        # --------------------------------------------------
        # Bézier segments
        # --------------------------------------------------

        segments = shape.get("segments", [])

        for segment in segments:

            for key in (
                "p0",
                "p1",
                "p2",
                "p3"
            ):

                point = segment.get(key)

                if point is None:
                    continue

                point = np.asarray(
                    point,
                    dtype=float
                )

                if len(point) != 2:
                    continue

                min_x = min(
                    min_x,
                    point[0]
                )

                min_y = min(
                    min_y,
                    point[1]
                )

                max_x = max(
                    max_x,
                    point[0]
                )

                max_y = max(
                    max_y,
                    point[1]
                )

    # ------------------------------------------------------
    # Padding
    # ------------------------------------------------------

    min_x -= padding
    min_y -= padding
    max_x += padding
    max_y += padding

    return (
        min_x,
        min_y,
        max_x,
        max_y
    )

# ============================================================
# MAIN PIPELINE
# ============================================================
def _img_array_to_svg(
    img,
    edge_detection_threshold=10,
    min_anchor_distance=15,
):
    
    edges = detect_color_edges(
        img,
        blur_sigma=1.0,
        threshold=edge_detection_threshold,
    )

    # contours = find_closed_contours(edges, min_area=30)

    labels, masks = extract_regions(edges)

    edges = skeletonize_edges(edges)

    render_masks = assign_edges_to_regions(
        labels,
        masks,
        max_distance=2
    )

    # =====================================================
    # DEBUG COVERAGE
    # =====================================================

    coverage = np.zeros_like(edges)

    for mask in render_masks:

        coverage |= (
            mask > 0
        ).astype(np.uint8)

    # =====================================================
    # CREATE SHAPES
    # =====================================================

    shapes = []

    for shape_idx, (original_mask, render_mask) in enumerate(
        zip(masks, render_masks)
    ):

        # ==========================================================
        # 1. Extract contour from RENDER mask
        #
        # render_mask contains:
        #   - original region
        #   - assigned edge pixels
        #
        # This gives us the visible boundary we actually want to trace.
        # ==========================================================

        contours, _ = cv2.findContours(
            render_mask.astype(np.uint8),
            cv2.RETR_TREE,
            cv2.CHAIN_APPROX_NONE
        )

        if len(contours) == 0:
            print("No contour found.")
            continue

        # ----------------------------------------------------------
        # Use largest contour
        # ----------------------------------------------------------

        contour = max(
            contours,
            key=cv2.contourArea
        )

        original_point_count = len(contour)

        if original_point_count < 4:
            print("Contour too small.")
            continue

        # ==========================================================
        # 2. Detect meaningful anchor positions
        #
        # IMPORTANT:
        # These indices refer to the ORIGINAL contour.
        #
        # We are NOT simplifying the contour here.
        # ==========================================================

        anchor_indices = detect_curve_anchors(
            contour,

            corner_threshold=35,

            min_anchor_distance=min_anchor_distance,

            smooth_window=8,

            curve_midpoints=True
        )

        path_result = reconstruct_path_from_anchors(
            contour,
            anchor_indices,

            # Lower = more accurate
            max_error=1.0,

            # Prevent very tiny curve segments
            min_points=8,

            # Maximum recursive splitting
            max_depth=10
        )

        if path_result is None:
            continue

        simplified_path = path_result["path"]

        bezier_segments = path_result["segments"]

        # ==========================================================
        # 5. Extract shape information
        #
        # IMPORTANT:
        # extract_shape_data() still receives the ORIGINAL contour.
        #
        # Therefore:
        #   - bbox remains correct
        #   - mask remains correct
        #   - original pixels remain correct
        #   - gradient analysis remains based on original pixels
        # ==========================================================

        shape = extract_shape_data(
            contour,
            img,
            original_mask
        )

        if shape is None:
            print("Shape extraction failed.")
            continue

        # ==========================================================
        # 6. Analyze fill using ORIGINAL pixels
        # ==========================================================

        shape["fill"] = analyze_fill(shape)

        # ==========================================================
        # 7. Store render mask
        # ==========================================================

        shape["render_mask"] = render_mask

        # ==========================================================
        # 8. Store anchor information
        # ==========================================================

        shape["anchor_indices"] = anchor_indices

        # ==========================================================
        # 9. Store reconstructed SVG path
        # ==========================================================

        shape["simplified_path"] = simplified_path

        # ==========================================================
        # 10. Store Bézier segment information
        #
        # This is useful later when creating the DWG.
        # ==========================================================

        shape["bezier_segments"] = bezier_segments

        # ==========================================================
        # 11. Store original point count
        # ==========================================================

        shape["original_point_count"] = original_point_count

        # ==========================================================
        # 12. Store number of generated Bézier segments
        # ==========================================================

        shape["bezier_segment_count"] = len(
            bezier_segments
        )

        # ==========================================================
        # 13. Add to shapes
        # ==========================================================

        shapes.append(shape)

    h, w = img.shape[:2]

    min_x, min_y, max_x, max_y = calculate_svg_bounds(
        shapes,
        image_width=w,
        image_height=h,
        padding=5
    )

    svg_width = max_x - min_x
    svg_height = max_y - min_y
        
    buffer = StringIO()

    dwg = svgwrite.Drawing(
        buffer,
        size=(
            f"{svg_width}px",
            f"{svg_height}px"
        ),
        profile="full",
        viewBox=(
            f"{min_x} {min_y} "
            f"{svg_width} {svg_height}"
        )
    )

    i = 1

    for shape in shapes:

        g = dwg.g(
            id=f"layer_{i}",
            class_="svg-layer"
        )

        # r, g, b = color
        fill = create_svg_fill(
            dwg,
            shape["fill"]["best"]
        )

        g.add(
            dwg.path(
                d=shape["simplified_path"],
                fill=fill,
                stroke=fill,
                stroke_width=2,
                stroke_linejoin="round",
                stroke_linecap="round"
            )
        )

        dwg.add(g)

        i += 1
    dwg.write(buffer)
    return buffer.getvalue()
