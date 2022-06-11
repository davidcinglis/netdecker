from abc import ABC, abstractmethod
from google.cloud import vision
from netdecker.text_storage import Textbox, BoundingBox
from typing import List

class OCRResponse:
    def __init__(self, success: bool, textboxes: List[Textbox], 
                 error_message: str = None):
        self.success = success
        self.textboxes = textboxes
        self.error_message = error_message

class OCR(ABC):

    @abstractmethod
    def detect_text_uri(self, b64_img) -> OCRResponse:
        """ Takes a uri to an image and converts the OCR result into the
            proper Textbox format.

        Args:
            uri (str): The link to the image being processed.

        Returns:
            List[Textbox]: A list of textbox objects for each line of text
                           in the image.
        """
        pass


class GoogleOCR(OCR):

    def detect_text_uri(self, img_b64):
        """ Google Cloud Vision implementation of the decklist ocr.
        """
        ocr_response = OCRResponse(True, [], None)

        client = vision.ImageAnnotatorClient()
        image = vision.Image(content=img_b64)
        response = client.text_detection(image=image)

        if response.error.message:
            ocr_response.success = False
            ocr_response.error_message = response.error.message
        
        else:
            words = response.text_annotations[1:]
            current_textbox = Textbox()
            for word in words:
                curr_bounds = BoundingBox.init_from_bounding_poly(word.bounding_poly)
                if not current_textbox.isAdjacent(curr_bounds):
                    ocr_response.textboxes.append(current_textbox)
                    current_textbox = Textbox()
                current_textbox.addWord(curr_bounds, word.description)
            ocr_response.textboxes.append(current_textbox)
        
        return ocr_response
