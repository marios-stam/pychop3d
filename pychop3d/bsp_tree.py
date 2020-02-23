import trimesh
import numpy as np
import copy

from pychop3d.configuration import Configuration
from pychop3d import bsp_node


class BSPTree:

    def __init__(self, part: trimesh.Trimesh):
        config = Configuration.config
        self.nodes = [bsp_node.BSPNode(part)]
        self._node_data = {}

        theta_0 = self.nodes[0].n_parts
        nparts = sum([l.n_parts for l in self.leaves]) / theta_0

        V = np.prod(config.printer_extents)
        if config.obb_utilization:
            utilization = max(
                [1 - leaf.obb.volume / (leaf.n_parts * V) for leaf in self.leaves])
        else:
            utilization = max([1 - leaf.part.volume / (leaf.n_parts * V) for leaf in self.leaves])

        self.objectives = {
            'nparts': nparts,
            'utilization': utilization,
            'connector': 0,  # no connectors yet
            'fragility': 0,
            'seam': 0,
            'symmetry': 0
        }

    def copy(self):
        new_tree = copy.deepcopy(self)
        return new_tree

    def get_node(self, path=None):
        node = self.nodes[0]
        if not path:
            return node
        else:
            for i in path:
                node = node.children[i]
        return node

    @property
    def leaves(self):
        nodes = [self.nodes[0]]
        leaves = []
        while nodes:
            node = nodes.pop()
            if len(node.children) == 0:
                leaves.append(node)
            else:
                nodes += node.children
        return leaves

    @property
    def terminated(self):
        for leaf in self.leaves:
            if not leaf.terminated:
                return False
        return True

    @property
    def largest_part(self):
        return sorted(self.leaves, key=lambda x: x.n_parts)[-1]

    def sufficiently_different(self, node, tree_set):
        if not tree_set:
            return True
        for tree in tree_set:
            if not self.different_from(tree, node):
                self.different_from(tree, node)
                return False
        return True

    def different_from(self, tree, node):
        self_node = self.get_node(node.path)
        other_node = tree.get_node(node.path)
        return self_node.different_from(other_node)

    @property
    def objective(self):
        config = Configuration.config
        part = config.objective_weights['part'] * self.objectives['nparts']
        util = config.objective_weights['utilization'] * self.objectives['utilization']
        connector = config.objective_weights['connector'] * self.objectives['connector']
        fragility = config.objective_weights['fragility'] * self.objectives['fragility']
        seam = config.objective_weights['seam'] * self.objectives['seam']
        symmetry = config.objective_weights['symmetry'] * self.objectives['symmetry']
        return part + util + connector + fragility + seam + symmetry


def expand_node(tree, path, plane):
    """

    :param tree:
    :param path:
    :param plane:
    :return:
    """
    new_tree = tree.copy()
    new_node = new_tree.get_node(path)
    new_node, result = bsp_node.split(new_node, plane)
    if result != 'success':
        return None, result
    new_tree.nodes += new_node.children
    return new_tree, result


def get_planes(part, normal):
    """get all planes in the form of (origin, normal) pairs corresponding to valid cuts of the input part. Planes are
    in the direction specified by `normal` and are spaced according to the `plane_spacing` configuration parameter.

    :param part: object to determine valid cutting planes for
    :type part: `trimesh.Trimesh`
    :param normal: unit vector defining the normal vector for the planes
    :type normal: (3, ) shape `numpy.ndarray`
    :return: list of all valid cutting planes for the input object
    :rtype: list
    """
    config = Configuration.config  # collect configuration
    projection = part.vertices @ normal  # project all vertices of the input object onto the input normal vector
    # determine the extent of the object in the direction defined by the normal vector
    limits = [projection.min(), projection.max()]
    # create planes spaced out according to the configuration
    planes = [(d * normal, normal) for d in np.arange(limits[0], limits[1], config.plane_spacing)][1:]
    if config.add_middle_plane:  # add the middle plane
        planes += [(normal * (projection.min() + projection.max()) / 2, normal)]  # add a plane through the middle
    return planes
