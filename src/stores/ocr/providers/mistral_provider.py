import base64
import io
import importlib
import logging
from PIL import Image
from helpers.config import get_settings

logger = logging.getLogger(__name__)


def _load_mistral_class():
    try:
        # Preferred import if available
        from mistralai import Mistral  # type: ignore

        return Mistral
    except Exception:
        try:
            pkg = importlib.import_module("mistralai")
        except Exception:
            return None

        # Try several possible client class names used by different versions
        for name in ("Mistral", "MistralClient", "Client"):
            cls = getattr(pkg, name, None)
            if cls:
                return cls

        return None


class MistralProvider:
    def __init__(self, api_key):
        MistralClass = _load_mistral_class()
        if MistralClass is None:
            logger.error("mistralai package is not available or has an unexpected API")
            raise ImportError("mistralai client class not found; check installation and API")

        # instantiate the client using common constructor patterns
        try:
            self.client = MistralClass(api_key=api_key)
        except TypeError:
            # fallback: some clients expect a dict or different kwarg name
            try:
                self.client = MistralClass(key=api_key)
            except Exception as exc:
                logger.error(f"Failed to instantiate mistralai client: {exc}")
                raise

    def recognize_text(self, image: Image.Image):
        """
        Recognize text from a PIL.Image object.
        image: already processed PIL.Image
        Returns: OCR response from Mistral
        """

        # Convert image to JPEG bytes
        buffer = io.BytesIO()
        image.convert("RGB").save(buffer, format="JPEG")
        img_bytes = buffer.getvalue()

        # Encode as base64
        b64 = base64.b64encode(img_bytes).decode("utf-8")

        # Send to Mistral OCR
        ocr_response = self.client.ocr.process(
            model="mistral-ocr-latest",
            document={
                "type": "image_url",  # base64 can be sent as an image_url
                "image_url": f"data:image/jpeg;base64,{b64}",
            },
            include_image_base64=False,
        )

        return ocr_response