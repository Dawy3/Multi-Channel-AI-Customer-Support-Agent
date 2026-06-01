from enum import Enum


class OCRTypes(str, Enum):
    MISTRAL = "MISTRAL"
    GEMENAI = "GEMENAI"

class GemenaiOCRModels(str, Enum):
    GEMENAI_Model = "gemini-1.5-flash"
    TEMPERATURE =  0.0
    TOP_P = 0.0
    GENERATION_DEFAULT_MAX_TOKENS= 1024