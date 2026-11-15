import uuid
from typing import Any, Dict

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from app.core.lace_engine import LaceEngine
from app.core.pdf_exporter import LacePDFExporter
from app.core.svg_exporter import LaceSVGExporter
from app.models import ExportRequest, PatternGenerateRequest, PatternResponse

app = FastAPI(
    title="Bobbin Lace Generator API",
    description="Moteur open-source de génération de cartons de dentelle aux fuseaux à l'échelle 1:1",
    version="1.0.0",
)

# Autoriser les requêtes locales du frontend React/Vite
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = LaceEngine()
pdf_exporter = LacePDFExporter()
svg_exporter = LaceSVGExporter()

# Cache en mémoire des images segmentées {session_id: {"image_bytes": ..., "segmented": ...}}
SESSION_STORE: Dict[str, Dict[str, Any]] = {}


@app.get("/api/health")
def health_check():
    return {"status": "ok", "stitches_loaded": len(engine.stitches)}


@app.get("/api/stitches")
def get_stitches_catalog():
    """Retourne le catalogue complet des points de dentelle disponibles."""
    return {"stitches": list(engine.stitches.values())}


@app.post("/api/upload")
async def upload_and_segment_image(
    file: UploadFile = File(...),
    target_width_mm: float = Form(120.0),
):
    """
    Importe une image, nettoie le bruit, extrait les 3 zones (contour, fill, background)
    et retourne un premier jet complet du carton vectoriel.
    """
    if file.content_type not in ("image/png", "image/jpeg", "image/webp"):
        raise HTTPException(
            status_code=400,
            detail="Format d'image non supporté. Utilisez PNG, JPG ou WebP.",
        )

    image_bytes = await file.read()
    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="L'image dépasse la limite de 10 Mo.")

    try:
        segmented = engine.segment_image(
            image_bytes=image_bytes,
            target_width_mm=target_width_mm,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    session_id = str(uuid.uuid4())
    SESSION_STORE[session_id] = {
        "image_bytes": image_bytes,
        "segmented": segmented,
    }

    initial_pattern = engine.generate_pattern(segmented_data=segmented)

    return {
        "session_id": session_id,
        "pattern": initial_pattern,
    }


@app.post("/api/generate", response_model=PatternResponse)
def generate_pattern_realtime(
    req: PatternGenerateRequest,
    target_width_mm: float = 120.0,
):
    """
    Recalcule le patron en temps réel (< 150 ms) lorsque l'utilisateur déplace
    un curseur, coche/décoche un point connu ou force un point sur une zone.
    """
    session = SESSION_STORE.get(req.session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail="Session expirée ou introuvable. Veuillez réimporter votre image.",
        )

    segmented = session["segmented"]

    # Si l'utilisateur a modifié la largeur globale en mm, re-segmenter à la nouvelle échelle
    if abs(segmented["width_mm"] - target_width_mm) > 0.5:
        segmented = engine.segment_image(
            image_bytes=session["image_bytes"],
            target_width_mm=target_width_mm,
        )
        session["segmented"] = segmented

    pattern = engine.generate_pattern(
        segmented_data=segmented,
        pitch_mm=req.pitch_mm,
        angle_deg=req.angle_deg,
        max_difficulty=req.max_difficulty,
        known_stitch_ids=req.known_stitch_ids,
        density=req.density,
        ornament_type=req.ornament_type,
        zone_overrides=req.zone_overrides,
    )
    return pattern


@app.post("/api/export/pdf")
def export_pattern_pdf(req: ExportRequest, target_width_mm: float = 120.0):
    """Génère et télécharge le carton au format PDF à l'échelle stricte 1:1."""
    pattern = generate_pattern_realtime(req, target_width_mm=target_width_mm)
    pdf_bytes = pdf_exporter.export_to_bytes(pattern, title=req.title)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="carton_dentelle_1_1.pdf"'
        },
    )


@app.post("/api/export/svg")
def export_pattern_svg(req: ExportRequest, target_width_mm: float = 120.0):
    """Génère et télécharge le carton au format SVG vectoriel en millimètres."""
    pattern = generate_pattern_realtime(req, target_width_mm=target_width_mm)
    svg_content = svg_exporter.export_to_string(pattern)

    return Response(
        content=svg_content,
        media_type="image/svg+xml",
        headers={
            "Content-Disposition": 'attachment; filename="carton_dentelle_1_1.svg"'
        },
    )
