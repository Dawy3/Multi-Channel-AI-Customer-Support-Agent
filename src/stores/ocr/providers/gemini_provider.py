import io
from google import genai
from PIL import Image
from ..ocr_enums import GemenaiOCRModels


class GeminiProvider:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)

    def recognize_text(self, image: Image.Image):
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        img_bytes = buffer.getvalue()

        response = self.client.models.generate_content(
            model=GemenaiOCRModels.GEMENAI_Model,
            contents=[
                "You are an OCR engine. Output only raw detected text. "
                "Do not reason, explain, or summarize.",
                genai.types.Part.from_bytes(
                    data=img_bytes,
                    mime_type="image/png",
                ),
            ],
            config={
                "temperature": GemenaiOCRModels.TEMPERATURE,
                "top_p": GemenaiOCRModels.TOP_P,
                "max_output_tokens": GemenaiOCRModels.GENERATION_DEFAULT_MAX_TOKENS,
            },
        )

        return response.text if response else ""