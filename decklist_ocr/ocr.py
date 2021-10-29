from abc import ABC, abstractmethod
from google.cloud import vision
from decklist_ocr.text_storage import Textbox, BoundingBox
from typing import List


class OCR(ABC):

    @abstractmethod
    def detect_text_uri(self, uri: str) -> List[Textbox]:
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

    def detect_text_uri(self, uri):
        """ Google Cloud Vision implementation of the decklist ocr.
        """
        client = vision.ImageAnnotatorClient()
        image = vision.Image()
        image.source.image_uri = uri
        response = client.document_text_detection(image=image)
        document = response.full_text_annotation

        textboxes = []
        for page in document.pages:
            for block in page.blocks:
                for paragraph in block.paragraphs:
                    # Iterate through each word in the paragraph.
                    # If it's on the same line as the previous word,
                    # join them together into a textbox.
                    # Otherwise start a new textbox.
                    current_textbox = Textbox()
                    for word in paragraph.words:
                        word_text = ''.join([symbol.text for symbol in word.symbols])
                        curr_bounds = BoundingBox.init_from_bounding_poly(word.bounding_box)
                        if not current_textbox.isAdjacent(curr_bounds):
                            textboxes.append(current_textbox)
                            current_textbox = Textbox()
                        current_textbox.addWord(curr_bounds, word_text)
                    textboxes.append(current_textbox)
                
        return textboxes
