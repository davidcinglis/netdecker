import math
import pytest
from netdecker.text_storage import BoundingBox, Vertex, Textbox

@pytest.fixture
def left_box():
    v1 = Vertex(0, 0)
    v2 = Vertex(3, 0)
    v3 = Vertex(3, 2)
    v4 = Vertex(0, 2)

    return BoundingBox(v1, v2, v3, v4)

@pytest.fixture
def right_box():
    v1 = Vertex(4, 0)
    v2 = Vertex(7, 0)
    v3 = Vertex(7, 2)
    v4 = Vertex(4, 2)

    return BoundingBox(v1, v2, v3, v4)

def test_vertex():
    v1 = Vertex(0, 0)
    v2 = Vertex(3, 4)

    assert v1.y_delta(v2) == 4
    assert v2.y_delta(v1) == 4

    assert v1.x_delta(v2) == 3
    assert v2.x_delta(v1) == 3

    assert v1.distance(v2) == 5
    assert v2.distance(v1) == 5

    vmid = Vertex(5, 1)

    assert vmid.vertical_is_between(v1, v2)
    assert not v2.vertical_is_between(vmid, v1)
    assert not vmid.vertical_is_between(v2, v1)
    assert not v1.vertical_is_between(v2, vmid)

def test_bounding_box(left_box, right_box):
    assert left_box.get_height() == 2

    # horizontal distance 1 with height 2 is within the adjacency threshold
    assert left_box.isAdjacent(right_box)
    assert not right_box.isAdjacent(left_box)

    right_box.upper_left_vertex.x = 5
    right_box.lower_left_vertex.x = 5
    # horizontal distance 2 with height 2 is on the border of the threshold
    assert left_box.isAdjacent(right_box)

    # now with horizontal distance 3 we should no longer be adjacent
    right_box.upper_left_vertex.x = 6
    right_box.lower_left_vertex.x = 6

    assert not left_box.isAdjacent(right_box)

def test_textbox(left_box, right_box):
    t1 = Textbox()
    t1.addWord(left_box, "one")
    t1.addWord(right_box, "two")

    assert t1.text == "one two"
    assert t1.bounding_box.upper_right_vertex.x == 7
    assert t1.bounding_box.lower_right_vertex.x == 7
    assert t1.bounding_box.upper_left_vertex.x == 0
    assert t1.bounding_box.lower_left_vertex.x == 0




