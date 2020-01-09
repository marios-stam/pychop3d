import numpy as np
import trimesh
import json

from pychop3d import section
from pychop3d import bsp
from pychop3d.configuration import Configuration


def open_mesh():
    config = Configuration.config
    mesh = trimesh.load(config.mesh)
    trimesh_repair(mesh)
    if config.scale:
        if hasattr(config, 'scale_factor'):
            factor = config.scale_factor
            print(f"Configured scale factor: {factor}")
        else:
            factor = int(np.ceil(1.1 / np.max(mesh.bounding_box_oriented.primitive.extents / config.printer_extents)))
            config.scale_factor = factor
            print(f"Calculated scale factor: {factor}")
        if factor > 1:
            mesh.apply_scale(factor)
    if hasattr(config, 'subdivision_resolution'):
        if config.subdivision_resolution > 0:
            vertices, faces = trimesh.remesh.subdivide_to_size(mesh.vertices, mesh.faces, config.subdivision_resolution)
            mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=True)

    return mesh


def open_tree(tree_file):
    mesh = open_mesh()
    with open(tree_file) as f:
        data = json.load(f)

    node_data = data['nodes']
    tree = bsp.BSPTree(mesh)
    for n in node_data:
        plane = (np.array(n['origin']), np.array(n['normal']))
        node = tree.get_node(n['path'])
        tree = tree.expand_node(plane, node)
    return tree


def all_at_goal(trees):
    for tree in trees:
        if not tree.terminated():
            return False
    return True


def not_at_goal_set(trees):
    not_at_goal = []
    for tree in trees:
        if not tree.terminated():
            not_at_goal.append(tree)
    return not_at_goal


def get_unique_normals(non_unique_normals):
    rounded = np.round(non_unique_normals, 3)
    view = rounded.view(dtype=[('', float), ('', float), ('', float)])
    unique = np.unique(view)
    return unique.view(dtype=float).reshape((unique.shape[0], -1))


def make_plane(origin, normal, w=100):
    xform = np.linalg.inv(trimesh.points.plane_transform(origin, normal))
    box = trimesh.primitives.Box(extents=(w, w, .5), transform=xform)
    return box


def trimesh_repair(mesh):
    trimesh.repair.fill_holes(mesh)
    trimesh.repair.fix_winding(mesh)
    trimesh.repair.fix_inversion(mesh)
    trimesh.repair.fix_normals(mesh)
