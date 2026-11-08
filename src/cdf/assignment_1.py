import math
import Rhino.Geometry as rg
import rhinoscriptsyntax as rs
import random
from System.Drawing import Color


GOLDEN_RATIO = (1.0 + 5.0 ** 0.5) / 2.0


def create_intersecting_boards(
    base_point=None,
    board_length=50.0,
    board_thickness=2.0,
    first_intersection=0.5,
    second_intersection=0.5,
):
    """Create two perpendicular golden-ratio boards.

    The first board lies in the YZ plane: its length runs along Y and its
    golden-ratio width runs along Z. The second board lies in the XZ plane:
    its length runs along X and has the same width along Z.

    The first board is fixed at length 50.0. The second board reads the first board as its
    coordinate system:

    ``first_intersection`` moves the second board along the first board's Y
    edge. ``second_intersection`` moves the second board vertically along the
    first board's Z height. Both values are normalized from 0.0 to 1.0.
    ``board_length`` controls only the second board's X length and is limited
    to one third smaller or larger than 50.0.
    """
    if base_point is None:
        base_point = rg.Point3d(0, 0, 0)
    elif not isinstance(base_point, rg.Point3d):
        base_point = rs.coerce3dpoint(base_point)
        if base_point is None:
            raise TypeError("base_point must be a Point3d or point reference.")

    first_length = 50.0
    board_length = _snap_board_length(board_length, first_length)
    if board_thickness <= 0.0:
        raise ValueError("board_thickness must be positive.")
    first_intersection = _snap_intersection(first_intersection)
    if not 0.25 <= second_intersection <= 0.75:
        raise ValueError(
            "second_intersection must be between 0.25 and 0.75."
        )

    first_width = first_length / GOLDEN_RATIO
    second_width = board_length / GOLDEN_RATIO
    x0 = base_point.X
    y0 = base_point.Y
    z0 = base_point.Z

    # The first board is fixed in place and extends along Y and Z.
    first_board = _make_box(
        rg.Point3d(x0, y0, z0 + first_width / 2.0),
        board_thickness,
        first_length,
        first_width,
    )

    # The second board extends along X and Z, but its position is defined by
    # coordinates read from the fixed first board.
    second_y = y0 - first_length / 2.0 + first_intersection * first_length
    second_z = z0 + second_intersection * first_width
    second_board = _make_box(
        rg.Point3d(x0, second_y, second_z + second_width / 2.0),
        board_length,
        board_thickness,
        second_width,
    )

    return [first_board, second_board]


