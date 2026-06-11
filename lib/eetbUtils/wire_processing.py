#======================================================
# This software is released under the MIT license:
#
# MIT License
#
# Copyright (c) 2026 Pal Szabo
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#======================================================

import math
from .. import treelib

def connection_point_of_wires(wire1: dict, wire2: dict) -> tuple[int, int]:
    """
    Calculate the connection point coordinates where two wires intersect.

    This function takes two wire dictionaries and determines the point at which
    they connect. The wires are expected to be represented as dictionaries with
    coordinate information.

    Args:
        wire1 (dict): Dictionary containing the first wire's data including coordinates
        wire2 (dict): Dictionary containing the second wire's data including coordinates

    Returns:
        tuple[int, int]: A tuple containing the x and y coordinates of the connection point

    Note:
        The function assumes that the wire dictionaries contain the necessary coordinate
        information to determine the intersection point.
    """
    if abs(wire1['x1'] - wire2['x1']) < 1e-7 and abs(wire1['y1'] - wire2['y1']) < 1e-7:
        return (1, 1)
    elif abs(wire1['x2'] - wire2['x1']) < 1e-7 and abs(wire1['y2'] - wire2['y1']) < 1e-7:
        return (2, 1)
    elif abs(wire1['x2'] - wire2['x2']) < 1e-7 and abs(wire1['y2'] - wire2['y2']) < 1e-7:
        return (2, 2)
    elif abs(wire1['x1'] - wire2['x2']) < 1e-7 and abs(wire1['y1'] - wire2['y2']) < 1e-7:
        return (1, 2)
    else:
        return (0, 0)


def flip_wire(wire: dict):
    """
    Flip the direction of a wire by swapping its start and end coordinates.

    This function takes a wire dictionary and returns a new dictionary with the
    start and end coordinates swapped. The wire is represented as a dictionary
    with keys 'x1', 'y1', 'x2', and 'y2' for the start and end points respectively.
    If the wire is an arc, its curve property is negated.

    Args:
        wire (dict): Dictionary containing the wire's data including coordinates
    """
    wire['x1'], wire['x2'] = wire['x2'], wire['x1']
    wire['y1'], wire['y2'] = wire['y2'], wire['y1']
    if wire.get('curve', 0) != 0:
        wire['curve'] = -wire['curve']


