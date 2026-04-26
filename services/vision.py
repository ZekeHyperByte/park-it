"""Vision service — ANPR (plate recognition) and vehicle type detection.

This module provides a unified interface for camera-based analysis.
Both features use lightweight models (~21 MB total) that run on CPU.

When both ANPR and vehicle detection are enabled, they share a single
YOLO inference pass for maximum efficiency.

Dependencies (optional, installed via `pip install -e ".[vision]"`):
    - ultralytics (YOLOv8)
    - paddleocr
    - paddlepaddle (CPU)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from shared.config import get_settings
from shared.logging import get_logger

logger = get_logger("vision_service")

# COCO class names → internal vehicle type codes
COCO_TO_VEHICLE_TYPE: dict[str, str] = {
    "car": "MOBIL",
    "motorcycle": "MOTOR",
    "bus": "BUS",
    "truck": "TRUCK",
}


@dataclass
class VisionResult:
    """Result from the combined vision pipeline."""

    # ANPR
    plate_number: str | None = None
    plate_confidence: float = 0.0

    # Vehicle detection
    vehicle_type: str | None = None
    vehicle_confidence: float = 0.0

    # Raw detections for debugging
    raw_detections: list[dict[str, Any]] = field(default_factory=list)


class VisionService:
    """Lazy-loading vision service.

    Models are only loaded when first needed.  When both ANPR and vehicle
    detection are enabled, the YOLO model is shared between them.
    """

    _instance: VisionService | None = None

    def __init__(self) -> None:
        self._yolo_model: Any | None = None
        self._ocr_model: Any | None = None
        self._settings = get_settings()

    @classmethod
    def get_instance(cls) -> VisionService:
        """Return singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Lazy model loading
    # ------------------------------------------------------------------

    def _load_yolo(self) -> Any:
        """Load YOLOv8-nano model on first use."""
        if self._yolo_model is not None:
            return self._yolo_model

        try:
            from ultralytics import YOLO
        except ImportError:
            raise ImportError(
                "ultralytics is required for vision features. "
                "Install with: pip install -e '.[vision]'"
            )

        model_name = self._settings.vehicle_detection_model
        logger.info("loading_yolo_model", model=model_name)
        self._yolo_model = YOLO(f"{model_name}.pt")
        return self._yolo_model

    def _load_ocr(self) -> Any:
        """Load OCR model on first use."""
        if self._ocr_model is not None:
            return self._ocr_model

        ocr_engine = self._settings.anpr_model

        if ocr_engine == "paddleocr":
            try:
                from paddleocr import PaddleOCR
            except ImportError:
                raise ImportError(
                    "paddleocr is required for ANPR. "
                    "Install with: pip install -e '.[vision]'"
                )
            logger.info("loading_paddleocr")
            self._ocr_model = PaddleOCR(
                use_angle_cls=True,
                lang="en",
                show_log=False,
            )
        elif ocr_engine == "easyocr":
            try:
                import easyocr
            except ImportError:
                raise ImportError(
                    "easyocr is required for ANPR with easyocr engine. "
                    "Install with: pip install easyocr"
                )
            logger.info("loading_easyocr")
            self._ocr_model = easyocr.Reader(["en"], gpu=False)
        else:
            raise ValueError(f"Unknown ANPR model: {ocr_engine}")

        return self._ocr_model

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def analyze_snapshot(self, image_path: str | Path) -> VisionResult:
        """Run the combined vision pipeline on a snapshot image.

        Performs vehicle detection and/or ANPR based on configuration.
        Both features share the YOLO model when enabled simultaneously.

        Args:
            image_path: Path to the snapshot image file.

        Returns:
            VisionResult with plate_number, vehicle_type, and confidences.
        """
        image_path = Path(image_path)
        if not image_path.exists():
            logger.warning("snapshot_not_found", path=str(image_path))
            return VisionResult()

        result = VisionResult()
        anpr_enabled = self._settings.anpr_enabled
        detection_enabled = self._settings.vehicle_detection_enabled

        if not anpr_enabled and not detection_enabled:
            return result

        # Run YOLO if either feature needs it
        yolo_detections = []
        if anpr_enabled or detection_enabled:
            yolo_detections = self._run_yolo(str(image_path))
            result.raw_detections = yolo_detections

        # Extract vehicle type from YOLO results
        if detection_enabled:
            vtype, vconf = self._extract_vehicle_type(yolo_detections)
            if vconf >= self._settings.vehicle_detection_confidence_threshold:
                result.vehicle_type = vtype
                result.vehicle_confidence = vconf

        # Extract plate text via OCR
        if anpr_enabled:
            plate_text, plate_conf = self._extract_plate_number(
                str(image_path), yolo_detections
            )
            if plate_conf >= self._settings.anpr_confidence_threshold:
                result.plate_number = plate_text
                result.plate_confidence = plate_conf

        logger.info(
            "vision_analysis_complete",
            path=str(image_path),
            plate=result.plate_number,
            vehicle_type=result.vehicle_type,
        )

        return result

    # ------------------------------------------------------------------
    # Internal methods
    # ------------------------------------------------------------------

    def _run_yolo(self, image_path: str) -> list[dict[str, Any]]:
        """Run YOLOv8 detection on an image."""
        model = self._load_yolo()
        results = model(image_path, verbose=False)

        detections = []
        for det in results[0].boxes:
            class_id = int(det.cls)
            class_name = model.names[class_id]
            confidence = float(det.conf)
            bbox = det.xyxy[0].tolist()

            detections.append({
                "class_name": class_name,
                "class_id": class_id,
                "confidence": confidence,
                "bbox": bbox,
            })

        return detections

    def _extract_vehicle_type(
        self, detections: list[dict[str, Any]]
    ) -> tuple[str | None, float]:
        """Extract best vehicle type classification from YOLO detections."""
        best_type: str | None = None
        best_conf = 0.0

        for det in detections:
            class_name = det["class_name"]
            if class_name in COCO_TO_VEHICLE_TYPE and det["confidence"] > best_conf:
                best_type = COCO_TO_VEHICLE_TYPE[class_name]
                best_conf = det["confidence"]

        return best_type, best_conf

    def _extract_plate_number(
        self, image_path: str, detections: list[dict[str, Any]]
    ) -> tuple[str | None, float]:
        """Extract plate number using OCR.

        If YOLO detected a license plate region, crops to that region first.
        Otherwise runs OCR on the full image.
        """
        import re

        ocr = self._load_ocr()

        # Try to find plate region from YOLO (custom-trained models detect
        # "license_plate"; stock COCO does not, so we fall back to full image)
        plate_region = None
        for det in detections:
            if det["class_name"] in ("license_plate", "license-plate"):
                plate_region = det["bbox"]
                break

        # Run OCR
        ocr_engine = self._settings.anpr_model
        if ocr_engine == "paddleocr":
            result = ocr.ocr(image_path, cls=True)
            if not result or not result[0]:
                return None, 0.0

            # Concatenate all high-confidence text and try to match plate pattern
            texts = []
            avg_conf = 0.0
            count = 0
            for line in result[0]:
                text = line[1][0]
                conf = line[1][1]
                texts.append(text)
                avg_conf += conf
                count += 1

            avg_conf = avg_conf / count if count > 0 else 0.0
            full_text = " ".join(texts).upper()

        elif ocr_engine == "easyocr":
            result = ocr.readtext(image_path)
            if not result:
                return None, 0.0

            texts = []
            avg_conf = 0.0
            count = 0
            for bbox, text, conf in result:
                texts.append(text)
                avg_conf += conf
                count += 1

            avg_conf = avg_conf / count if count > 0 else 0.0
            full_text = " ".join(texts).upper()
        else:
            return None, 0.0

        # Indonesian plate pattern: 1-2 letters, 1-4 digits, 0-3 letters
        plate_pattern = re.compile(r"[A-Z]{1,2}\s?\d{1,4}\s?[A-Z]{0,3}")
        match = plate_pattern.search(full_text)

        if match:
            plate = match.group(0).replace(" ", " ").strip()
            # Normalize: ensure spaces between sections
            plate = re.sub(r"([A-Z]+)(\d+)([A-Z]*)", r"\1 \2 \3", plate).strip()
            return plate, avg_conf

        return None, 0.0
