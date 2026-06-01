from dataclasses import dataclass, field
import concurrent.futures
import logging
import fitz
import os
import io
import cv2
import numpy as np
from PIL import Image
from utils.clean_text import text_cleaner
from helpers.config import get_settings
from stores.ocr.ocr_factory import OCRFactory

settings = get_settings()
@dataclass
class Document:
    page_content: str
    metadata: dict = field(default_factory=dict)


    def __repr__(self) -> str:
        pg = self.metadata.get("page", "?")
        pt = self.metadata.get("page_type", "?")
        return f"<Document page={pg} type={pt} chars={len(self.page_content)}>"


class pdf_loader:
    MAX_WORKERS = 4  # parallel pages — tune to your CPU/network

    def __init__(self, file_path: str):
        self.file_path = str(file_path)
        self.model = OCRFactory.create_provider(settings.OCR_BACKEND)
        self.logger= logging.getLogger(__name__)
    def load(self) -> list[Document]:
        """Load all pages in parallel. Returns one Document per page."""
        doc = fitz.open(self.file_path)
        total_pages = len(doc)

        self.logger.info(f"Opened '{self.file_path}' — {total_pages} page(s)")

        pdf_meta = self._extract_pdf_metadata(doc)

        # ── Rasterise all pages up-front while fitz doc is open ───────
        # (fitz is not thread-safe, so we extract data before threading)
        page_data_list = []

        for page_index in range(total_pages):
            fitz_page = doc[page_index]

            # Extract blocks (text + embedded images) synchronously
            blocks = fitz_page.get_text("dict")["blocks"]

            # Pre-decode image bytes while fitz page is in scope
            decoded_blocks = self._decode_blocks(blocks)

            fitz_page = doc[page_index]

            pix = fitz_page.get_pixmap(matrix=fitz.Matrix(2, 2))

            img = Image.frombytes(
                "RGB",
                [pix.width, pix.height],
                pix.samples
            )

            page_data_list.append((page_index + 1, decoded_blocks, img))
        doc.close()

        # ── Process pages in parallel (OCR is the bottleneck) ─────────
        documents = [None] * total_pages

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as executor:
            futures = {
                executor.submit(
                    self._process_page_data,
                    page_num,
                    decoded_blocks,
                    raster,
                    total_pages,
                    pdf_meta,
                ): page_index
                for page_index, (page_num, decoded_blocks, raster) in enumerate(page_data_list)
            }

            for future in concurrent.futures.as_completed(futures):
                page_index = futures[future]
                try:
                    documents[page_index] = future.result()
                except Exception as exc:
                    page_num = page_data_list[page_index][0]
                    self.logger.error(f"Page {page_num} failed: {exc}")
                    documents[page_index] = self._error_doc(
                        page_num, total_pages, pdf_meta, str(exc)
                    )

        return documents

    def load_as_text(self) -> str:
        return "\n\n".join(d.page_content for d in self.load() if d.page_content)

    def _decode_blocks(self, blocks: list) -> list:
        """
        Resolve image bytes from fitz blocks so threads don't need to touch
        the (non-thread-safe) fitz document.
        Returns a simplified list of dicts.
        """
        decoded = []

        for block in blocks:
            if block["type"] == 0:
                # Text block — just copy
                decoded.append({"type": 0, "lines": block.get("lines", [])})

            elif block["type"] == 1:
                w = block.get("width", 0)
                h = block.get("height", 0)

                if w < 50 or h < 50:
                    continue

                img_bytes = block.get("image")
                if not img_bytes:
                    continue

                decoded.append(
                    {
                        "type": 1,
                        "img_bytes": bytes(img_bytes),
                        "bbox": block.get("bbox", [0, 0, 0, 0]),
                        "width": w,
                        "height": h,
                    }
                )

        return decoded

    # ──────────────────────────────────────────
    # Per-page processing (runs in thread)
    # ──────────────────────────────────────────
    def _process_page_data(
        self,
        page_num: int,
        total_pages: int,
        pdf_meta: dict,
        decoded_blocks: list = None,
        raster: Image.Image = None,
    ) -> Document:

        content = []
        image_meta = []
        has_ocr = False

        # ── Full-page OCR (Arabic mode) ───────────────────────────
        ocr_text = self._run_ocr(raster, page_num)
        has_ocr = True

        cleaned = self._clean(ocr_text)
        if cleaned:
            content.append(cleaned)

        page_type = "scanned"

        # ── Block-by-block (normal mode) ──────────────────────────
        for block in decoded_blocks:
            if block["type"] == 0:
                text = ""
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text += span.get("text", "") + " "

                if text.strip():
                    cleaned = self._clean(text)
                    if cleaned:
                        content.append(cleaned)

            elif block["type"] == 1:
                try:
                    pil_img = Image.open(
                        io.BytesIO(block["img_bytes"])
                    ).convert("RGB")

                    ocr_text = self._run_ocr(pil_img, page_num)
                    has_ocr = True

                    cleaned = self._clean(ocr_text)
                    if cleaned:
                        content.append(cleaned)

                    bbox = block["bbox"]
                    image_meta.append(
                        {
                            "pdf_bbox": {
                                "x0": bbox[0],
                                "y0": bbox[1],
                                "x1": bbox[2],
                                "y1": bbox[3],
                            },
                            "width": block["width"],
                            "height": block["height"],
                        }
                    )

                except Exception as exc:
                    self.logger.warning(f"Page {page_num}: image block error — {exc}")

        # ── Fallback: page had no extractable content ─────────────
        if not content:
            self.logger.info(f"Page {page_num}: empty blocks — needs full-page OCR")
            page_type = "scanned"
        else:
            page_type = "hybrid" if has_ocr else "text"

        cleaned_page = self._clean(" ".join(content))
        image_count = len(image_meta)

        self.logger.info(f"Page {page_num} [{page_type}]: {len(cleaned_page)} chars")

        return Document(
            page_content=cleaned_page,
            metadata={
                **pdf_meta,
                "page": page_num,
                "total_pages": total_pages,
                "page_type": page_type,
                "has_images": image_count > 0,
                "image_count": image_count,
                "char_count": len(cleaned_page),
                "images": image_meta,
                "error": None,
            },
        )

    def _extract_pdf_metadata(self, doc: fitz.Document) -> dict:
        raw = doc.metadata or {}
        return {
            "source": os.path.abspath(self.file_path),
            "file_name": os.path.basename(self.file_path),
            "pdf_title": raw.get("title", ""),
        }

    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        binary = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11,
            2,
        )

        return cv2.bitwise_not(binary)

    def _preprocess_image_pil(self, pil_img: Image.Image) -> Image.Image:
        np_bgr = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        processed = self.preprocess_image(np_bgr)
        rgb = cv2.cvtColor(processed, cv2.COLOR_GRAY2RGB)
        return Image.fromarray(rgb)

    def _run_ocr(self, pil_img: Image.Image, page_num: int) -> str:
        try:
            ocr_response = self.model.recognize_text(pil_img)
            return "\n".join(page.markdown for page in ocr_response.pages)
        except Exception as exc:
            self.logger.error(
                f"Model OCR do not found image on page {page_num}: {exc}"
            )
            return ""

    def _clean(self, text: str) -> str:
        return text_cleaner(text)

    def _error_doc(self, page_num, total_pages, pdf_meta, error_msg) -> Document:
        return Document(
            page_content="",
            metadata={
                **pdf_meta,
                "page": page_num,
                "total_pages": total_pages,
                "page_type": "error",
                "has_images": False,
                "image_count": 0,
                "char_count": 0,
                "images": [],
                "error": error_msg,
            },
        )