def create_additional_panels(
    existing_boards=None,
    panel_thickness=2.0,
    panel_length=65.0,
    panel_width=25.0,
    seed=1,
    first_board=None,
    second_board=None,
    minimum_clearance=0.0,
    minimum_panel_clearance=0.0,
    minimum_target_edge_clearance=0.0,
    placement_area_scale=2.0,
):
    """Create exactly four panels that intersect the two existing boards.

    Two new panels intersect each base board. Each new panel changes axis
    relative to its target board: panels
    attached to the YZ board use XY and XZ, while panels attached to the XZ
    board use XY and YZ.
    """
    if first_board is not None or second_board is not None:
        boards = _coerce_breps(first_board) + _coerce_breps(second_board)
    else:
        boards = _coerce_breps(existing_boards)
    if len(boards) < 2:
        raise ValueError("existing_boards must contain two boards.")
    if panel_thickness <= 0.0 or panel_length <= 0.0 or panel_width <= 0.0:
        raise ValueError("Panel dimensions must be positive.")
    if minimum_clearance < 0.0:
        raise ValueError("minimum_clearance cannot be negative.")
    if minimum_panel_clearance < 0.0:
        raise ValueError("minimum_panel_clearance cannot be negative.")
    if minimum_target_edge_clearance < 0.0:
        raise ValueError("minimum_target_edge_clearance cannot be negative.")
    if placement_area_scale < 1.0:
        raise ValueError("placement_area_scale must be at least 1.0.")

    rng = random.Random(seed)
    targets = [0, 0, 1, 1]
    rng.shuffle(targets)
    orientation_sequences = {
        0: ["xy", "xz"],
        1: ["xy", "yz"],
    }
    orientation_indices = {0: 0, 1: 0}
    orientations = []
    for target_index in targets:
        orientation = orientation_sequences[target_index][
            orientation_indices[target_index]
        ]
        orientations.append(orientation)
        orientation_indices[target_index] += 1
    result = []
    attempts = 0

    while len(result) < 4 and attempts < 10000:
        attempts += 1
        panel_index = len(result)
        target_index = targets[panel_index]
        orientation = orientations[panel_index]
        target_box = boards[target_index].GetBoundingBox(True)
        other_index = 1 - target_index
        center = target_box.Center
        target_slot = targets[:panel_index].count(target_index)
        length = panel_length * rng.uniform(0.75, 1.75)
        width = min(
            panel_width * rng.uniform(0.75, 1.75),
            max(target_box.Diagonal.Length, panel_width),
        )
        height = panel_width * rng.uniform(0.75, 1.75)
        z_center = _separated_z_coordinate(
            target_box,
            height,
            target_slot,
            rng,
        )

        if orientation == "xy":
            dimensions = (length, width, panel_thickness)
            center = rg.Point3d(
                center.X + rng.uniform(
                    -width * placement_area_scale,
                    width * placement_area_scale,
                ),
                center.Y + rng.uniform(
                    -width * placement_area_scale,
                    width * placement_area_scale,
                ),
                center.Z + rng.uniform(-height, height),
            )
        elif orientation == "xz":
            dimensions = (length, panel_thickness, height)
            center = rg.Point3d(
                center.X + rng.uniform(
                    -width * placement_area_scale,
                    width * placement_area_scale,
                ),
                _separated_target_coordinate(
                    target_box.Min.Y,
                    target_box.Max.Y,
                    target_slot,
                    rng,
                ),
                z_center,
            )
        else:
            dimensions = (panel_thickness, length, height)
            center = rg.Point3d(
                _separated_target_coordinate(
                    target_box.Min.X,
                    target_box.Max.X,
                    target_slot,
                    rng,
                ),
                center.Y + rng.uniform(
                    -width * placement_area_scale,
                    width * placement_area_scale,
                ),
                z_center,
            )

        candidate = _make_box(
            center,
            dimensions[0],
            dimensions[1],
            dimensions[2],
        )
        if candidate.GetBoundingBox(True).Min.Z < -1e-6:
            continue
        if not _positive_bbox_overlap(candidate, boards[target_index]):
            continue
        if not _intersects_inside_target(
            candidate,
            boards[target_index],
            minimum_target_edge_clearance,
        ):
            continue
        if _bbox_distance(candidate, boards[other_index]) < minimum_clearance:
            continue
        if any(
            _bbox_distance(candidate, panel) < minimum_panel_clearance
            for panel in result
        ):
            continue
        result.append(candidate)

    if len(result) != 4:
        raise RuntimeError(
            "Could not place four non-intersecting additional panels. "
            "Increase placement_area_scale or reduce panel dimensions."
        )
    return result


def _separated_target_coordinate(target_min, target_max, slot, rng):
    """Choose one of two interior anchors on the target board."""
    interior_min = target_min + 10.0
    interior_max = target_max - 10.0
    if interior_min >= interior_max:
        return (target_min + target_max) / 2.0
    midpoint = (interior_min + interior_max) / 2.0
    span = (interior_max - interior_min) * 0.3
    anchor = midpoint - span if slot == 0 else midpoint + span
    return anchor + rng.uniform(-span * 0.15, span * 0.15)


def _separated_z_coordinate(target_box, panel_height, slot, rng):
    """Choose ground-safe lower/upper bands that still overlap the board."""
    board_min = target_box.Min.Z
    board_max = target_box.Max.Z
    minimum_center = max(panel_height / 2.0, board_min)
    lower_center = max(
        minimum_center,
        board_min + min(panel_height * 0.35, (board_max - board_min) * 0.35),
    )
    upper_center = max(
        lower_center + panel_height * 0.65,
        board_max - panel_height * 0.25,
    )
    center = lower_center if slot == 0 else upper_center
    return center + rng.uniform(-1.5, 1.5)


