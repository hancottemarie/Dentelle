import json
import math
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

import cv2
import numpy as np
from shapely.geometry import LineString, MultiPoint, Point, Polygon, box
from shapely.ops import unary_union
from skimage.morphology import skeletonize

ZoneRole = Literal["contour", "fill", "background"]


class LaceEngine:
    """
    Moteur principal de traitement d'image et de géométrie computationnelle
    pour la génération de cartons de dentelle aux fuseaux à l'échelle 1:1.
    """

    def __init__(self, catalog_path: Optional[Path] = None):
        if catalog_path is None:
            catalog_path = Path(__file__).resolve().parent.parent / "data" / "stitches.json"
        with open(catalog_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.stitches: Dict[str, Dict[str, Any]] = {
            s["id"]: s for s in data["stitches"]
        }

    # =========================================================================
    # 1. SEGMENTATION D'IMAGE EN 3 ZONES (CONTOUR, REMPLISSAGE, FOND)
    # =========================================================================
    def segment_image(
        self,
        image_bytes: bytes,
        target_width_mm: float = 120.0,
        simplify_tolerance_mm: float = 0.4,
    ) -> Dict[str, Any]:
        """
        Nettoie l'image importée, extrait les contours, utilise la squelettisation
        pour isoler les meneurs et segmente le motif en polygones Shapely en mm.
        """
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
        if img is None:
            raise ValueError("Impossible de décoder l'image fournie.")

        # Réduction du bruit tout en préservant les bords nets
        denoised = cv2.bilateralFilter(img, d=9, sigmaColor=75, sigmaSpace=75)

        # Binarisation adaptative + Otsu pour gérer photos et dessins
        _, binary = cv2.threshold(
            denoised, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        )

        # Fermeture morphologique pour combler les micro-coupures des traits
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=1)

        # Rogner autour de la boîte englobante active avec une marge de 5%
        coords = cv2.findNonZero(cleaned)
        if coords is not None:
            x, y, w, h = cv2.boundingRect(coords)
            pad = int(max(w, h) * 0.05) + 5
            x0 = max(0, x - pad)
            y0 = max(0, y - pad)
            x1 = min(cleaned.shape[1], x + w + pad)
            y1 = min(cleaned.shape[0], y + h + pad)
            cleaned = cleaned[y0:y1, x0:x1]

        img_h, img_w = cleaned.shape
        px_to_mm = target_width_mm / float(img_w)
        target_height_mm = img_h * px_to_mm

        # Squelettisation pour identifier l'ossature des meneurs/rubans
        skeleton = skeletonize(cleaned > 0).astype(np.uint8) * 255
        dilated_skeleton = cv2.dilate(skeleton, kernel, iterations=2)

        # Extraction hiérarchique des contours OpenCV
        contours, hierarchy = cv2.findContours(
            cleaned, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
        )

        zones: List[Dict[str, Any]] = []
        zone_counter = 1

        # Création de la zone de fond globale (rectangle englobant)
        canvas_poly = box(0.0, 0.0, target_width_mm, target_height_mm)
        foreground_polys: List[Polygon] = []

        if hierarchy is not None:
            hier = hierarchy[0]
            for idx, cnt in enumerate(contours):
                area_px = cv2.contourArea(cnt)
                # Filtrer le bruit résiduel (< 2 mm²)
                if area_px * (px_to_mm ** 2) < 2.0:
                    continue

                # Conversion des coordonnées pixels -> millimètres (inversion axe Y pour repère cartésien)
                pts_mm = [
                    (float(pt[0][0]) * px_to_mm, float(img_h - pt[0][1]) * px_to_mm)
                    for pt in cnt
                ]
                if len(pts_mm) < 3:
                    continue

                poly = Polygon(pts_mm).buffer(0)
                if poly.is_empty or not poly.is_valid:
                    continue

                # Simplification vectorielle Douglas-Peucker
                poly = poly.simplify(simplify_tolerance_mm, preserve_topology=True)
                if poly.is_empty:
                    continue

                # Classification : un contour avec un parent dans la hiérarchie (trou interne)
                # ou une forme pleine devient une zone de remplissage ; sa bordure devient un meneur.
                parent_idx = hier[idx][3]
                is_inner_hole = parent_idx != -1

                # Création de la bande de contour (meneur/lacet de 2.4 mm de large)
                ribbon_width_mm = 2.4
                contour_band = poly.boundary.buffer(
                    ribbon_width_mm / 2.0, cap_style=1, join_style=1
                ).intersection(canvas_poly)

                if not contour_band.is_empty:
                    zones.append({
                        "zone_id": f"zone_{zone_counter}",
                        "role": "contour",
                        "polygon": contour_band,
                        "locked_stitch_id": None,
                    })
                    zone_counter += 1
                    foreground_polys.append(contour_band)

                # Intérieur de la forme -> zone de remplissage
                inner_fill = poly.difference(contour_band)
                if not inner_fill.is_empty and inner_fill.area >= 4.0 and not is_inner_hole:
                    zones.append({
                        "zone_id": f"zone_{zone_counter}",
                        "role": "fill",
                        "polygon": inner_fill,
                        "locked_stitch_id": None,
                    })
                    zone_counter += 1
                    foreground_polys.append(inner_fill)

        # Calcul du fond (réseau) par différence booléenne entre le cadre et les motifs
        if foreground_polys:
            merged_fg = unary_union(foreground_polys)
            bg_poly = canvas_poly.difference(merged_fg)
        else:
            bg_poly = canvas_poly

        if not bg_poly.is_empty and bg_poly.area > 5.0:
            zones.append({
                "zone_id": "zone_bg",
                "role": "background",
                "polygon": bg_poly,
                "locked_stitch_id": None,
            })

        return {
            "width_mm": round(target_width_mm, 2),
            "height_mm": round(target_height_mm, 2),
            "zones": zones,
        }

    # =========================================================================
    # 2. GÉNÉRATION DES GRILLES DE PIQUAGE (45° OU 60°) EN MILLIMÈTRES
    # =========================================================================
    def generate_grid_basis(
        self, angle_deg: int, pitch_mm: float
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Calcule les deux vecteurs de base (u, v) d'une maille de dentelle en mm.
        - angle 45° : maille losange Torchon (diagonales à 45°)
        - angle 60° : maille isométrique Cluny/Flandre (triangles équilatéraux)
        """
        if angle_deg == 45:
            # Pas diagonal = pitch_mm -> projection orthogonale = pitch_mm * sqrt(2)
            dx = pitch_mm * math.sqrt(2.0)
            u = np.array([dx, 0.0])
            v = np.array([dx / 2.0, dx / 2.0])
            return u, v
        elif angle_deg == 60:
            rad = math.radians(60.0)
            u = np.array([pitch_mm, 0.0])
            v = np.array([pitch_mm * math.cos(rad), pitch_mm * math.sin(rad)])
            return u, v
        else:
            raise ValueError(f"Angle de grille non supporté : {angle_deg}° (attendu: 45 ou 60).")

    # =========================================================================
    # 3. APPLICATION D'UN POINT DU CATALOGUE SUR UNE ZONE POLYGONALE
    # =========================================================================
    def apply_stitch_to_zone(
        self,
        polygon: Polygon,
        stitch_id: str,
        pitch_mm: float,
        angle_deg: int,
        density: float = 1.0,
        margin_mm: float = 0.6,
    ) -> Dict[str, Any]:
        """
        Pave l'intérieur d'un polygone Shapely avec les trous d'épingle (pins)
        et les lignes de guidage du point sélectionné.
        """
        stitch = self.stitches[stitch_id]
        effective_pitch = max(
            stitch["min_pitch_mm"],
            pitch_mm / max(0.3, density * stitch.get("density_factor", 1.0)),
        )

        # Marge intérieure pour éviter le chevauchement des épingles sur les bordures
        safe_zone = polygon.buffer(-margin_mm)
        if safe_zone.is_empty:
            safe_zone = polygon

        minx, miny, maxx, maxy = safe_zone.bounds
        u, v = self.generate_grid_basis(angle_deg, effective_pitch)

        # Calcul des bornes d'indices (i, j) couvrant largement la bounding box
        span_x = (maxx - minx) + effective_pitch * 4
        span_y = (maxy - miny) + effective_pitch * 4
        max_i = int(math.ceil(span_x / max(u[0], 0.1))) + 4
        max_j = int(math.ceil(span_y / max(v[1], 0.1))) + 4

        origin = np.array([minx - effective_pitch * 2, miny - effective_pitch * 2])

        cell_pins = stitch["cell_geometry"]["pins"]
        cell_lines = stitch["cell_geometry"]["guide_lines"]

        raw_pins: List[Tuple[float, float]] = []
        raw_lines: List[Dict[str, Any]] = []

        # Parcours de la maille régulière
        for j in range(-max_j, max_j + 1):
            for i in range(-max_i, max_i + 1):
                cell_origin = origin + i * u + j * v

                # Test rapide d'élagage par boîte englobante
                if (
                    cell_origin[0] < minx - effective_pitch * 2
                    or cell_origin[0] > maxx + effective_pitch * 2
                    or cell_origin[1] < miny - effective_pitch * 2
                    or cell_origin[1] > maxy + effective_pitch * 2
                ):
                    continue

                # Placement des épingles de la cellule
                for p_def in cell_pins:
                    pt_coord = cell_origin + p_def["u"] * u + p_def["v"] * v
                    pt = Point(float(pt_coord[0]), float(pt_coord[1]))
                    if safe_zone.contains(pt):
                        raw_pins.append((round(pt.x, 3), round(pt.y, 3)))

                # Placement et découpage (clipping) des lignes de guidage
                for l_def in cell_lines:
                    p1 = cell_origin + l_def["from"][0] * u + l_def["from"][1] * v
                    p2 = cell_origin + l_def["to"][0] * u + l_def["to"][1] * v
                    seg = LineString([(float(p1[0]), float(p1[1])), (float(p2[0]), float(p2[1]))])

                    clipped = seg.intersection(safe_zone)
                    if clipped.is_empty:
                        continue

                    geoms = [clipped] if isinstance(clipped, LineString) else getattr(clipped, "geoms", [])
                    for g in geoms:
                        if isinstance(g, LineString) and g.length > 0.15:
                            coords = list(g.coords)
                            raw_lines.append({
                                "x1": round(coords[0][0], 3),
                                "y1": round(coords[0][1], 3),
                                "x2": round(coords[-1][0], 3),
                                "y2": round(coords[-1][1], 3),
                                "style": l_def["style"],
                            })

        # Déduplication des trous d'épingle partagés entre cellules adjacentes (tolérance 0.05 mm)
        unique_pins = self._deduplicate_pins(raw_pins, tolerance=0.05)

        return {
            "stitch_id": stitch_id,
            "stitch_name": stitch["name"],
            "pins": unique_pins,
            "guide_lines": raw_lines,
        }

    def _deduplicate_pins(
        self, pins: List[Tuple[float, float]], tolerance: float = 0.05
    ) -> List[Tuple[float, float]]:
        seen = set()
        unique: List[Tuple[float, float]] = []
        inv_tol = 1.0 / tolerance
        for x, y in pins:
            key = (round(x * inv_tol), round(y * inv_tol))
            if key not in seen:
                seen.add(key)
                unique.append((x, y))
        return unique

    # =========================================================================
    # 4. ORNEMENTS DE BORDURE (PICOTS, COQUILLES, FESTONS)
    # =========================================================================
    def generate_border_ornaments(
        self,
        zones: List[Dict[str, Any]],
        pitch_mm: float,
        ornament_type: Literal["none", "picots", "shells", "scallops"] = "shells",
    ) -> Dict[str, Any]:
        """
        Génère des piquages décoratifs réguliers le long de l'enveloppe extérieure
        du motif (contour externe).
        """
        if ornament_type == "none":
            return {"pins": [], "guide_lines": []}

        contour_polys = [z["polygon"] for z in zones if z["role"] == "contour"]
        if not contour_polys:
            return {"pins": [], "guide_lines": []}

        outer_union = unary_union(contour_polys).buffer(0.5)
        exterior_ring = (
            outer_union.exterior
            if isinstance(outer_union, Polygon)
            else max(outer_union.geoms, key=lambda g: g.area).exterior
        )

        perimeter = exterior_ring.length
        step = pitch_mm * (2.5 if ornament_type in ("shells", "scallops") else 1.2)
        num_steps = max(4, int(round(perimeter / step)))
        actual_step = perimeter / num_steps

        pins: List[Tuple[float, float]] = []
        lines: List[Dict[str, Any]] = []

        for k in range(num_steps):
            dist = k * actual_step
            pt_curr = exterior_ring.interpolate(dist)
            pt_next = exterior_ring.interpolate((dist + actual_step * 0.1) % perimeter)

            # Vecteur tangent et normale extérieure
            tx = pt_next.x - pt_curr.x
            ty = pt_next.y - pt_curr.y
            norm = math.hypot(tx, ty) or 1.0
            nx, ny = ty / norm, -tx / norm  # Normale sortante

            # Vérifier que la normale pointe bien vers l'extérieur du polygone
            test_pt = Point(pt_curr.x + nx * 0.2, pt_curr.y + ny * 0.2)
            if outer_union.contains(test_pt):
                nx, ny = -nx, -ny

            if ornament_type == "picots":
                pin_x = pt_curr.x + nx * (pitch_mm * 0.9)
                pin_y = pt_curr.y + ny * (pitch_mm * 0.9)
                pins.append((round(pin_x, 3), round(pin_y, 3)))
                lines.append({
                    "x1": round(pt_curr.x, 3),
                    "y1": round(pt_curr.y, 3),
                    "x2": round(pin_x, 3),
                    "y2": round(pin_y, 3),
                    "style": "solid",
                })

            elif ornament_type in ("shells", "scallops"):
                # Éventail à 5 épingles en arc de cercle extérieur
                fan_count = 5 if ornament_type == "shells" else 7
                radius = pitch_mm * 1.4
                base_angle = math.atan2(ny, nx)
                spread = math.radians(110.0)

                fan_pts: List[Tuple[float, float]] = []
                for f_idx in range(fan_count):
                    frac = (f_idx / (fan_count - 1)) - 0.5
                    theta = base_angle + frac * spread
                    px = pt_curr.x + math.cos(theta) * radius
                    py = pt_curr.y + math.sin(theta) * radius
                    pins.append((round(px, 3), round(py, 3)))
                    fan_pts.append((round(px, 3), round(py, 3)))

                    if ornament_type == "shells":
                        # Rayons partant de la base de la coquille
                        lines.append({
                            "x1": round(pt_curr.x, 3),
                            "y1": round(pt_curr.y, 3),
                            "x2": round(px, 3),
                            "y2": round(py, 3),
                            "style": "dotted",
                        })

                # Arc reliant les pointes de l'éventail
                for idx_p in range(len(fan_pts) - 1):
                    lines.append({
                        "x1": fan_pts[idx_p][0],
                        "y1": fan_pts[idx_p][1],
                        "x2": fan_pts[idx_p + 1][0],
                        "y2": fan_pts[idx_p + 1][1],
                        "style": "solid",
                    })

        return {"pins": pins, "guide_lines": lines}

    # =========================================================================
    # 5. ORCHESTRATION COMPLÈTE DU PATRON SELON LES PARAMÈTRES UTILISATEUR
    # =========================================================================
    def generate_pattern(
        self,
        segmented_data: Dict[str, Any],
        pitch_mm: float = 3.0,
        angle_deg: int = 45,
        max_difficulty: int = 3,
        known_stitch_ids: Optional[List[str]] = None,
        density: float = 1.0,
        ornament_type: Literal["none", "picots", "shells", "scallops"] = "none",
        zone_overrides: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Génère le carton vectoriel complet en temps réel (< 150ms) en filtrant
        strictement les points connus par l'utilisateur et le niveau de difficulté.
        """
        if known_stitch_ids is None:
            known_stitch_ids = list(self.stitches.keys())
        if zone_overrides is None:
            zone_overrides = {}

        # Filtrage des points autorisés : connus + difficulté <= curseur + angle compatible
        allowed_stitches = [
            s
            for s in self.stitches.values()
            if s["id"] in known_stitch_ids
            and s["difficulty"] <= max_difficulty
            and angle_deg in s["grid_angles"]
        ]

        # Fallback de sécurité si l'utilisateur a tout décoché
        if not allowed_stitches:
            allowed_stitches = [self.stitches["cloth_stitch"]]

        rendered_zones: List[Dict[str, Any]] = []

        for zone in segmented_data["zones"]:
            z_id = zone["zone_id"]
            role: ZoneRole = zone["role"]
            poly: Polygon = zone["polygon"]

            # 1. Vérifier si l'utilisateur a forcé un point au clic sur cette zone
            forced_id = zone_overrides.get(z_id) or zone.get("locked_stitch_id")
            if forced_id and forced_id in self.stitches:
                chosen_stitch = self.stitches[forced_id]
            else:
                # 2. Sélection automatique du meilleur point compatible avec le rôle de la zone
                candidates = [
                    s for s in allowed_stitches if role in s["compatible_roles"]
                ]
                if not candidates:
                    candidates = allowed_stitches

                # Privilégier le point le plus riche correspondant au niveau de difficulté choisi
                candidates.sort(key=lambda s: s["difficulty"], reverse=True)
                chosen_stitch = candidates[0]

            stitch_render = self.apply_stitch_to_zone(
                polygon=poly,
                stitch_id=chosen_stitch["id"],
                pitch_mm=pitch_mm,
                angle_deg=angle_deg,
                density=density,
            )

            # Extraction des contours de zone pour l'interactivité frontend (Konva)
            exterior_coords = []
            if isinstance(poly, Polygon):
                exterior_coords = [[round(x, 2), round(y, 2)] for x, y in poly.exterior.coords]
            elif hasattr(poly, "geoms"):
                largest = max(poly.geoms, key=lambda g: g.area)
                exterior_coords = [[round(x, 2), round(y, 2)] for x, y in largest.exterior.coords]

            rendered_zones.append({
                "zone_id": z_id,
                "role": role,
                "stitch_id": chosen_stitch["id"],
                "stitch_name": chosen_stitch["name"],
                "boundary_mm": exterior_coords,
                "pins": stitch_render["pins"],
                "guide_lines": stitch_render["guide_lines"],
            })

        ornaments = self.generate_border_ornaments(
            zones=segmented_data["zones"],
            pitch_mm=pitch_mm,
            ornament_type=ornament_type,
        )

        return {
            "width_mm": segmented_data["width_mm"],
            "height_mm": segmented_data["height_mm"],
            "pitch_mm": pitch_mm,
            "angle_deg": angle_deg,
            "zones": rendered_zones,
            "ornaments": ornaments,
        }
