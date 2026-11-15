from typing import Dict, List, Literal, Optional, Tuple
from pydantic import BaseModel, Field


class PatternGenerateRequest(BaseModel):
    session_id: str = Field(..., description="Identifiant de l'image segmentée en mémoire")
    pitch_mm: float = Field(default=3.0, ge=1.5, le=10.0, description="Pas de grille en mm")
    angle_deg: Literal[45, 60] = Field(default=45, description="Angle de la maille (45° ou 60°)")
    max_difficulty: int = Field(default=3, ge=1, le=5, description="Niveau de difficulté max (1 à 5)")
    known_stitch_ids: Optional[List[str]] = Field(
        default=None, description="Liste des IDs de points maîtrisés par l'utilisateur"
    )
    density: float = Field(default=1.0, ge=0.4, le=2.0, description="Facteur de densité du remplissage")
    ornament_type: Literal["none", "picots", "shells", "scallops"] = Field(
        default="none", description="Type d'ornement sur le contour extérieur"
    )
    zone_overrides: Dict[str, str] = Field(
        default_factory=dict,
        description="Dictionnaire {zone_id: stitch_id} pour les zones modifiées manuellement au clic",
    )


class ExportRequest(PatternGenerateRequest):
    title: str = Field(
        default="Carton Technique - Dentelle aux Fuseaux",
        description="Titre affiché dans le cartouche du carton",
    )


class GuideLineResponse(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float
    style: str


class ZoneRenderResponse(BaseModel):
    zone_id: str
    role: Literal["contour", "fill", "background"]
    stitch_id: str
    stitch_name: str
    boundary_mm: List[List[float]]
    pins: List[Tuple[float, float]]
    guide_lines: List[GuideLineResponse]


class OrnamentsResponse(BaseModel):
    pins: List[Tuple[float, float]]
    guide_lines: List[GuideLineResponse]


class PatternResponse(BaseModel):
    width_mm: float
    height_mm: float
    pitch_mm: float
    angle_deg: int
    zones: List[ZoneRenderResponse]
    ornaments: OrnamentsResponse