def create_support_board(
    base_point=None,
    board_thickness=5.0,
):
    """Create one fixed 100 by 100 solid board spanning Z=-thickness to Z=0."""
    if base_point is None:
        base_point = rg.Point3d(0, 0, 0)
    elif not isinstance(base_point, rg.Point3d):
        base_point = rs.coerce3dpoint(base_point)
        if base_point is None:
            raise TypeError("base_point must be a Point3d or point reference.")
    if board_thickness <= 0.0:
        raise ValueError("board_thickness must be positive.")

    plane = rg.Plane(
        rg.Point3d(
            base_point.X,
            base_point.Y,
            -board_thickness,
        ),
        rg.Vector3d.ZAxis,
    )
    board = rg.Box(
        plane,
        rg.Interval(-50.0, 50.0),
        rg.Interval(-50.0, 50.0),
        rg.Interval(0.0, board_thickness),
    )
    return board.ToBrep()


def cut_composition(
    first_board,
    second_board,
    additional_panels=None,
    tolerance=0.01,
):
    """Keep the first board whole and Boolean-cut the rest of the composition.

    The second board is cut by the first board. Each additional panel is cut
    by both original boards so its intersections become fitted openings.
    """
    first = _coerce_breps(first_board)
    second = _coerce_breps(second_board)
    panels = _coerce_breps(additional_panels)
    if len(first) != 1 or len(second) != 1:
        raise ValueError(
            "first_board and second_board must each contain one Brep."
        )
    if tolerance <= 0.0:
        raise ValueError("tolerance must be positive.")

    first_brep = first[0]
    second_cut = _boolean_difference(
        second[0],
        [first_brep],
        tolerance,
    )
    cut_panels = []
    for panel in panels:
        cut_panels.extend(
            _boolean_difference(
                panel,
                [first_brep, second[0]],
                tolerance,
            )
        )
    return first_brep, second_cut, cut_panels


def create_colored_spheres(
    panels,
    first_board=None,
    second_board=None,
    sphere_clearance=1.0,
    sphere_scale=0.45,
):
    """Place up to three safe Bauhaus-colored spheres.

    No horizontal panel receives more than two spheres. Each sphere is
    tangent to its host panel only; all other panels, boards, and spheres are
    treated as obstacles. If fewer than three safe positions exist, the
    spheres that were safely placed are returned without raising an error.
    """
    panel_breps = _coerce_breps(panels)
    if not panel_breps:
        raise ValueError("panels must contain at least one Brep.")
    if sphere_clearance < 0.0:
        raise ValueError("sphere_clearance cannot be negative.")
    if not 0.1 <= sphere_scale <= 0.5:
        raise ValueError("sphere_scale must be between 0.1 and 0.5.")

    boards = _coerce_breps(first_board) + _coerce_breps(second_board)
    horizontal_panels = [
        (panel_index, panel)
        for panel_index, panel in enumerate(panel_breps)
        if _is_horizontal_panel(panel)
    ]
    spheres = []
    colors = []
    radii = []
    centers = []
    sphere_counts_by_panel = {}
    bauhaus_colors = (
        Color.FromArgb(0, 90, 220),
        Color.FromArgb(245, 200, 0),
    )
    target_sphere_count = 3
    used_candidates = set()

    for pass_index in range(target_sphere_count):
        placed_this_pass = False
        for panel_index, host in horizontal_panels:
            if len(spheres) >= target_sphere_count:
                break
            if sphere_counts_by_panel.get(panel_index, 0) >= 2:
                continue
            host_box = host.GetBoundingBox(True)
            host_width = host_box.Max.X - host_box.Min.X
            host_depth = host_box.Max.Y - host_box.Min.Y
            maximum_radius = min(host_width, host_depth) * sphere_scale
            if maximum_radius <= 0.0:
                continue

            candidates = _sphere_candidates(host_box, maximum_radius)
            chosen = None
            for candidate_index, (radius, x, y) in enumerate(candidates):
                candidate_key = (panel_index, candidate_index)
                if candidate_key in used_candidates:
                    continue
                used_candidates.add(candidate_key)
                center = rg.Point3d(x, y, host_box.Max.Z + radius)
                sphere = rg.Sphere(center, radius).ToBrep()
                other_obstacles = [
                    obstacle
                    for obstacle_index, obstacle in enumerate(panel_breps)
                    if obstacle_index != panel_index
                ]
                other_obstacles.extend(boards)
                if any(
                    not _sphere_is_clear_of(
                        sphere,
                        obstacle,
                        sphere_clearance,
                        center,
                        radius,
                    )
                    for obstacle in other_obstacles
                ):
                    continue
                if any(
                    _sphere_boxes_overlap(
                        center,
                        radius,
                        existing_center,
                        existing_radius,
                        sphere_clearance,
                    )
                    for existing_center, existing_radius in zip(
                        centers,
                        radii,
                    )
                ):
                    continue
                chosen = (sphere, center, radius)
                break

            if chosen is None:
                continue
            sphere, center, radius = chosen
            spheres.append(sphere)
            centers.append(center)
            radii.append(radius)
            colors.append(random.choice(bauhaus_colors))
            sphere_counts_by_panel[panel_index] = (
                sphere_counts_by_panel.get(panel_index, 0) + 1
            )
            placed_this_pass = True

        if not placed_this_pass:
            break

    return spheres, colors, radii, centers


