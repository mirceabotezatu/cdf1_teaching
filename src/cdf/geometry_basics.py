"""
Geometry basics -- reusable Rhino.Geometry functions for Grasshopper.

Adding a new function with Copilot
-----------------------------------
1. Open this file and select this chat model, then ask Copilot something like:
   "Add a function here, all in Rhino geometry, that builds a <your shape/idea>.
   Follow the same style as create_cone / create_fractal_tree (defaults for
   optional inputs, a docstring listing params, return a Rhino.Geometry object)."
2. Once the function is added, ask Copilot:
   "Give me the Python code to use this function in a Grasshopper GHPython 3
   component, importing it from computational_design_and_fabrication."
3. Copy the snippet Copilot gives you into a GHPython component, wire up the
   inputs as sliders/panels, and set the output variable (e.g. `a`).
"""

import math
import random
import Rhino.Geometry as rg
import rhinoscriptsyntax as rs
from System.Drawing import Color

def create_cone(base_point=None, height=10.0, radius=5.0, cap_bottom=True):
    """
    Build a cone as a Brep.

    base_point : Rhino.Geometry.Point3d -- center of the cone's base circle
    height     : float -- cone height above the base plane along +Z
    radius     : float -- base circle radius
    cap_bottom : bool  -- whether to cap the base circle (closed vs open cone)

    Returns a Rhino.Geometry.Brep.
    """
    if base_point is None:
        base_point = rg.Point3d(0, 0, 0)

    # RhinoCommon uses the plane origin as the apex and extends the cone
    # along the plane's +Z axis to its base.  Place the apex above the
    # requested base and point the cone axis downward so the base is at
    # base_point on the XY plane.
    apex_point = rg.Point3d(
        base_point.X,
        base_point.Y,
        base_point.Z + height,
    )
    plane = rg.Plane(apex_point, rg.Vector3d(0, 0, -1))
    cone = rg.Cone(plane, height, radius)
    return cone.ToBrep(cap_bottom)

def create_shape_grid(
    shape_type,
    base_point,
    radius,
    height,
    divisions=6,
):
    """
    Create curve geometry that follows a sphere or cone surface.

    shape_type : str -- either "sphere" or "cone"
    base_point : Point3d -- base center for a cone, sphere center otherwise
    radius     : float -- sphere or cone base radius
    height     : float -- cone height; ignored for spheres
    divisions  : int -- number of latitude and longitude grid lines

    Returns a list of Rhino.Geometry.Curve objects.
    """
    if shape_type not in ("sphere", "cone"):
        raise ValueError("shape_type must be 'sphere' or 'cone'.")
    if radius <= 0 or divisions < 2:
        raise ValueError("radius must be positive and divisions must be at least 2.")

    divisions = int(divisions)
    curves = []
    if shape_type == "sphere":
        for index in range(1, divisions):
            latitude = -math.pi / 2.0 + math.pi * index / divisions
            latitude_radius = radius * math.cos(latitude)
            latitude_z = base_point.Z + radius * math.sin(latitude)
            curves.append(
                rg.Circle(
                    rg.Plane(
                        rg.Point3d(base_point.X, base_point.Y, latitude_z),
                        rg.Vector3d.ZAxis,
                    ),
                    latitude_radius,
                ).ToNurbsCurve()
            )

        for index in range(divisions):
            longitude = 2.0 * math.pi * index / divisions
            points = []
            for step in range(divisions * 2 + 1):
                latitude = -math.pi / 2.0 + math.pi * step / (divisions * 2)
                points.append(
                    rg.Point3d(
                        base_point.X + radius * math.cos(latitude) * math.cos(longitude),
                        base_point.Y + radius * math.cos(latitude) * math.sin(longitude),
                        base_point.Z + radius * math.sin(latitude),
                    )
                )
            curves.append(rg.PolylineCurve(points))
    else:
        apex = rg.Point3d(
            base_point.X,
            base_point.Y,
            base_point.Z + height,
        )
        for index in range(1, divisions):
            fraction = float(index) / divisions
            z = base_point.Z + height * fraction
            ring_radius = radius * (1.0 - fraction)
            curves.append(
                rg.Circle(
                    rg.Plane(
                        rg.Point3d(base_point.X, base_point.Y, z),
                        rg.Vector3d.ZAxis,
                    ),
                    ring_radius,
                ).ToNurbsCurve()
            )

        for index in range(divisions):
            angle = 2.0 * math.pi * index / divisions
            base_edge = rg.Point3d(
                base_point.X + radius * math.cos(angle),
                base_point.Y + radius * math.sin(angle),
                base_point.Z,
            )
            curves.append(rg.LineCurve(apex, base_edge))

    return curves

