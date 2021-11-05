from __future__ import annotations
import math
from google.cloud.vision_v1.types.geometry import BoundingPoly
ADJACENCY_THRESHOLD = 3

class Vertex:
    """ Class to store a single point on the image being parsed.
    """
    def __init__(self, x: int, y: int) -> None:
        self.x = x
        self.y = y

    def y_delta(self, target: Vertex) -> int:
        return abs(self.y - target.y)

    def x_delta(self, target: Vertex) -> int:
        return abs(self.x - target.x)

    def distance(self, target: Vertex) -> float:
        return math.sqrt((self.x_delta(target) ** 2 + 
                          self.y_delta(target) ** 2))
    
class BoundingBox:
    """ Class to store the bounds of a piece of text. 
        Stores a Vertex object for each corner.
    """
    def __init__(self, upper_left_vertex, upper_right_vertex, 
                 lower_right_vertex, lower_left_vertex) -> None:
        self.upper_left_vertex = upper_left_vertex
        self.upper_right_vertex = upper_right_vertex
        self.lower_right_vertex = lower_right_vertex
        self.lower_left_vertex = lower_left_vertex
    
    @classmethod
    def init_from_bounding_poly(cls, bounding_poly: BoundingPoly):
        """Creates a BoundingBox from google cloud vision's BoundingPoly.
            Args:
                bounding_poly (BoundingPoly): Polygon object with vertices 
                stored as an array in clockwise order
                from the upper left vertex.

            Returns:
                BoundingBox: The instantiated BoundingBox object.
        """
        upper_left = Vertex(bounding_poly.vertices[0].x, 
                            bounding_poly.vertices[0].y)
        upper_right = Vertex(bounding_poly.vertices[1].x, 
                             bounding_poly.vertices[1].y)
        lower_right = Vertex(bounding_poly.vertices[2].x, 
                             bounding_poly.vertices[2].y)
        lower_left = Vertex(bounding_poly.vertices[3].x, 
                            bounding_poly.vertices[3].y)
        return cls(upper_left, upper_right, lower_right, lower_left)

    def get_height(self):
        return self.lower_left_vertex.y - self.upper_left_vertex.y

    def isAdjacent(self, candidate: BoundingBox):
        return self.upper_right_vertex.y_delta(candidate.upper_left_vertex) <= ADJACENCY_THRESHOLD and \
               self.lower_right_vertex.y_delta(candidate.lower_left_vertex) <= ADJACENCY_THRESHOLD
    
    def serialize(self):
        return "(%d, %d)" % (self.upper_left_vertex.x, self.upper_left_vertex.y)

    
class Textbox:
    """ Class for representing a chunk of text in a parsed image.

        Atributes:
            bounding_box (BoundingBox): the bounds of the text chunk.
            text (str): The text chunk.
    """
    def __init__(self, bounding_box=None, text=None) -> None:
        self.bounding_box = bounding_box
        self.text = text

    def addWord(self, bounding_box, text):
        if not self.bounding_box:
            self.bounding_box = bounding_box
        else:
            # Since we're only storing single lines of text we only have to
            # update the x coordinate.
            self.bounding_box.upper_right_vertex.x = bounding_box.upper_right_vertex.x
            self.bounding_box.lower_right_vertex.x = bounding_box.lower_right_vertex.x
        
        if not self.text:
            self.text = text
        else:
            self.text += ' '  + text
    
    def isAdjacent(self, candidate: BoundingBox):
        if not self.bounding_box:
            return True
        else:
            return self.bounding_box.isAdjacent(candidate)
 