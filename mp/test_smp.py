import pytest
import torch

from mp.smp import ChainMessagePassing
from torch_geometric.nn.conv import MessagePassing
from data.dummy_complexes import get_square_dot_complex


def test_propagate_in_cmp():
    """We build a graph in the shape of a house (a triangle on top of a square)
    and test propagation at the edge level."""

    # [0, 1, 2] are the edges that form the triangle. They are all upper adjacent.
    up_index = torch.tensor([[0, 1, 0, 2, 1, 2],
                             [1, 0, 2, 0, 2, 1]], dtype=torch.long)
    # A feature for each common triangle shared by the edges.
    up_attr = torch.tensor([[1], [1], [2], [2], [3], [3]])

    # [2, 3, 4, 5] for the edges of the square. They are lower adjacent (share a common vertex).
    # We also need to add the edges of the triangle again because they are also lower adjacent.
    down_index = torch.tensor([[0, 1, 0, 2, 1, 2, 2, 3, 3, 4, 4, 5, 2, 5, 0, 3, 1, 5],
                               [1, 0, 2, 0, 2, 1, 3, 2, 4, 3, 5, 4, 5, 2, 3, 0, 5, 1]],
                              dtype=torch.long)
    # A feature for each common vertex.
    down_attr = torch.tensor([[1], [1], [2], [2], [3], [3], [4], [4],
                              [5], [5], [6], [6], [7], [7], [8], [8], [9], [9]])
    # We initialise the edges with dummy scalar features
    x = torch.tensor([[1], [2], [3], [4], [5], [6]], dtype=torch.float)

    # Extract the message passing object and propagate
    cmp = ChainMessagePassing(up_msg_size=1, down_msg_size=1)
    up_msg, down_msg = cmp.propagate(up_index, down_index, x=x, up_attr=up_attr, down_attr=down_attr)
    expected_updated_x = torch.tensor([[14], [14], [16], [9], [10], [10]], dtype=torch.float)

    assert torch.equal(up_msg + down_msg, expected_updated_x)


def test_propagate_at_vertex_level_in_cmp():
    """We build a graph in the shape of a house (a triangle on top of a square)
    and test propagation at the vertex level. This makes sure propagate works when
    down_index is None.
    """

    # [0, 1, 2] are the edges that form the triangle. They are all upper adjacent.
    up_index = torch.tensor([[0, 1, 0, 4, 1, 2, 1, 4, 2, 3, 3, 4],
                             [1, 0, 4, 0, 2, 1, 4, 1, 3, 2, 4, 3]], dtype=torch.long)
    # A feature for each common edge shared by the edges.
    up_attr = torch.tensor([[1], [1], [2], [2], [3], [3], [4], [4], [5], [5], [6], [6]])

    # [2, 3, 4, 5] for the edges of the square. They are lower adjacent (share a common vertex).
    # We also need to add the edges of the triangle again because they are also lower adjacent.
    down_index = None

    # We initialise the vertices with dummy scalar features
    x = torch.tensor([[1], [2], [3], [4], [5]], dtype=torch.float)

    # Extract the message passing object and propagate
    cmp = ChainMessagePassing(up_msg_size=1, down_msg_size=1)
    up_msg, down_msg = cmp.propagate(up_index, down_index, x=x, up_attr=up_attr)
    expected_updated_x = torch.tensor([[7], [9], [6], [8], [7]], dtype=torch.float)

    assert torch.equal(up_msg + down_msg, expected_updated_x)


def test_propagate_at_triangle_level_in_cmp_when_there_is_a_single_one():
    """We build a graph in the shape of a house (a triangle on top of a square)
    and test propagation at the triangle level. This makes sure that propagate works when
    up_index is None."""

    # When there is a single triangle, there is no upper or lower adjacency
    up_index = None
    down_index = None

    # We initialise the vertices with dummy scalar features
    x = torch.tensor([[1]], dtype=torch.float)

    # Extract the message passing object and propagate
    cmp = ChainMessagePassing(up_msg_size=1, down_msg_size=1)
    up_msg, down_msg = cmp.propagate(up_index, down_index, x=x)
    expected_msg = torch.tensor([[0]], dtype=torch.float)

    assert torch.equal(up_msg + down_msg, expected_msg)


def test_propagate_at_triangle_level_in_cmp():
    """We build a graph formed of two triangles sharing an edge.
    This makes sure that propagate works when up_index is None."""

    # When there is a single triangle, there is no upper or lower adjacency
    up_index = None
    down_index = torch.tensor([[0, 1],
                               [1, 0]], dtype=torch.long)
    # Add features for the edges shared by the triangles
    down_attr = torch.tensor([[1], [1]])

    # We initialise the vertices with dummy scalar features
    x = torch.tensor([[32], [17]], dtype=torch.float)

    # Extract the message passing object and propagate
    cmp = ChainMessagePassing(up_msg_size=1, down_msg_size=1)
    up_msg, down_msg = cmp.propagate(up_index, down_index, x=x, down_attr=down_attr)
    expected_updated_x = torch.tensor([[17], [32]], dtype=torch.float)

    assert torch.equal(up_msg + down_msg, expected_updated_x)


def test_smp_messaging_with_isolated_nodes():
    """
    This checks how pyG handles messages for isolated nodes. This shows that it sends a zero vector.
    """
    square_dot_complex = get_square_dot_complex()
    params = square_dot_complex.get_chain_params(dim=0)

    mp = MessagePassing()
    out = mp.propagate(edge_index=params.up_index, x=params.x)
    isolated_out = out[4]

    # This confirms pyG returns a zero message to isolated vertices
    assert torch.equal(isolated_out, torch.zeros_like(isolated_out))
    for i in range(4):
        assert not torch.equal(out[i], torch.zeros_like(out[i]))

    cmp = ChainMessagePassing(up_msg_size=1, down_msg_size=1)
    up_msg, down_msg = cmp.propagate(up_index=params.up_index, down_index=None, x=params.x, up_attr=None)
    assert torch.equal(out, up_msg)
    assert torch.equal(down_msg, torch.zeros_like(down_msg))