def _is_horizontal_panel(panel):
    box = panel.GetBoundingBox(True)
    sizes = (
        box.Max.X - box.Min.X,
        box.Max.Y - box.Min.Y,
        box.Max.Z - box.Min.Z,
    )
    return sizes[2] <= min(sizes[0], sizes[1])


def _point_distance(first, second):
    return first.DistanceTo(second)


def _sphere_is_clear_of(sphere, obstacle, clearance, center, radius):
    """Return false unless the sphere has a strict gap from an obstacle."""
    obstacle_box = obstacle.GetBoundingBox(True)
    margin = max(clearance, 1e-6)
    if _expanded_bbox_overlap(
        center,
        radius + margin,
        obstacle_box,
    ):
        return False
    closest_x = min(max(center.X, obstacle_box.Min.X), obstacle_box.Max.X)
    closest_y = min(max(center.Y, obstacle_box.Min.Y), obstacle_box.Max.Y)
    closest_z = min(max(center.Z, obstacle_box.Min.Z), obstacle_box.Max.Z)
    closest = rg.Point3d(closest_x, closest_y, closest_z)
    if center.DistanceTo(closest) <= radius + margin:
        return False
    return True


def _expanded_bbox_overlap(center, radius, obstacle_box):
    """Conservative collision test for a sphere against an obstacle box."""
    return not (
        center.X + radius < obstacle_box.Min.X
        or center.X - radius > obstacle_box.Max.X
        or center.Y + radius < obstacle_box.Min.Y
        or center.Y - radius > obstacle_box.Max.Y
        or center.Z + radius < obstacle_box.Min.Z
        or center.Z - radius > obstacle_box.Max.Z
    )


def _sphere_boxes_overlap(
    first_center,
    first_radius,
    second_center,
    second_radius,
    clearance,
):
    """Return true when two clearance-expanded sphere boxes overlap."""
    margin = max(clearance, 1e-6)
    radius = first_radius + margin
    other_radius = second_radius + margin
    return not (
        first_center.X + radius < second_center.X - other_radius
        or first_center.X - radius > second_center.X + other_radius
        or first_center.Y + radius < second_center.Y - other_radius
        or first_center.Y - radius > second_center.Y + other_radius
        or first_center.Z + radius < second_center.Z - other_radius
        or first_center.Z - radius > second_center.Z + other_radius
    )