def intersect_lines(wire1: dict, wire2: dict):
    """Find intersection of two lines or arcs defined by two wire dictionaries.

    Args:
        wire1, wire2: Wires defining the first and second line/arc.
                      Expected keys: x1, y1, x2, y2, and optionally curve, xc, yc, radius.

    Returns:
        tuple: (x, y) intersection point or (None, None) if no intersection found.
    """
    curve1 = wire1.get('curve', 0)
    curve2 = wire2.get('curve', 0)

    if curve1 == 0 and curve2 == 0:
        x1, y1 = wire1['x1'], wire1['y1']
        x2, y2 = wire1['x2'], wire1['y2']
        x3, y3 = wire2['x1'], wire2['y1']
        x4, y4 = wire2['x2'], wire2['y2']
        
        denom = (y4 - y3) * (x2 - x1) - (x4 - x3) * (y2 - y1)
        if abs(denom) < 1e-10:
            return None, None
        ua = ((x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3)) / denom
        return x1 + ua * (x2 - x1), y1 + ua * (y2 - y1)

    def intersect_line_circle(lx1, ly1, lx2, ly2, cx, cy, r):
        dx, dy = lx2 - lx1, ly2 - ly1
        a = dx**2 + dy**2
        if a < 1e-10: return []
        bx, by = lx1 - cx, ly1 - cy
        b = 2 * (dx * bx + dy * by)
        c = bx**2 + by**2 - r**2
        det = b**2 - 4 * a * c
        if det < 0: return []
        det = math.sqrt(det)
        return [(lx1 + u * dx, ly1 + u * dy) for u in [(-b + det) / (2 * a), (-b - det) / (2 * a)]]

    def intersect_circle_circle(c1x, c1y, r1, c2x, c2y, r2):
        dx, dy = c2x - c1x, c2y - c1y
        d2 = dx**2 + dy**2
        d = math.sqrt(d2)
        if d > r1 + r2 or d < abs(r1 - r2) or d == 0: return []
        a = (r1**2 - r2**2 + d2) / (2 * d)
        h = math.sqrt(max(0, r1**2 - a**2))
        x2, y2 = c1x + a * dx / d, c1y + a * dy / d
        return [(x2 + h * dy / d, y2 - h * dx / d), (x2 - h * dy / d, y2 + h * dx / d)]

    points = []
    if curve1 == 0:
        points = intersect_line_circle(wire1['x1'], wire1['y1'], wire1['x2'], wire1['y2'],
                                       wire2['xc'], wire2['yc'], wire2['radius'])
    elif curve2 == 0:
        points = intersect_line_circle(wire2['x1'], wire2['y1'], wire2['x2'], wire2['y2'],
                                       wire1['xc'], wire1['yc'], wire1['radius'])
    else:
        points = intersect_circle_circle(wire1['xc'], wire1['yc'], wire1['radius'],
                                         wire2['xc'], wire2['yc'], wire2['radius'])

    if not points:
        return None, None
    
    # Pick the point closest to the connection point of the original wires
    ref_x, ref_y = (wire1['x2'] + wire2['x1']) / 2, (wire1['y2'] + wire2['y1']) / 2
    return min(points, key=lambda p: (p[0] - ref_x)**2 + (p[1] - ref_y)**2)


def translate_wire(wire: dict, offset_value: float) -> dict:
    """Translate a wire segment perpendicular to itself by the offset value.

    Args:
        wire (dict): Original wire dictionary with x1, y1, x2, y2 coordinates
        offset_value (float): The offset distance to apply

    Returns:
        dict: Translated wire dictionary
    """
    curve = wire.get('curve', 0)
    if curve == 0:
        x1, y1 = wire['x1'], wire['y1']
        x2, y2 = wire['x2'], wire['y2']

        # Calculate wire length and direction
        dx = x2 - x1
        dy = y2 - y1

        # Calculate perpendicular vector (rotated 90 degrees)
        perp_x = -dy
        perp_y = dx

        # Normalize perpendicular vector
        length = (perp_x ** 2 + perp_y ** 2) ** 0.5
        if length > 0:
            perp_x /= length
            perp_y /= length

        # Apply offset
        offset_x = perp_x * offset_value
        offset_y = perp_y * offset_value

        # Create new wire coordinates
        new_wire = wire.copy()
        new_wire['x1'] = x1 + offset_x
        new_wire['y1'] = y1 + offset_y
        new_wire['x2'] = x2 + offset_x
        new_wire['y2'] = y2 + offset_y
        return new_wire
    else:
        xc, yc = wire['xc'], wire['yc']
        radius = wire['radius']

        # CCW (curve > 0): offset > 0 moves left (inwards) -> radius decreases
        # CW (curve < 0): offset > 0 moves left (outwards) -> radius increases
        new_radius = radius - offset_value if curve > 0 else radius + offset_value
        
        ratio = new_radius / radius if radius != 0 else 1.0
        new_wire = wire.copy()
        new_wire['radius'] = new_radius
        new_wire['x1'] = xc + (wire['x1'] - xc) * ratio
        new_wire['y1'] = yc + (wire['y1'] - yc) * ratio
        new_wire['x2'] = xc + (wire['x2'] - xc) * ratio
        new_wire['y2'] = yc + (wire['y2'] - yc) * ratio
        return new_wire


