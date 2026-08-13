"""
ARIA — AI Regulatory Inspection Accelerator
Core Platform — Document Intelligence — Quality Assessment

Pure decision logic for the pre-OCR image quality check: given a quality
score (0.0-1.0) produced by a vision model, decide pass/fail against a
configurable threshold, and normalize/validate the raw model response into
a `QualityCheckResult`.

Ported from PAFN's di/di_quality.py, generalized:
  - The 19-issue OCR-readability rubric and system prompt are genuinely
    domain-neutral already (blur, contrast, skew, occlusion, etc. apply to
    any scanned/photographed document, not just food-safety certificates) -
    kept as-is.
  - Removed the direct `AzureOpenAI` vision call and PDF-rasterization I/O
    (`_rasterize_pdf_first_page`). Core Platform has no dependency on a
    specific AI client or PDF library. `assess_quality` accepts an
    injectable `vision_check_fn` callback that performs the actual model
    call (and any PDF rasterization) and returns the raw JSON response dict
    - this module only validates/normalizes that response and applies the
    threshold decision, which is the part that must be deterministic and
    consistent regardless of which AI client implementation is wired in.
  - Removed the `QUALITY_SCORE_THRESHOLD` env var lookup at import time
    (Core Platform must not read environment variables directly - see
    ADR-010). The threshold is now a parameter with the same default value.
"""

from dataclasses import asdict, dataclass

DEFAULT_QUALITY_SCORE_THRESHOLD = 0.75

# Quality check prompt - focuses on OCR-readability, not aesthetic quality.
# This rubric is domain-neutral: it applies to any scanned/photographed
# document, regardless of industry template.
QUALITY_CHECK_SYSTEM_PROMPT = """You are a document quality assessment expert. Your task is to evaluate whether a document image is suitable for OCR (Optical Character Recognition) text extraction.

Analyze the image for the following quality issues that affect text readability:

**Clarity & Focus**
1. **Blur/Out of Focus**: Text is fuzzy or unreadable
2. **Very Blurry Scan**: Entire document is too blurry for reliable text extraction

**Lighting & Exposure**
3. **Low Contrast**: Text doesn't stand out from background
4. **Overexposure**: Washed out, text is lost in white
5. **Underexposure**: Too dark, text is hard to see
6. **Shadows**: Shadows cast across text areas reducing readability

**Resolution & Size**
7. **Low Resolution**: Text is pixelated or too small to read
8. **Text Too Small**: Font size is too small for reliable OCR even at adequate resolution

**Orientation & Geometry**
9. **Distortion/Skew**: Document is warped or heavily angled
10. **Perspective Distortion**: Phone-camera image with trapezoid/keystoning effect
11. **Severely Skewed**: Page is rotated or tilted significantly

**Physical Damage & Obstruction**
12. **Occlusion/Partial Cutoff**: Parts of text are covered, cropped, or cut off at edges
13. **Torn/Cropped Pages**: Physical damage causing missing text regions
14. **Stamps/Signatures Covering Text**: Stamps, seals, or signatures overlapping printed text

**Content Complexity**
15. **Mixed Printed + Handwritten**: Document contains both printed and handwritten text which may reduce OCR accuracy
16. **Heavy Handwriting**: Predominantly handwritten content that is difficult to OCR
17. **Dense Tables with Weak Scan Quality**: Tabular data where cell boundaries or text are hard to distinguish

**Composition**
18. **Noise/Artifacts**: Visual noise, compression artifacts, or stains obscuring text
19. **Multiple Pages Merged**: Two or more pages captured in a single image, overlapping or poorly aligned

Respond in JSON format:
{
    "passed": true/false,
    "quality_score": 0.0-1.0,
    "issues": ["issue1", "issue2"],
    "recommendation": "Brief recommendation"
}

Where:
- quality_score: 1.0 = perfect, 0.8+ = good, 0.5-0.8 = acceptable, <0.5 = poor
- issues: specific problems detected (empty list if none) - use the exact issue names listed above
- recommendation: "Proceed with extraction" or brief advice"""


@dataclass
class QualityCheckResult:
    """Result of the image quality check."""
    passed: bool
    quality_score: float  # 0.0-1.0, where 1.0 is perfect quality
    issues: list[str]
    recommendation: str

    def to_dict(self) -> dict:
        return asdict(self)


def evaluate_quality_response(
    raw_response: dict,
    threshold: float = DEFAULT_QUALITY_SCORE_THRESHOLD,
) -> QualityCheckResult:
    """Normalize a raw vision-model JSON response into a `QualityCheckResult`
    and apply the pass/fail decision.

    Pass/fail is determined by comparing `quality_score` against `threshold`
    rather than trusting the model's own `passed` field, which tends to be
    too lenient (see PAFN incident: a 0.1-scoring, clearly unreadable image
    was still marked `passed: true` by the model).

    Args:
        raw_response: parsed JSON dict from the vision model, expected to
            contain `quality_score` (float), `issues` (list[str]), and
            `recommendation` (str). Missing fields default safely.
        threshold: minimum `quality_score` to pass. Documents scoring below
            this are flagged for manual review rather than wasting DI/LLM
            tokens on an unreliable extraction.
    """
    quality_score = float(raw_response.get("quality_score", 0.0))
    issues = list(raw_response.get("issues", []))
    recommendation = raw_response.get("recommendation", "")
    return QualityCheckResult(
        passed=quality_score >= threshold,
        quality_score=quality_score,
        issues=issues,
        recommendation=recommendation,
    )


def assess_quality(
    vision_check_fn,
    image_data: bytes,
    file_name: str,
    threshold: float = DEFAULT_QUALITY_SCORE_THRESHOLD,
) -> QualityCheckResult:
    """Run the pre-OCR quality check on a document image.

    Args:
        vision_check_fn: injectable callable `(image_data, file_name) -> dict`
            that performs the actual vision-model call (including any PDF
            rasterization) using `QUALITY_CHECK_SYSTEM_PROMPT`, and returns
            the parsed JSON response. Supplied by the connector/AI-client
            layer - Core Platform has no direct AI SDK dependency.
        image_data: raw document bytes.
        file_name: original file name, for logging/traceability by the
            injected callback.
        threshold: minimum `quality_score` to pass (see `evaluate_quality_response`).

    Returns:
        QualityCheckResult with the threshold-based pass/fail decision
        applied.
    """
    raw_response = vision_check_fn(image_data, file_name)
    return evaluate_quality_response(raw_response, threshold=threshold)