def create_sphere(center_point=None, radius=5.0):
    """
    Build a sphere as a Brep.

    center_point : Rhino.Geometry.Point3d or Rhino object reference -- center
    radius       : float -- sphere radius

    Returns a Rhino.Geometry.Brep.
    """
    if center_point is None:
        center_point = rg.Point3d(0, 0, 0)
    elif not isinstance(center_point, rg.Point3d):
        center_point = rs.coerce3dpoint(center_point)
        if center_point is None:
            raise ValueError("center_point must be a Point3d or a point object reference.")

    if radius is None:
        radius = 5.0

    sphere = rg.Sphere(center_point, radius)
    return sphere.ToBrep()

def create_torus(
    center_point=None,
    major_radius=8.0,
    minor_radius=1.0,
):
    """
    Build a torus as a Brep in the XY plane.

    center_point : Rhino.Geometry.Point3d or Rhino object reference -- center
    major_radius : float -- distance from the torus center to the tube center
    minor_radius : float -- radius of the torus tube

    Returns a Rhino.Geometry.Brep.
    """
    if center_point is None:
        center_point = rg.Point3d(0, 0, 0)
    elif not isinstance(center_point, rg.Point3d):
        center_point = rs.coerce3dpoint(center_point)
        if center_point is None:
            raise ValueError("center_point must be a Point3d or a point object reference.")

    if major_radius is None:
        major_radius = 8.0
    if minor_radius is None:
        minor_radius = 1.0

    if major_radius <= 0 or minor_radius <= 0:
        raise ValueError("major_radius and minor_radius must be positive.")

    plane = rg.Plane(center_point, rg.Vector3d.ZAxis)
    torus = rg.Torus(plane, major_radius, minor_radius)
    return torus.ToBrep()

def create_box(base_point=None, width=20.0, depth=20.0, height=2.0):
    """
    Build a box as a Brep with its base centered on base_point.

    base_point : Rhino.Geometry.Point3d or Rhino object reference -- base center
    width      : float -- size along the plane's X axis
    depth      : float -- size along the plane's Y axis
    height     : float -- size along the plane's Z axis

    Returns a Rhino.Geometry.Brep.
    """
    if base_point is None:
        base_point = rg.Point3d(0, 0, 0)
    elif not isinstance(base_point, rg.Point3d):
        base_point = rs.coerce3dpoint(base_point)
        if base_point is None:
            raise ValueError("base_point must be a Point3d or a point object reference.")

    if width is None:
        width = 20.0
    if depth is None:
        depth = 20.0
    if height is None:
        height = 2.0
    if width <= 0 or depth <= 0 or height <= 0:
        raise ValueError("width, depth, and height must be positive.")

    plane = rg.Plane(base_point, rg.Vector3d.ZAxis)
    box = rg.Box(
        plane,
        rg.Interval(-width / 2.0, width / 2.0),
        rg.Interval(-depth / 2.0, depth / 2.0),
        rg.Interval(0.0, height),
    )
    return box.ToBrep()

def create_cylinder(base_point=None, radius=3.0, height=12.0):
    """
    Build a vertical cylinder as a Brep.

    base_point : Rhino.Geometry.Point3d or Rhino object reference -- base center
    radius     : float -- cylinder radius
    height     : float -- cylinder height along the Z axis

    Returns a Rhino.Geometry.Brep.
    """
    if base_point is None:
        base_point = rg.Point3d(0, 0, 0)
    elif not isinstance(base_point, rg.Point3d):
        base_point = rs.coerce3dpoint(base_point)
        if base_point is None:
            raise ValueError("base_point must be a Point3d or a point object reference.")

    if radius is None:
        radius = 3.0
    if height is None:
        height = 12.0
    if radius <= 0 or height <= 0:
        raise ValueError("radius and height must be positive.")

    plane = rg.Plane(base_point, rg.Vector3d.ZAxis)
    cylinder = rg.Cylinder(rg.Circle(plane, radius), height)
    return cylinder.ToBrep(True, True)

def create_bauhaus_composition(
    base_point=None,
    base_width=24.0,
    base_depth=18.0,
    base_height=1.0,
    cylinder_radius=3.0,
    cylinder_height=12.0,
    sphere_radius=4.0,
    sphere_x=5.0,
    sphere_y=0.0,
    box_width=5.0,
    box_depth=5.0,
    box_height=5.0,
    box_x=-6.0,
    box_y=0.0,
    box_angle=0.0,
):
    """
    Create a Bauhaus-style composition and a matching colour list.

    The base, cylinder, sphere, and box are generated from shared parameters
    so changing the slider values creates new composition variants.

    Returns a tuple: (list of Breps, list of System.Drawing.Color).
    """
    if base_point is None:
        base_point = rg.Point3d(0, 0, 0)
    elif not isinstance(base_point, rg.Point3d):
        base_point = rs.coerce3dpoint(base_point)
        if base_point is None:
            raise ValueError("base_point must be a Point3d or a point object reference.")

    base = create_box(base_point, base_width, base_depth, base_height)
    base_z = base_point.Z + base_height

    cylinder = create_cylinder(
        rg.Point3d(base_point.X, base_point.Y, base_z),
        cylinder_radius,
        cylinder_height,
    )
    sphere = create_sphere(
        rg.Point3d(
            base_point.X + sphere_x,
            base_point.Y + sphere_y,
            base_z + cylinder_height + sphere_radius,
        ),
        sphere_radius,
    )
    box = create_box(
        rg.Point3d(base_point.X + box_x, base_point.Y + box_y, base_z),
        box_width,
        box_depth,
        box_height,
    )

    if box_angle:
        box = rotate_brep_around_axis(
            box,
            rg.Point3d(base_point.X + box_x, base_point.Y + box_y, base_z),
            rg.Vector3d.ZAxis,
            box_angle,
        )

    geometry = [base, cylinder, sphere, box]
    colors = [
        Color.White,
        Color.Red,
        Color.Blue,
        Color.Yellow,
    ]
    return geometry, colors