def are_wires_connecting(wire1: dict, wire2: dict) -> tuple[int, int]:
    """
    Check if any endpoints of two wires are coincident.

    This function compares the endpoints of two wires and determines if any
    of the endpoints match. It returns a tuple describing which endpoints are coincident.
    Args:
        wire1 (dict): Dictionary containing the first wire's data including coordinates
        wire2 (dict): Dictionary containing the second wire's data including coordinates

    Returns:
        tuple[int, int]: A tuple of integers (wire1_endpoint, wire2_endpoint) where
                          wire1_endpoint is 1 for start and 2 for end of wire1,
                          and wire2_endpoint is 1 for start and 2 for end of wire2.
                         Returns (0, 0) if no coincident endpoints found.
    """
    # Check if wire1 start coincides with wire2 start
    if (wire1['x1'] == wire2['x1'] and
        wire1['y1'] == wire2['y1']):
        return (1, 1)
    # Check if wire1 start coincides with wire2 end
    if (wire1['x1'] == wire2['x2'] and
        wire1['y1'] == wire2['y2']):
        return (1, 2)

    # Check if wire1 end coincides with wire2 start
    if (wire1['x2'] == wire2['x1'] and
        wire1['y2'] == wire2['y1']):
        return (2, 1)
    # Check if wire1 end coincides with wire2 end
    if (wire1['x2'] == wire2['x2'] and
        wire1['y2'] == wire2['y2']):
        return (2, 2)

    # No coincident endpoints found
    return (0, 0)


def are_wire_endpoints_near(wire1: dict, wire2: dict, epsilon: float) -> tuple[int, int]:
    """
    Check if any endpoints of two wires are near each other within a given epsilon distance.

    This function compares the endpoints of two wires and determines if any
    of the endpoints are within the specified epsilon distance of each other.
    It returns a tuple describing which endpoints are near.

    Args:
        wire1 (dict): Dictionary containing the first wire's data including coordinates
        wire2 (dict): Dictionary containing the second wire's data including coordinates
        epsilon (float): Maximum distance allowed between endpoints to be considered near

    Returns:
        tuple[int, int]: A tuple of integers (wire1_endpoint, wire2_endpoint) where
                          wire1_endpoint is 1 for start and 2 for end of wire1,
                          and wire2_endpoint is 1 for start and 2 for end of wire2.
                         Returns (0, 0) if no near endpoints found.
    """
    # Check if wire1 start is near wire2 start
    distance1 = math.sqrt((wire1['x1'] - wire2['x1'])**2 + (wire1['y1'] - wire2['y1'])**2)
    if distance1 < epsilon:
        return (1, 1)
    
    # Check if wire1 start is near wire2 end
    distance2 = math.sqrt((wire1['x1'] - wire2['x2'])**2 + (wire1['y1'] - wire2['y2'])**2)
    if distance2 < epsilon:
        return (1, 2)

    # Check if wire1 end is near wire2 start
    distance3 = math.sqrt((wire1['x2'] - wire2['x1'])**2 + (wire1['y2'] - wire2['y1'])**2)
    if distance3 < epsilon:
        return (2, 1)
    
    # Check if wire1 end is near wire2 end
    distance4 = math.sqrt((wire1['x2'] - wire2['x2'])**2 + (wire1['y2'] - wire2['y2'])**2)
    if distance4 < epsilon:
        return (2, 2)

    # No near endpoints found
    return (0, 0)


def wire_length(wire: dict) -> float:
    """Calculate the length of the wire segment.
    
    Args:
        wire (dict): Wire dictionary
        
    Returns:
        float: Length of the wire or arc.
    """
    curve = wire.get('curve', 0)
    if curve == 0:
        dx = wire['x2'] - wire['x1']
        dy = wire['y2'] - wire['y1']
        return (dx**2 + dy**2)**0.5
    else:
        return abs(curve * math.pi / 180.0) * wire['radius']