def _sphere_candidates(box, maximum_radius):
    """Try a dense set of positions, reducing radius only as a fallback."""
    center_x = (box.Min.X + box.Max.X) / 2.0
    center_y = (box.Min.Y + box.Max.Y) / 2.0
    offsets = (
        -0.8,
        -0.6,
        -0.4,
        -0.2,
        0.0,
        0.2,
        0.4,
        0.6,
        0.8,
    )
    candidates = []
    for scale in (
        1.0,
        0.9,
        0.8,
        0.7,
        0.6,
        0.5,
        0.4,
        0.3,
        0.2,
        0.1,
    ):
        radius = maximum_radius * scale
        x_span = max(0.0, (box.Max.X - box.Min.X) / 2.0 - radius)
        y_span = max(0.0, (box.Max.Y - box.Min.Y) / 2.0 - radius)
        for x_offset in offsets:
            for y_offset in offsets:
                candidates.append(
                    (
                        radius,
                        center_x + x_offset * x_span,
                        center_y + y_offset * y_span,
                    )
                )
    return candidates


def _boolean_difference(subject, cutters, tolerance):
    result = [subject]
    for cutter in cutters:
        next_result = []
        for item in result:
            difference = rg.Brep.CreateBooleanDifference(
                item,
                cutter,
                tolerance,
            )
            if not difference and _positive_bbox_overlap(item, cutter):
                difference = rg.Brep.CreateBooleanDifference(
                    item,
                    cutter,
                    max(tolerance * 0.1, 1e-6),
                )
            if difference and _same_brep_volume(item, difference):
                difference = None
            if not difference:
                if _positive_bbox_overlap(item, cutter):
                    for retry_tolerance in (
                        tolerance * 10.0,
                        max(tolerance * 0.01, 1e-6),
                    ):
                        difference = rg.Brep.CreateBooleanDifference(
                            item,
                            cutter,
                            retry_tolerance,
                        )
                        if difference and not _same_brep_volume(
                            item,
                            difference,
                        ):
                            break
                else:
                    difference = [item]
            if not difference:
                raise RuntimeError(
                    "Boolean difference failed for an intersecting "
                    "panel or board. Check Rhino tolerance and Brep validity."
                )
            if difference == [item]:
                next_result.append(item)
            else:
                next_result.extend(difference)
        result = next_result
    return result


def _same_brep_volume(subject, difference):
    """Detect a Boolean result that is only the unchanged input Brep."""
    subject_mass = rg.VolumeMassProperties.Compute(subject)
    if not subject_mass:
        return False
    result_volume = sum(
        (
            rg.VolumeMassProperties.Compute(item).Volume
            for item in difference
            if rg.VolumeMassProperties.Compute(item)
        ),
        0.0,
    )
    return abs(subject_mass.Volume - result_volume) <= 1e-6


def _positive_bbox_overlap(first, second):
    first_box = first.GetBoundingBox(True)
    second_box = second.GetBoundingBox(True)
    tolerance = 1e-6
    return (
        min(first_box.Max.X, second_box.Max.X)
        - max(first_box.Min.X, second_box.Min.X)
        > tolerance
        and min(first_box.Max.Y, second_box.Max.Y)
        - max(first_box.Min.Y, second_box.Min.Y)
        > tolerance
        and min(first_box.Max.Z, second_box.Max.Z)
        - max(first_box.Min.Z, second_box.Min.Z)
        > tolerance
    )


