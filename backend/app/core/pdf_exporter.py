import io
from typing import Any, Dict

from reportlab.lib import colors
from reportlab.lib.pagesizes import A3, A4, landscape, portrait
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


class LacePDFExporter:
    """
    Générateur PDF technique pour cartons de dentelle aux fuseaux.
    Garantit une échelle stricte 1:1 en millimètres avec mire de calibration.
    """

    PIN_RADIUS_MM = 0.20  # Diamètre exact du trou de piquage = 0.40 mm

    def export_to_bytes(
        self,
        pattern_data: Dict[str, Any],
        title: str = "Carton Technique - Dentelle aux Fuseaux",
    ) -> bytes:
        """
        Génère le fichier PDF en mémoire prêt à être téléchargé et imprimé à 100%.
        """
        buffer = io.BytesIO()

        pattern_w_mm = float(pattern_data["width_mm"])
        pattern_h_mm = float(pattern_data["height_mm"])

        # Marges techniques : 15 mm sur les côtés, 25 mm en bas pour le cartouche et la mire
        margin_side_mm = 15.0
        margin_top_mm = 18.0
        margin_bottom_mm = 28.0

        req_w_pt = (pattern_w_mm + 2 * margin_side_mm) * mm
        req_h_pt = (pattern_h_mm + margin_top_mm + margin_bottom_mm) * mm

        # Choix automatique de la taille de feuille standard minimale (A4 ou A3)
        page_size = self._select_optimal_page_size(req_w_pt, req_h_pt)
        page_w_pt, page_h_pt = page_size

        c = canvas.Canvas(buffer, pagesize=page_size)
        c.setTitle(title)
        c.setAuthor("Bobbin Lace Open-Source Generator")
        c.setSubject(
            f"Carton 1:1 | Pas: {pattern_data['pitch_mm']} mm | Angle: {pattern_data['angle_deg']} deg"
        )

        # Centrage horizontal du patron sur la feuille
        offset_x_pt = (page_w_pt - (pattern_w_mm * mm)) / 2.0
        offset_y_pt = margin_bottom_mm * mm

        # 1. En-tête technique discret
        self._draw_header(c, page_w_pt, page_h_pt, pattern_data, title)

        # 2. Cadre de délimitation du carton
        c.saveState()
        c.setStrokeColor(colors.Color(0.75, 0.75, 0.75))
        c.setLineWidth(0.15 * mm)
        c.rect(
            offset_x_pt,
            offset_y_pt,
            pattern_w_mm * mm,
            pattern_h_mm * mm,
            stroke=1,
            fill=0,
        )
        c.restoreState()

        # 3. Dessin des lignes de guidage et des points de piquage par zone
        for zone in pattern_data.get("zones", []):
            self._draw_zone(c, zone, offset_x_pt, offset_y_pt)

        # 4. Dessin des ornements de bordure (picots, coquilles, festons)
        ornaments = pattern_data.get("ornaments", {})
        if ornaments:
            self._draw_ornaments(c, ornaments, offset_x_pt, offset_y_pt)

        # 5. Dessin du carré de calibration 10x10 mm et de la règle témoin
        self._draw_calibration_block(c, page_w_pt, margin_side_mm * mm)

        c.showPage()
        c.save()

        buffer.seek(0)
        return buffer.getvalue()

    def _select_optimal_page_size(self, req_w_pt: float, req_h_pt: float):
        candidates = [
            portrait(A4),
            landscape(A4),
            portrait(A3),
            landscape(A3),
        ]
        for pw, ph in candidates:
            if req_w_pt <= pw and req_h_pt <= ph:
                return (pw, ph)
        # Format personnalisé grand format si le patron dépasse le A3
        return (req_w_pt, req_h_pt)

    def _draw_header(
        self,
        c: canvas.Canvas,
        page_w_pt: float,
        page_h_pt: float,
        pattern_data: Dict[str, Any],
        title: str,
    ) -> None:
        c.saveState()
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(colors.black)
        c.drawString(15 * mm, page_h_pt - 11 * mm, title)

        c.setFont("Helvetica", 7.5)
        c.setFillColor(colors.Color(0.3, 0.3, 0.3))
        specs = (
            f"Dimensions: {pattern_data['width_mm']} x {pattern_data['height_mm']} mm  |  "
            f"Pas de grille: {pattern_data['pitch_mm']} mm  |  "
            f"Angle: {pattern_data['angle_deg']}°  |  "
            f"Échelle: 1:1 (Imprimer à 100% - Sans ajustement)"
        )
        c.drawString(15 * mm, page_h_pt - 15 * mm, specs)
        c.restoreState()

    def _draw_zone(
        self,
        c: canvas.Canvas,
        zone: Dict[str, Any],
        offset_x_pt: float,
        offset_y_pt: float,
    ) -> None:
        role = zone["role"]

        # A. Lignes de guidage des paires
        c.saveState()
        if role == "contour":
            c.setStrokeColor(colors.Color(0.25, 0.45, 0.75))  # Bleu technique fin pour meneurs
            c.setLineWidth(0.18 * mm)
        elif role == "fill":
            c.setStrokeColor(colors.Color(0.45, 0.45, 0.45))  # Gris moyen pour remplissage
            c.setLineWidth(0.14 * mm)
        else:
            c.setStrokeColor(colors.Color(0.72, 0.72, 0.72))  # Gris clair discret pour le réseau
            c.setLineWidth(0.10 * mm)

        for line in zone.get("guide_lines", []):
            style = line.get("style", "solid")
            if style == "dashed":
                c.setDash([1.2 * mm, 0.8 * mm])
            elif style == "dotted":
                c.setDash([0.3 * mm, 0.7 * mm])
            else:
                c.setDash([])

            x1 = offset_x_pt + line["x1"] * mm
            y1 = offset_y_pt + line["y1"] * mm
            x2 = offset_x_pt + line["x2"] * mm
            y2 = offset_y_pt + line["y2"] * mm
            c.line(x1, y1, x2, y2)
        c.restoreState()

        # B. Trous d'épingle (points de piquage nets de 0.4 mm de diamètre)
        c.saveState()
        c.setFillColor(colors.black)
        pin_r_pt = self.PIN_RADIUS_MM * mm
        for px, py in zone.get("pins", []):
            cx = offset_x_pt + px * mm
            cy = offset_y_pt + py * mm
            c.circle(cx, cy, pin_r_pt, stroke=0, fill=1)
        c.restoreState()

    def _draw_ornaments(
        self,
        c: canvas.Canvas,
        ornaments: Dict[str, Any],
        offset_x_pt: float,
        offset_y_pt: float,
    ) -> None:
        c.saveState()
        c.setStrokeColor(colors.Color(0.65, 0.2, 0.2))
        c.setLineWidth(0.15 * mm)
        for line in ornaments.get("guide_lines", []):
            if line.get("style") == "dotted":
                c.setDash([0.3 * mm, 0.6 * mm])
            else:
                c.setDash([])
            c.line(
                offset_x_pt + line["x1"] * mm,
                offset_y_pt + line["y1"] * mm,
                offset_x_pt + line["x2"] * mm,
                offset_y_pt + line["y2"] * mm,
            )

        c.setFillColor(colors.black)
        pin_r_pt = self.PIN_RADIUS_MM * mm
        for px, py in ornaments.get("pins", []):
            c.circle(
                offset_x_pt + px * mm,
                offset_y_pt + py * mm,
                pin_r_pt,
                stroke=0,
                fill=1,
            )
        c.restoreState()

    def _draw_calibration_block(
        self, c: canvas.Canvas, page_w_pt: float, margin_pt: float
    ) -> None:
        """
        Dessine en bas de page :
        1. Un carré de calibration strict de 10.0 x 10.0 mm
        2. Une règle de contrôle graduée de 50.0 mm
        """
        c.saveState()
        base_y = 8.0 * mm
        cal_x = page_w_pt - margin_pt - 10.0 * mm

        # Carré 10x10 mm
        c.setStrokeColor(colors.black)
        c.setLineWidth(0.25 * mm)
        c.rect(cal_x, base_y, 10.0 * mm, 10.0 * mm, stroke=1, fill=0)

        # Croix centrale de précision dans le carré
        c.setLineWidth(0.1 * mm)
        c.line(cal_x + 5.0 * mm, base_y, cal_x + 5.0 * mm, base_y + 10.0 * mm)
        c.line(cal_x, base_y + 5.0 * mm, cal_x + 10.0 * mm, base_y + 5.0 * mm)

        c.setFont("Helvetica-Bold", 7)
        c.setFillColor(colors.black)
        c.drawRightString(cal_x - 3 * mm, base_y + 6 * mm, "CARRÉ DE CALIBRATION : 10 x 10 mm")
        c.setFont("Helvetica", 6.5)
        c.drawRightString(
            cal_x - 3 * mm,
            base_y + 2 * mm,
            "Vérifiez au réglet avant de piquer (Impression 100% / Taille réelle)",
        )

        # Règle témoin de 50 mm en bas à gauche
        ruler_x = margin_pt
        ruler_y = base_y + 3 * mm
        c.setLineWidth(0.25 * mm)
        c.line(ruler_x, ruler_y, ruler_x + 50.0 * mm, ruler_y)
        for tick in range(0, 55, 5):
            tick_h = 3.0 * mm if tick % 10 == 0 else 1.8 * mm
            tx = ruler_x + tick * mm
            c.line(tx, ruler_y, tx, ruler_y + tick_h)
            if tick % 10 == 0:
                c.setFont("Helvetica", 6)
                c.drawCentredString(tx, ruler_y - 2.8 * mm, f"{tick}mm")

        c.restoreState()
