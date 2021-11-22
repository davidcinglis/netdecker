from __future__ import annotations
import math
from google.cloud.vision_v1.types.geometry import BoundingPoly

# The maximum distance gap tolerated between two words,
# when determining whether they are adjacent.
# Measured as a ratio to the height of the word.
MAX_VERTICAL_GAP = .2
MAX_HORIZONTAL_GAP = 1

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

    def vertical_is_between(self, v1, v2):
        return v1.y <= self.y <= v2.y

    
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
        vertical_check = self.upper_right_vertex.vertical_is_between(candidate.upper_left_vertex, candidate.lower_left_vertex) or \
                         candidate.upper_left_vertex.vertical_is_between(self.upper_right_vertex, self.lower_right_vertex)
        upper_x_delta = self.upper_right_vertex.x_delta(candidate.upper_left_vertex)
        lower_x_delta = self.lower_right_vertex.x_delta(candidate.lower_left_vertex)
        mean_x_delta = (upper_x_delta + lower_x_delta) / 2
        horizontal_check = mean_x_delta / self.get_height() <= MAX_HORIZONTAL_GAP
        return vertical_check and horizontal_check
    
    def serialize(self):
        return "(%d, %d) to (%d, %d)" % \
        (self.upper_left_vertex.x, self.upper_left_vertex.y,
        self.lower_right_vertex.x, self.lower_right_vertex.y)

    
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
            self.text += ' ' + text
    
    def isAdjacent(self, candidate: BoundingBox):
        if not self.bounding_box:
            return True
        elif self.bounding_box.get_height() == 0:
            return False
        else:
            return self.bounding_box.isAdjacent(candidate)
 