def walk_along_wire(wire: dict, starting_point: tuple[float, float], distance: float) -> tuple[float, float]:
    """Calculate a point along a wire segment at a specified distance from a starting point.

    Args:
        wire (dict): Wire dictionary
        starting_point (tuple): (x, y) coordinates of the starting point
        distance (float): Distance to walk along the wire

    Returns:
        tuple: (x, y) coordinates of the new point
    """
    curve = wire.get('curve', 0)
    if curve == 0:
        length = wire_length(wire)
        if length == 0:
            raise ZeroDivisionError("Wire segment has zero length")
        
        # Calculate direction vector
        ux = (wire['x2'] - wire['x1']) / length
        uy = (wire['y2'] - wire['y1']) / length

        # Check if the starting point is on the wire segment
        t = ((starting_point[0] - wire['x1']) * ux + (starting_point[1] - wire['y1']) * uy) / length
        if t < -1e-7 or t > 1.0000001:
            raise ValueError("Starting point is not on the wire segment")

        # Calculate the new point along the wire at the specified distance
        new_x = starting_point[0] + (distance * ux)
        new_y = starting_point[1] + (distance * uy)
        return new_x, new_y
    else:
        xc, yc = wire['xc'], wire['yc']
        radius = wire['radius']
        
        # Current angle
        theta_start = math.atan2(starting_point[1] - yc, starting_point[0] - xc)
        
        # Check if the starting point is on the arc segment
        theta1 = math.atan2(wire['y1'] - yc, wire['x1'] - xc)
        diff = theta_start - theta1
        curve_rad = curve * math.pi / 180.0
        
        if curve > 0:
            while diff < 0: diff += 2 * math.pi
            while diff > 2 * math.pi - 1e-7: diff -= 2 * math.pi
            if diff > curve_rad + 1e-7:
                raise ValueError("Starting point is not on the arc segment")
        else:
            while diff > 0: diff -= 2 * math.pi
            while diff < -2 * math.pi + 1e-7: diff += 2 * math.pi
            if diff < curve_rad - 1e-7:
                raise ValueError("Starting point is not on the arc segment")

        # Angular displacement
        d_theta = distance / radius if radius != 0 else 0
        new_theta = theta_start + (d_theta if curve > 0 else -d_theta)
            
        return xc + radius * math.cos(new_theta), yc + radius * math.sin(new_theta)


def build_wire_trees(wires: list) -> list[treelib.Tree]:
    """Build connected component trees from wire segments using the treelib library.

    This method groups connected wire segments into treelib trees where each tree
    represents a connected component of wires. For each tree, the wire with the 
    most negative X coordinate endpoint is used as the root of the tree.

    Args:
        wires (list): List of wire dictionaries with x1, y1, x2, y2 coordinates

    Returns:
        list: List of treelib.Tree objects
    """
    if not wires:
        return []

    # Create a mapping of wire endpoints to wire indices
    endpoint_to_wires = {}
    for i, wire in enumerate(wires):
        p1 = (wire['x1'], wire['y1'])
        p2 = (wire['x2'], wire['y2'])
        for p in [p1, p2]:
            if p not in endpoint_to_wires:
                endpoint_to_wires[p] = []
            endpoint_to_wires[p].append(i)

    visited = set()
    treelib_trees = []

    # Find connected components and build trees
    for i in range(len(wires)):
        if i in visited:
            continue

        # Identify all wires in this connected component (BFS to collect indices)
        component_indices = set()
        stack = [i]
        visited.add(i)
        while stack:
            curr_idx = stack.pop()
            component_indices.add(curr_idx)
            wire = wires[curr_idx]
            for p in [(wire['x1'], wire['y1']), (wire['x2'], wire['y2'])]:
                for neighbor_idx in endpoint_to_wires.get(p, []):
                    if neighbor_idx not in visited:
                        visited.add(neighbor_idx)
                        stack.append(neighbor_idx)

        # Choose a random root - the tree will be re-rooted later anyway
        root_idx = min(component_indices)

        # Create the treelib tree
        tree = treelib.Tree()
        tree.create_node(tag=f"Wire {root_idx}", identifier=root_idx, data=wires[root_idx])

        # Build the tree structure using BFS from the root
        bfs_queue = [root_idx]
        added_to_tree = {root_idx}
        while bfs_queue:
            parent_idx = bfs_queue.pop(0)
            parent_wire = wires[parent_idx]
            # Check neighbors of the parent wire via its endpoints
            for p in [(parent_wire['x1'], parent_wire['y1']), (parent_wire['x2'], parent_wire['y2'])]:
                for neighbor_idx in endpoint_to_wires.get(p, []):
                    if neighbor_idx in component_indices and neighbor_idx not in added_to_tree:
                        tree.create_node(tag=f"Wire {neighbor_idx}", 
                                        identifier=neighbor_idx, 
                                        parent=parent_idx, 
                                        data=wires[neighbor_idx])
                        added_to_tree.add(neighbor_idx)
                        bfs_queue.append(neighbor_idx)
        
        treelib_trees.append(tree)

    return treelib_trees