def _create_connected_random_boxes_once(
    base_point=None,
    box_count=24,
    min_width=2.0,
    max_width=6.0,
    min_depth=2.0,
    max_depth=6.0,
    min_height=3.0,
    max_height=6.0,
    seed=1,
    field_size=40.0,
):
    """
    Create randomly sized rectangular prisms connected in plan.

    Every prism shares a non-zero-length edge with a previous prism in the
    XY plane. Prisms do not overlap in plan, leaving voids between branches
    of the connected composition.

    field_size : float -- side length of the square plan boundary

    Returns a tuple: (list of Breps, list of System.Drawing.Color).
    """
    if base_point is None:
        base_point = rg.Point3d(0, 0, 0)
    elif not isinstance(base_point, rg.Point3d):
        base_point = rs.coerce3dpoint(base_point)
        if base_point is None:
            raise ValueError("base_point must be a Point3d or a point object reference.")

    if box_count is None:
        box_count = 24
    if min_width is None:
        min_width = 2.0
    if max_width is None:
        max_width = 6.0
    if min_depth is None:
        min_depth = 2.0
    if max_depth is None:
        max_depth = 6.0
    if min_height is None:
        min_height = 3.0
    if max_height is None:
        max_height = 6.0
    if seed is None:
        seed = 1
    if field_size is None:
        field_size = 40.0

    box_count = int(box_count)
    if box_count <= 0:
        raise ValueError("box_count must be positive.")
    if (
        min_width <= 0
        or max_width < min_width
        or min_depth <= 0
        or max_depth < min_depth
        or min_height <= 0
        or max_height < min_height
        or field_size <= 0
    ):
        raise ValueError("Each minimum dimension must be positive and no greater than its maximum.")

    generator = random.Random(int(seed))
    rectangles = []
    geometry = []
    colors = []
    bauhaus_palette = (
        Color.White,
        Color.Black,
        Color.FromArgb(190, 30, 45),
        Color.FromArgb(245, 190, 35),
        Color.FromArgb(35, 75, 145),
        Color.FromArgb(130, 130, 130),
    )
    epsilon = 1e-6
    max_attempts = 500
    field_half = field_size / 2.0

    def add_rectangle(x_min, x_max, y_min, y_max, height):
        center = rg.Point3d(
            base_point.X + (x_min + x_max) / 2.0,
            base_point.Y + (y_min + y_max) / 2.0,
            base_point.Z,
        )
        geometry.append(
            create_box(
                center,
                x_max - x_min,
                y_max - y_min,
                height,
            )
        )
        rectangles.append((x_min, x_max, y_min, y_max))
        colors.append(generator.choice(bauhaus_palette))

    first_width = generator.uniform(min_width, max_width)
    first_depth = generator.uniform(min_depth, max_depth)
    if first_width > field_size or first_depth > field_size:
        raise ValueError("field_size must be at least as large as the maximum box width and depth.")
    add_rectangle(
        -first_width / 2.0,
        first_width / 2.0,
        -first_depth / 2.0,
        first_depth / 2.0,
        generator.uniform(min_height, max_height),
    )

    while len(rectangles) < box_count:
        placed = False
        candidate_placements = []
        for _ in range(max_attempts):
            parent = generator.choice(rectangles)
            parent_x_min, parent_x_max, parent_y_min, parent_y_max = parent
            width = generator.uniform(min_width, max_width)
            depth = generator.uniform(min_depth, max_depth)
            height = generator.uniform(min_height, max_height)
            corner = generator.choice(
                ("bottom_left", "bottom_right", "top_left", "top_right")
            )

            if corner == "bottom_left":
                x_max = parent_x_min
                x_min = x_max - width
                y_max = parent_y_min
                y_min = y_max - depth
            elif corner == "bottom_right":
                x_min = parent_x_max
                x_max = x_min + width
                y_max = parent_y_min
                y_min = y_max - depth
            elif corner == "top_left":
                x_max = parent_x_min
                x_min = x_max - width
                y_min = parent_y_max
                y_max = y_min + depth
            else:
                x_min = parent_x_max
                x_max = x_min + width
                y_min = parent_y_max
                y_max = y_min + depth

            if (
                x_min < -field_half
                or x_max > field_half
                or y_min < -field_half
                or y_max > field_half
            ):
                continue

            overlaps_existing = any(
                x_min < other_x_max - epsilon
                and x_max > other_x_min + epsilon
                and y_min < other_y_max - epsilon
                and y_max > other_y_min + epsilon
                for other_x_min, other_x_max, other_y_min, other_y_max in rectangles
            )
            if overlaps_existing:
                continue

            distance_from_center = abs((x_min + x_max) / 2.0) + abs((y_min + y_max) / 2.0)
            candidate_placements.append(
                (
                    distance_from_center,
                    x_min,
                    x_max,
                    y_min,
                    y_max,
                    height,
                )
            )

        if candidate_placements:
            candidate_placements.sort(key=lambda candidate: candidate[0])
            _, x_min, x_max, y_min, y_max, height = generator.choice(
                candidate_placements[: max(1, len(candidate_placements) // 3)]
            )
            add_rectangle(x_min, x_max, y_min, y_max, height)
            placed = True

        if not placed:
            raise RuntimeError(
                "Could not place all boxes without plan overlap. "
                "Try fewer boxes or smaller dimensions."
            )

    return geometry, colors

def create_connected_random_boxes(
    base_point=None,
    box_count=24,
    min_width=2.0,
    max_width=6.0,
    min_depth=2.0,
    max_depth=6.0,
    min_height=3.0,
    max_height=6.0,
    seed=1,
    field_size=40.0,
):
    """
    Create connected random boxes, retrying deterministic layouts if needed.

    The retries use consecutive seeds derived from the supplied seed. This
    avoids rejecting a valid parameter set because one random growth path
    became trapped against the boundary.
    """
    if seed is None:
        seed = 1

    last_error = None
    for scale_step in range(15):
        scale = 1.0 - scale_step * 0.05
        scaled_min_width = min_width * scale
        scaled_max_width = max_width * scale
        scaled_min_depth = min_depth * scale
        scaled_max_depth = max_depth * scale
        scaled_min_height = min_height * scale
        scaled_max_height = max_height * scale

        for attempt in range(20):
            try:
                return _create_connected_random_boxes_once(
                    base_point,
                    box_count,
                    scaled_min_width,
                    scaled_max_width,
                    scaled_min_depth,
                    scaled_max_depth,
                    scaled_min_height,
                    scaled_max_height,
                    int(seed) + scale_step * 20 + attempt,
                    field_size,
                )
            except RuntimeError as error:
                last_error = error

    raise RuntimeError(
        "Could not place all boxes inside the square field, even after "
        "reducing their dimensions. Try fewer boxes or a larger field_size."
    ) from last_error

def create_connected_boxes_with_gap_shapes(
    base_point=None,
    box_count=24,
    min_width=2.0,
    max_width=6.0,
    min_depth=2.0,
    max_depth=6.0,
    min_height=3.0,
    max_height=6.0,
    seed=1,
    field_size=40.0,
    gap_shape_count=12,
    gap_min_radius=0.5,
    gap_max_radius=1.5,
    gap_min_height=2.0,
    gap_max_height=5.0,
    sphere_count=None,
    cone_count=None,
    show_shape_grid=True,
    grid_divisions=6,
    grid_color=None,
):
    """
    Create connected boxes with random spheres and cones in the plan gaps.

    Gap shapes are accepted only when their circular plan footprint is clear
    of every box and every previously placed gap shape.

    gap_shape_count : int -- total number of randomly selected spheres and
        cones when sphere_count and cone_count are not provided
    sphere_count : int or None -- exact number of spheres to add; when set,
        cone_count defaults to zero
    cone_count : int or None -- exact number of cones to add; when set,
        sphere_count defaults to zero
    show_shape_grid : bool -- add curve grids over generated spheres and cones
    grid_divisions : int -- grid density for each generated shape
    grid_color : System.Drawing.Color or None -- color of grid curves

    Returns a tuple: (list of geometry objects, list of System.Drawing.Color).
    """
    geometry, colors = create_connected_random_boxes(
        base_point,
        box_count,
        min_width,
        max_width,
        min_depth,
        max_depth,
        min_height,
        max_height,
        seed,
        field_size,
    )

    if base_point is None:
        base_point = rg.Point3d(0, 0, 0)
    elif not isinstance(base_point, rg.Point3d):
        base_point = rs.coerce3dpoint(base_point)
        if base_point is None:
            raise ValueError("base_point must be a Point3d or a point object reference.")

    if gap_shape_count is None:
        gap_shape_count = 12
    if gap_min_radius is None:
        gap_min_radius = 0.5
    if gap_max_radius is None:
        gap_max_radius = 1.5
    if gap_min_height is None:
        gap_min_height = 2.0
    if gap_max_height is None:
        gap_max_height = 5.0
    if grid_divisions is None:
        grid_divisions = 6
    if grid_color is None:
        grid_color = Color.Black
    if (
        gap_shape_count < 0
        or (sphere_count is not None and sphere_count < 0)
        or (cone_count is not None and cone_count < 0)
        or gap_min_radius <= 0
        or gap_max_radius < gap_min_radius
    ):
        raise ValueError("Gap shape count and radius values are invalid.")
    if gap_min_height <= 0 or gap_max_height < gap_min_height:
        raise ValueError("Gap height values are invalid.")
    if int(grid_divisions) < 2:
        raise ValueError("grid_divisions must be at least 2.")

    if sphere_count is None and cone_count is None:
        shape_types = [None] * int(gap_shape_count)
    else:
        shape_types = (
            ["sphere"] * int(sphere_count or 0)
            + ["cone"] * int(cone_count or 0)
        )

    generator = random.Random(int(seed) + 100000)
    generator.shuffle(shape_types)
    occupied = []
    for brep in geometry:
        bounds = brep.GetBoundingBox(True)
        occupied.append(
            (bounds.Min.X, bounds.Max.X, bounds.Min.Y, bounds.Max.Y)
        )

    field_half = field_size / 2.0
    gap_palette = (
        Color.White,
        Color.Black,
        Color.FromArgb(190, 30, 45),
        Color.FromArgb(245, 190, 35),
        Color.FromArgb(35, 75, 145),
    )
    max_attempts = max(100, len(shape_types) * 100)

    placed_shape_count = 0
    for shape_type in shape_types:
        placed = False
        for _ in range(max_attempts):
            radius = generator.uniform(gap_min_radius, gap_max_radius)
            x = generator.uniform(-field_half + radius, field_half - radius)
            y = generator.uniform(-field_half + radius, field_half - radius)
            candidate = (x - radius, x + radius, y - radius, y + radius)

            if any(
                candidate[0] < other_x_max
                and candidate[1] > other_x_min
                and candidate[2] < other_y_max
                and candidate[3] > other_y_min
                for other_x_min, other_x_max, other_y_min, other_y_max in occupied
            ):
                continue

            shape_point = rg.Point3d(
                base_point.X + x,
                base_point.Y + y,
                base_point.Z,
            )
            height = generator.uniform(gap_min_height, gap_max_height)
            if shape_type == "sphere" or (
                shape_type is None and generator.choice((True, False))
            ):
                sphere_center = rg.Point3d(
                    shape_point.X,
                    shape_point.Y,
                    shape_point.Z + radius,
                )
                shape = create_sphere(sphere_center, radius)
                grid_base_point = sphere_center
                grid_shape_type = "sphere"
            else:
                shape = create_cone(shape_point, height, radius, True)
                grid_base_point = shape_point
                grid_shape_type = "cone"

            geometry.append(shape)
            colors.append(generator.choice(gap_palette))
            if show_shape_grid:
                grid_curves = create_shape_grid(
                    grid_shape_type,
                    grid_base_point,
                    radius,
                    height,
                    int(grid_divisions),
                )
                geometry.extend(grid_curves)
                colors.extend([grid_color] * len(grid_curves))
            occupied.append(candidate)
            placed = True
            break

        if not placed:
            if shape_type is None:
                break
            raise RuntimeError(
                "Could not place all requested gap shapes. "
                "Try fewer spheres/cones, smaller radii, or a larger field_size. "
                "Placed {0} of {1} requested shapes.".format(
                    placed_shape_count,
                    len(shape_types),
                )
            )
        placed_shape_count += 1

    return geometry, colors

def create_connected_3d_boxes(
    base_point=None,
    cube_size=40.0,
    box_count=40,
    min_width=2.0,
    max_width=6.0,
    min_depth=2.0,
    max_depth=6.0,
    min_height=2.0,
    max_height=6.0,
    seed=1,
    show_hatch=True,
    hatch_spacing=1.0,
    hatch_color=None,
):
    """
    Grow a connected 3D composition from the center of a bounding cube.

    The first box is centered at base_point and uses the maximum requested
    dimensions. Each subsequent box is attached to one face of an existing
    box, sharing a positive-area face overlap. Boxes become smaller as their
    growth moves away from base_point. Every box remains inside the bounding
    cube and boxes do not overlap.

    base_point : Point3d or Rhino object reference -- center of the cube
    cube_size : float -- side length of the bounding cube
    box_count : int -- total number of connected boxes
    min/max_width : float -- box size range along X
    min/max_depth : float -- box size range along Y
    min/max_height : float -- box size range along Z
    seed : int -- deterministic random seed
    show_hatch : bool -- add square hatch curves to the box faces
    hatch_spacing : float -- spacing between hatch lines
    hatch_color : System.Drawing.Color or None -- hatch curve color

    Returns a tuple: (list of geometry objects, list of System.Drawing.Color).
    """
    if base_point is None:
        base_point = rg.Point3d(0, 0, 0)
    elif not isinstance(base_point, rg.Point3d):
        base_point = rs.coerce3dpoint(base_point)
        if base_point is None:
            raise ValueError("base_point must be a Point3d or a point object reference.")

    if cube_size is None:
        cube_size = 40.0
    if box_count is None:
        box_count = 40
    if min_width is None:
        min_width = 2.0
    if max_width is None:
        max_width = 6.0
    if min_depth is None:
        min_depth = 2.0
    if max_depth is None:
        max_depth = 6.0
    if min_height is None:
        min_height = 2.0
    if max_height is None:
        max_height = 6.0
    if seed is None:
        seed = 1
    if hatch_spacing is None:
        hatch_spacing = 1.0
    if hatch_color is None:
        hatch_color = Color.Black

    box_count = int(box_count)
    cube_size = float(cube_size)
    if cube_size <= 0 or box_count <= 0:
        raise ValueError("cube_size and box_count must be positive.")
    if (
        min_width <= 0
        or max_width < min_width
        or min_depth <= 0
        or max_depth < min_depth
        or min_height <= 0
        or max_height < min_height
    ):
        raise ValueError("Each minimum dimension must be positive and no greater than its maximum.")
    if max_width > cube_size or max_depth > cube_size or max_height > cube_size:
        raise ValueError("Every maximum box dimension must fit inside cube_size.")
    if hatch_spacing <= 0:
        raise ValueError("hatch_spacing must be positive.")

    generator = random.Random(int(seed))
    half_cube = cube_size / 2.0
    epsilon = 1e-6
    palette = (
        Color.White,
        Color.Black,
        Color.FromArgb(190, 30, 45),
        Color.FromArgb(245, 190, 35),
        Color.FromArgb(35, 75, 145),
        Color.FromArgb(130, 130, 130),
    )

    def dimensions_for_distance(distance):
        scale = max(0.0, min(1.0, 1.0 - distance / half_cube))
        return (
            min_width + (max_width - min_width) * scale,
            min_depth + (max_depth - min_depth) * scale,
            min_height + (max_height - min_height) * scale,
        )

    def overlaps(first, second):
        return (
            first[0] < second[1] - epsilon
            and first[1] > second[0] + epsilon
            and first[2] < second[3] - epsilon
            and first[3] > second[2] + epsilon
            and first[4] < second[5] - epsilon
            and first[5] > second[4] + epsilon
        )

    def interval_overlap(first_min, first_max, second_min, second_max):
        return max(
            0.0,
            min(first_max, second_max) - max(first_min, second_min),
        )

    def face_contact_area(first, second, direction):
        if direction.startswith("x"):
            return interval_overlap(first[2], first[3], second[2], second[3]) * interval_overlap(
                first[4], first[5], second[4], second[5]
            )
        if direction.startswith("y"):
            return interval_overlap(first[0], first[1], second[0], second[1]) * interval_overlap(
                first[4], first[5], second[4], second[5]
            )
        return interval_overlap(first[0], first[1], second[0], second[1]) * interval_overlap(
            first[2], first[3], second[2], second[3]
        )

    def inside_cube(bounds):
        return (
            bounds[0] >= -half_cube - epsilon
            and bounds[1] <= half_cube + epsilon
            and bounds[2] >= -half_cube - epsilon
            and bounds[3] <= half_cube + epsilon
            and bounds[4] >= -half_cube - epsilon
            and bounds[5] <= half_cube + epsilon
        )

    def create_box_hatch(bounds):
        x_min, x_max, y_min, y_max, z_min, z_max = bounds
        curves = []

        def add_x_lines(z, y_start, y_end):
            y = y_start
            while y <= y_end + epsilon:
                curves.append(
                    rg.LineCurve(
                        rg.Point3d(base_point.X + x_min, base_point.Y + y, base_point.Z + z),
                        rg.Point3d(base_point.X + x_max, base_point.Y + y, base_point.Z + z),
                    )
                )
                y += hatch_spacing

        def add_y_lines(z, x_start, x_end):
            x = x_start
            while x <= x_end + epsilon:
                curves.append(
                    rg.LineCurve(
                        rg.Point3d(base_point.X + x, base_point.Y + y_min, base_point.Z + z),
                        rg.Point3d(base_point.X + x, base_point.Y + y_max, base_point.Z + z),
                    )
                )
                x += hatch_spacing

        def add_xz_lines(y):
            x = x_min
            while x <= x_max + epsilon:
                curves.append(
                    rg.LineCurve(
                        rg.Point3d(base_point.X + x, base_point.Y + y, base_point.Z + z_min),
                        rg.Point3d(base_point.X + x, base_point.Y + y, base_point.Z + z_max),
                    )
                )
                x += hatch_spacing
            z = z_min
            while z <= z_max + epsilon:
                curves.append(
                    rg.LineCurve(
                        rg.Point3d(base_point.X + x_min, base_point.Y + y, base_point.Z + z),
                        rg.Point3d(base_point.X + x_max, base_point.Y + y, base_point.Z + z),
                    )
                )
                z += hatch_spacing

        def add_yz_lines(x):
            y = y_min
            while y <= y_max + epsilon:
                curves.append(
                    rg.LineCurve(
                        rg.Point3d(base_point.X + x, base_point.Y + y, base_point.Z + z_min),
                        rg.Point3d(base_point.X + x, base_point.Y + y, base_point.Z + z_max),
                    )
                )
                y += hatch_spacing
            z = z_min
            while z <= z_max + epsilon:
                curves.append(
                    rg.LineCurve(
                        rg.Point3d(base_point.X + x, base_point.Y + y_min, base_point.Z + z),
                        rg.Point3d(base_point.X + x, base_point.Y + y_max, base_point.Z + z),
                    )
                )
                z += hatch_spacing

        add_x_lines(z_min, y_min, y_max)
        add_y_lines(z_min, x_min, x_max)
        add_x_lines(z_max, y_min, y_max)
        add_y_lines(z_max, x_min, x_max)
        add_xz_lines(y_min)
        add_xz_lines(y_max)
        add_yz_lines(x_min)
        add_yz_lines(x_max)
        return curves

    def add_box(bounds, color):
        center = rg.Point3d(
            base_point.X + (bounds[0] + bounds[1]) / 2.0,
            base_point.Y + (bounds[2] + bounds[3]) / 2.0,
            base_point.Z + bounds[4],
        )
        geometry.append(
            create_box(
                center,
                bounds[1] - bounds[0],
                bounds[3] - bounds[2],
                bounds[5] - bounds[4],
            )
        )
        colors.append(color)
        if show_hatch:
            hatch_curves = create_box_hatch(bounds)
            geometry.extend(hatch_curves)
            colors.extend([hatch_color] * len(hatch_curves))

    root_width = max_width
    root_depth = max_depth
    root_height = max_height
    bounds_list = [
        (
            -root_width / 2.0,
            root_width / 2.0,
            -root_depth / 2.0,
            root_depth / 2.0,
            -root_height / 2.0,
            root_height / 2.0,
        )
    ]
    geometry = []
    colors = []
    add_box(bounds_list[0], generator.choice(palette))

    directions = (
        ("x_min", -1),
        ("x_max", 1),
        ("y_min", -1),
        ("y_max", 1),
        ("z_min", -1),
        ("z_max", 1),
    )

    while len(bounds_list) < box_count:
        candidates = []
        for _ in range(1000):
            parent = generator.choice(bounds_list)
            direction, sign = generator.choice(directions)
            parent_center_distance = math.sqrt(
                (
                    (parent[0] + parent[1]) / 2.0
                ) ** 2
                + (
                    (parent[2] + parent[3]) / 2.0
                ) ** 2
                + (
                    (parent[4] + parent[5]) / 2.0
                ) ** 2
            )
            estimated_child_distance = parent_center_distance + max(
                max_width,
                max_depth,
                max_height,
            ) / 2.0
            width, depth, height = dimensions_for_distance(estimated_child_distance)
            candidate = None

            if direction.startswith("x"):
                x = parent[0] - width if sign < 0 else parent[1]
                y_min = generator.uniform(
                    max(-half_cube, parent[2] - depth + epsilon),
                    min(parent[3] - epsilon, half_cube - depth),
                )
                z_min = generator.uniform(
                    max(-half_cube, parent[4] - height + epsilon),
                    min(parent[5] - epsilon, half_cube - height),
                )
                candidate = (x, x + width, y_min, y_min + depth, z_min, z_min + height)
            elif direction.startswith("y"):
                y = parent[2] - depth if sign < 0 else parent[3]
                x_min = generator.uniform(
                    max(-half_cube, parent[0] - width + epsilon),
                    min(parent[1] - epsilon, half_cube - width),
                )
                z_min = generator.uniform(
                    max(-half_cube, parent[4] - height + epsilon),
                    min(parent[5] - epsilon, half_cube - height),
                )
                candidate = (x_min, x_min + width, y, y + depth, z_min, z_min + height)
            else:
                z = parent[4] - height if sign < 0 else parent[5]
                x_min = generator.uniform(
                    max(-half_cube, parent[0] - width + epsilon),
                    min(parent[1] - epsilon, half_cube - width),
                )
                y_min = generator.uniform(
                    max(-half_cube, parent[2] - depth + epsilon),
                    min(parent[3] - epsilon, half_cube - depth),
                )
                candidate = (x_min, x_min + width, y_min, y_min + depth, z, z + height)

            if (
                inside_cube(candidate)
                and not any(overlaps(candidate, existing) for existing in bounds_list)
            ):
                contact_area = face_contact_area(candidate, parent, direction)
                if contact_area > epsilon:
                    candidates.append((contact_area, candidate))

        if not candidates:
            raise RuntimeError(
                "Could not grow the requested 3D composition. "
                "Try fewer boxes, smaller dimensions, or a larger cube_size. "
                "Placed {0} of {1} requested boxes.".format(
                    len(bounds_list),
                    box_count,
                )
            )

        candidates.sort(key=lambda item: item[0], reverse=True)
        best_count = max(1, len(candidates) // 10)
        _, candidate = generator.choice(candidates[:best_count])
        bounds_list.append(candidate)
        add_box(candidate, generator.choice(palette))

    return geometry, colors

def create_chequered_box(
    base_point=None,
    cube_size=2.0,
    columns=4,
    rows=4,
    layers=4,
):
    """
    Create a 3D checkerboard from separate cubes.

    The cube at a grid position is created when
    (layer + row + column) is even. Empty positions remain free air.

    base_point : Rhino.Geometry.Point3d or Rhino object reference -- lower corner
    cube_size  : float -- side length of every cube
    columns    : int -- number of cubes along the X axis
    rows       : int -- number of cubes along the Y axis
    layers     : int -- number of cubes along the Z axis

    Returns a list of Rhino.Geometry.Brep cubes.
    """
    if base_point is None:
        base_point = rg.Point3d(0, 0, 0)
    elif not isinstance(base_point, rg.Point3d):
        base_point = rs.coerce3dpoint(base_point)
        if base_point is None:
            raise ValueError("base_point must be a Point3d or a point object reference.")

    if cube_size is None:
        cube_size = 2.0
    if columns is None:
        columns = 4
    if rows is None:
        rows = 4
    if layers is None:
        layers = 4

    columns = int(columns)
    rows = int(rows)
    layers = int(layers)
    if cube_size <= 0:
        raise ValueError("cube_size must be positive.")
    if columns <= 0 or rows <= 0 or layers <= 0:
        raise ValueError("columns, rows, and layers must be positive.")

    cubes = []
    for layer in range(layers):
        for row in range(rows):
            for column in range(columns):
                if (layer + row + column) % 2 == 0:
                    cube_center = rg.Point3d(
                        base_point.X + (column + 0.5) * cube_size,
                        base_point.Y + (row + 0.5) * cube_size,
                        base_point.Z + (layer + 0.5) * cube_size,
                    )
                    cubes.append(
                        create_box(
                            cube_center,
                            cube_size,
                            cube_size,
                            cube_size,
                        )
                    )
    return cubes

def rotate_brep_around_axis(
    brep,
    axis_origin=None,
    axis_direction=None,
    angle=0.0,
):
    """
    Return a copy of a Brep rotated around an external axis.

    brep           : Rhino.Geometry.Brep -- geometry fixed to the moving plane
    axis_origin    : Rhino.Geometry.Point3d -- point on the external axis
    axis_direction : Rhino.Geometry.Vector3d -- direction of the external axis
    angle          : float -- rotation angle in degrees

    Returns a Rhino.Geometry.Brep.
    """
    if brep is None:
        raise ValueError("brep must be provided.")

    if axis_origin is None:
        axis_origin = rg.Point3d(0, 0, 0)
    elif not isinstance(axis_origin, rg.Point3d):
        axis_origin = rs.coerce3dpoint(axis_origin)
        if axis_origin is None:
            raise ValueError("axis_origin must be a Point3d or a point object reference.")

    if axis_direction is None:
        axis_direction = rg.Vector3d.YAxis
    elif not isinstance(axis_direction, rg.Vector3d):
        axis_direction = rg.Vector3d(
            axis_direction.X,
            axis_direction.Y,
            axis_direction.Z,
        )
    if angle is None:
        angle = 0.0
    if not axis_direction.Unitize():
        raise ValueError("axis_direction must be a non-zero vector.")

    rotated_brep = brep.DuplicateBrep()
    transform = rg.Transform.Rotation(
        math.radians(angle),
        axis_direction,
        axis_origin,
    )
    rotated_brep.Transform(transform)
    return rotated_brep

def boolean_difference(brep_a, brep_b):
    """
    Perform a boolean difference operation between two Breps.

    brep_a : Rhino.Geometry.Brep -- the first Brep
    brep_b : Rhino.Geometry.Brep -- the second Brep to subtract from the first

    Returns a list of Rhino.Geometry.Brep resulting from the difference.
    """
    if brep_a is None or brep_b is None:
        raise ValueError("Both brep_a and brep_b must be provided.")

    if not isinstance(brep_a, rg.Brep):
        brep_a = rs.coercebrep(brep_a)
    if not isinstance(brep_b, rg.Brep):
        brep_b = rs.coercebrep(brep_b)
    if brep_a is None or brep_b is None:
        raise ValueError("brep_a and brep_b must be Breps or Brep object references.")

    result = rg.Brep.CreateBooleanDifference([brep_a], [brep_b], 0.001)
    return result


def copy_brep_along_z(brep, distance, copy_count):
    """
    Create copies of a Brep, each offset in the +Z direction.

    brep : Rhino.Geometry.Brep -- the Brep to copy
    distance : float -- the Z spacing between consecutive copies
    copy_count : int -- the number of copies to create

    Returns a list of Rhino.Geometry.Brep copies; copy i is moved by distance * (i + 1).
    """
    if brep is None:
        raise ValueError("brep must be provided.")
    if copy_count < 0:
        raise ValueError("copy_count must not be negative.")

    copies = []
    for i in range(1, int(copy_count) + 1):
        copy = brep.DuplicateBrep()
        copy.Transform(rg.Transform.Translation(rg.Vector3d(0, 0, distance * i)))
        copies.append(copy)
    return copies