import matplotlib.pyplot as plt
import numpy as np


def find_intersection(p1, p2, p3, p4):
    """Calculates the 2D intersection of segment (p1,p2) and (p3,p4)."""
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    x4, y4 = p4
    denom = (y4 - y3) * (x2 - x1) - (x4 - x3) * (y2 - y1)
    if denom == 0:
        return None
    ua = ((x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3)) / denom
    ub = ((x2 - x1) * (y1 - y3) - (y2 - y1) * (x1 - x3)) / denom
    # Only return if the intersection is actually on both segments
    if 0 < ua < 1 and 0 < ub < 1:
        return x1 + ua * (x2 - x1), y1 + ua * (y2 - y1)
    return None


def generate_chronicle_graph_final():
    # Changed: Set facecolor to 'none' instead of 'white' for transparency
    fig, ax = plt.subplots(figsize=(10, 10), facecolor="none")
    ax.set_facecolor("none")  # Changed: Set axis background to 'none' for transparency

    n = 12
    brand_color = "#FFFFFF"  # Changed to white
    line_weight = 1.7  # Reduced from 2.5 for thinner lines

    # 1. Primary 12 Outer Vertices
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False) - np.pi / 2
    outer_nodes = np.column_stack((np.cos(angles), np.sin(angles)))

    # 2. Define the Edges
    edges = []
    for i in range(n):
        edges.append((outer_nodes[i], outer_nodes[(i + 1) % n]))  # Perimeter
        edges.append((outer_nodes[i], outer_nodes[(i + 4) % n]))  # Internal Star
        edges.append((outer_nodes[i], outer_nodes[(i + 2) % n]))  # Internal Hex

    # 3. Draw Edges with Uniform Boldness
    for p1, p2 in edges:
        ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color=brand_color, lw=line_weight, zorder=1)

    # 4. Find precise intersections for Node placement
    all_nodes = list(outer_nodes)
    for i in range(len(edges)):
        for j in range(i + 1, len(edges)):
            point = find_intersection(edges[i][0], edges[i][1], edges[j][0], edges[j][1])
            if point:
                all_nodes.append(point)

    # Unique nodes only
    unique_nodes = np.unique(np.round(all_nodes, decimals=5), axis=0)
    ax.scatter(unique_nodes[:, 0], unique_nodes[:, 1], color=brand_color, s=70, zorder=5)

    # 5. Shortened Square Clock Hands (2:00 PM)
    h_angle = np.deg2rad(60)
    ax.plot(
        [0, 0.20 * np.cos(h_angle)],
        [0, 0.20 * np.sin(h_angle)],
        color=brand_color,
        lw=line_weight,
        solid_capstyle="butt",
        zorder=10,
    )
    ax.plot([0, 0], [0, 0.35], color=brand_color, lw=line_weight, solid_capstyle="butt", zorder=10)

    # Center Hub
    ax.scatter(0, 0, color=brand_color, s=70, zorder=11)

    # 6. Circular Text Treatment with Modern Font
    # Logo height is approximately 2 units (from -1 to 1), so letter height is 0.4
    letter_height = 0.4

    # Position text ring closer to the main logo
    # Main logo extends to radius ~1, so place text closer but with clearance
    inner_radius = 1.15  # Moved closer from 1.3
    outer_radius = inner_radius + letter_height
    mid_radius = (inner_radius + outer_radius) / 2

    # 16 equal segments (22.5 degrees each)
    segment_angle = 360 / 16

    # Font properties for clean, modern look
    font_props = {
        "fontsize": 28,
        "fontweight": 500,  # Semi-bold for better presence
        "fontfamily": "Aptos",
        "color": brand_color,
    }

    # Center both words by placing A in GRAPH at bottom center (270°)
    # GRAPH has 5 letters: G-R-A-P-H
    # A is at position 2 (index 2), so it's at 270°

    # GRAPH on bottom (5 letters)
    graph = "GRAPH"
    graph_center_index = 2  # A is at index 2
    graph_center_angle = 270  # Bottom center

    for i, letter in enumerate(graph):
        # Calculate angle relative to center position
        angle_deg = graph_center_angle + ((i - graph_center_index) * segment_angle)
        angle_rad = np.deg2rad(angle_deg)

        # Position for the letter (place at mid_radius)
        x = mid_radius * np.cos(angle_rad)
        y = mid_radius * np.sin(angle_rad)

        # Rotation: letter should be tangent to the circle
        # For bottom arc, need to flip orientation so it reads left to right
        rotation = angle_deg + 90

        ax.text(
            x,
            y,
            letter,
            ha="center",
            va="center",
            rotation=rotation,
            rotation_mode="anchor",
            **font_props,
        )

    # CHRONICLE on top (9 letters)
    # Center it similarly - middle letter (I at index 4) should be at top center (90°)
    chronicle = "CHRONICLE"
    chronicle_center_index = 4  # I is at index 4
    chronicle_center_angle = 90  # Top center

    for i, letter in enumerate(chronicle):
        # Calculate angle relative to center position
        angle_deg = chronicle_center_angle - ((i - chronicle_center_index) * segment_angle)
        angle_rad = np.deg2rad(angle_deg)

        # Position for the letter (place at mid_radius)
        x = mid_radius * np.cos(angle_rad)
        y = mid_radius * np.sin(angle_rad)

        # Rotation: letter should be tangent to the circle
        # Perpendicular to radius, reading left to right on top arc
        rotation = angle_deg - 90

        ax.text(
            x,
            y,
            letter,
            ha="center",
            va="center",
            rotation=rotation,
            rotation_mode="anchor",
            **font_props,
        )

    # Left dot separator (between C and G on the left)
    # C is at the end of CHRONICLE, G is at the start of GRAPH
    # Place dot midway between them
    c_angle = chronicle_center_angle - ((0 - chronicle_center_index) * segment_angle)
    g_angle = graph_center_angle + ((0 - graph_center_index) * segment_angle)
    left_dot_angle_deg = (c_angle + g_angle) / 2
    left_dot_angle_rad = np.deg2rad(left_dot_angle_deg)
    left_dot_x = mid_radius * np.cos(left_dot_angle_rad)
    left_dot_y = mid_radius * np.sin(left_dot_angle_rad)
    ax.scatter(left_dot_x, left_dot_y, color=brand_color, s=50, zorder=12)

    # Right dot separator (between E and H on the right)
    # E is at the end of CHRONICLE (index 8), H is at the end of GRAPH (index 4)
    e_angle = chronicle_center_angle - ((8 - chronicle_center_index) * segment_angle)
    h_angle = graph_center_angle + ((4 - graph_center_index) * segment_angle)

    # Handle angle wraparound: E is at 0°, H is at 315°
    # The dot should be between them on the right side (around 337.5°)
    # Since we're going from H (315°) to E (0°), we want the midpoint in that direction
    if e_angle < h_angle:
        # E has wrapped around, so add 360 to it for averaging
        right_dot_angle_deg = (e_angle + 360 + h_angle) / 2
        if right_dot_angle_deg >= 360:
            right_dot_angle_deg -= 360
    else:
        right_dot_angle_deg = (e_angle + h_angle) / 2

    right_dot_angle_rad = np.deg2rad(right_dot_angle_deg)
    right_dot_x = mid_radius * np.cos(right_dot_angle_rad)
    right_dot_y = mid_radius * np.sin(right_dot_angle_rad)
    ax.scatter(right_dot_x, right_dot_y, color=brand_color, s=50, zorder=12)

    # Draw container outlines
    # Inner and outer circles
    circle_inner = plt.Circle(
        (0, 0), inner_radius, fill=False, color=brand_color, linewidth=0.5, zorder=0
    )
    circle_outer = plt.Circle(
        (0, 0), outer_radius, fill=False, color=brand_color, linewidth=0.5, zorder=0
    )
    ax.add_patch(circle_inner)
    ax.add_patch(circle_outer)

    # Radial lines for each of the 16 segments
    # Offset by half a segment so lines fall between letters
    for i in range(16):
        angle_deg = (i * segment_angle) + (segment_angle / 2)
        angle_rad = np.deg2rad(angle_deg)
        x_inner = inner_radius * np.cos(angle_rad)
        y_inner = inner_radius * np.sin(angle_rad)
        x_outer = outer_radius * np.cos(angle_rad)
        y_outer = outer_radius * np.sin(angle_rad)
        ax.plot([x_inner, x_outer], [y_inner, y_outer], color=brand_color, linewidth=0.5, zorder=0)

    # 7. Final adjustments
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_xlim(-2.2, 2.2)
    ax.set_ylim(-2.2, 2.2)

    plt.tight_layout()
    return fig


fig = generate_chronicle_graph_final()
# Changed: Set transparent=True to ensure transparent background
fig.savefig(
    "/home/claude/chronicle_logo_white_transparent.svg",
    format="svg",
    bbox_inches="tight",
    pad_inches=0.1,
    dpi=300,
    transparent=True,
)
print("Transparent SVG with white design saved successfully")