def normalize_wire_trees(trees: list[treelib.Tree]) -> list[treelib.Tree]:
    """Standardize wire trees by finding leaves and selecting the leftmost unconnected end as the new root.

    This method processes each tree to identify all leaf nodes (nodes with no children) and then
    selects the leaf with the leftmost (minimum x-coordinate) unconnected end to become the new root.
    This ensures a consistent starting point for processing each connected component, especially
    when dealing with complex wire geometries where the original root might not be ideal for
    subsequent operations like stitching or offsetting.

    Args:
        trees (list[treelib.Tree]): List of treelib.Tree objects representing connected wire components

    Returns:
        list[treelib.Tree]: List of normalized treelib.Tree objects with potentially new roots
    """
    def reroot_tree(old_tree: treelib.Tree, leaf_id: str):
        #self.log_to_console(old_tree.show(stdout=False)) # type: ignore
        
        # 1. Get path from leaf up to root: [leaf, ..., parent, root]
        path = list(old_tree.rsearch(leaf_id))
        new_tree = treelib.Tree()
        
        # 2. add the old leaf as the new root
        new_root_node = old_tree[leaf_id]
        new_tree.create_node(new_root_node.tag, new_root_node.identifier, parent=None, data=new_root_node.data)

        # 3. Add the rest of the path, using the PREVIOUSLY added node as the parent
        for i in range(len(path) - 1):
            child_id = path[i+1] # The node that will become a child in the new tree
            parent_id = path[i]  # The node we just added
            
            node_to_add = old_tree[child_id]
            new_tree.create_node(node_to_add.tag, node_to_add.identifier, parent=parent_id, data=node_to_add.data)
        
            # 4. Handle side-branches (neighbors not on the main path)
            for child in old_tree.children(child_id):
                if child.identifier not in path:
                    # subtree() creates a copy of the branch
                    branch = old_tree.subtree(child.identifier)
                    new_tree.paste(child_id, branch)
                    
        return new_tree


    normalized_trees = []
    for tree in trees:
        if not tree:
            continue

        # Find all leaf nodes (nodes with no children)
        leaves = tree.leaves()
        root_id = tree.root
        if root_id and tree.children(root_id).count == 1:
                leaves.append(tree.get_node(tree.root)) # type: ignore

        # Find the leaf with the leftmost unconnected end
        leftmost_leaf = None
        min_x = float('inf')
        for leaf in leaves:
            wire = leaf.data
            # Check both endpoints of the wire for the leaf
            x1, x2 = wire['x1'], wire['x2']
            leaf_x = min(x1, x2)
            if leaf_x < min_x:
                min_x = leaf_x
                leftmost_leaf = leaf

        # If we found a leftmost leaf, make it the new root
        if leftmost_leaf and leftmost_leaf.identifier != tree.root:
            # Create a new tree with the leftmost leaf as root
            normalized_trees.append(reroot_tree(tree, leftmost_leaf.identifier))
        else:
            # No change needed, keep the original tree
            normalized_trees.append(tree)
    return normalized_trees