def _intersects_inside_target(candidate, target, edge_clearance):
    """Require a panel's cut line to be well inside the target board."""
    candidate_box = candidate.GetBoundingBox(True)
    target_box = target.GetBoundingBox(True)
    overlap_min = (
        max(candidate_box.Min.X, target_box.Min.X),
        max(candidate_box.Min.Y, target_box.Min.Y),
        max(candidate_box.Min.Z, target_box.Min.Z),
    )
    overlap_max = (
        min(candidate_box.Max.X, target_box.Max.X),
        min(candidate_box.Max.Y, target_box.Max.Y),
        min(candidate_box.Max.Z, target_box.Max.Z),
    )
    target_sizes = (
        target_box.Max.X - target_box.Min.X,
        target_box.Max.Y - target_box.Min.Y,
        target_box.Max.Z - target_box.Min.Z,
    )
    thin_axis = min(range(3), key=lambda axis: target_sizes[axis])

    for axis in range(3):
        if axis == thin_axis:
            continue
        panel_centers = (
            (candidate_box.Min.X + candidate_box.Max.X) / 2.0,
            (candidate_box.Min.Y + candidate_box.Max.Y) / 2.0,
            (candidate_box.Min.Z + candidate_box.Max.Z) / 2.0,
        )
        panel_center = panel_centers[axis]
        target_min = (target_box.Min.X, target_box.Min.Y, target_box.Min.Z)[
            axis
        ]
        target_max = (target_box.Max.X, target_box.Max.Y, target_box.Max.Z)[
            axis
        ]
        overlap_center = (overlap_min[axis] + overlap_max[axis]) / 2.0
        if (
            panel_center < target_min + edge_clearance
            or panel_center > target_max - edge_clearance
            or overlap_center < target_min + edge_clearance
            or overlap_center > target_max - edge_clearance
        ):
            return False
    return True


def _bbox_distance(first, second):
    """Return the shortest separation between two axis-aligned bounding boxes."""
    first_box = first.GetBoundingBox(True)
    second_box = second.GetBoundingBox(True)

    def axis_gap(first_min, first_max, second_min, second_max):
        if first_max < second_min:
            return second_min - first_max
        if second_max < first_min:
            return first_min - second_max
        return 0.0

    gap_x = axis_gap(
        first_box.Min.X,
        first_box.Max.X,
        second_box.Min.X,
        second_box.Max.X,
    )
    gap_y = axis_gap(
        first_box.Min.Y,
        first_box.Max.Y,
        second_box.Min.Y,
        second_box.Max.Y,
    )
    gap_z = axis_gap(
        first_box.Min.Z,
        first_box.Max.Z,
        second_box.Min.Z,
        second_box.Max.Z,
    )
    return math.sqrt(gap_x * gap_x + gap_y * gap_y + gap_z * gap_z)


def _coerce_breps(value):
    """Convert one board or a Grasshopper collection into Breps."""
    if value is None:
        return []
    if isinstance(value, rg.Brep):
        return [value]

    if hasattr(value, "Value"):
        return _coerce_breps(value.Value)

    try:
        values = list(value)
    except TypeError:
        values = [value]

    breps = []
    for item in values:
        if isinstance(item, rg.Brep) or hasattr(item, "Value"):
            breps.extend(_coerce_breps(item))
            continue
        try:
            nested_values = list(item)
        except TypeError:
            nested_values = None
        if nested_values is not None:
            breps.extend(_coerce_breps(nested_values))
            continue
        brep = rs.coercebrep(item)
        if brep is not None:
            breps.append(brep)
    return breps


def _snap_intersection(value):
    allowed_positions = (0.25, 0.5, 0.75)
    if not 0.0 <= value <= 1.0:
        raise ValueError(
            "Intersection values must be between 0.0 and 1.0."
        )
    return min(
        allowed_positions,
        key=lambda position: abs(position - value),
    )


def _snap_board_length(value, reference_length):
    allowed_lengths = (
        reference_length * (2.0 / 3.0),
        reference_length,
        reference_length * (4.0 / 3.0),
    )
    if value <= 0.0:
        raise ValueError("board_length must be positive.")
    return min(
        allowed_lengths,
        key=lambda length: abs(length - value),
    )


def _make_box(center, width, depth, height):
    plane = rg.Plane(
        rg.Point3d(center.X, center.Y, center.Z - height / 2.0),
        rg.Vector3d.ZAxis,
    )
    box = rg.Box(
        plane,
        rg.Interval(-width / 2.0, width / 2.0),
        rg.Interval(-depth / 2.0, depth / 2.0),
        rg.Interval(0.0, height),
    )
    return box.ToBrep()