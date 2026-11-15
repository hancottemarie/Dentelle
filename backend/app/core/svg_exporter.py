from typing import Any, Dict
import svgwrite


class LaceSVGExporter:
    """
    Générateur SVG vectoriel à l'échelle stricte 1:1 en millimètres.
    Compatible avec Inkscape, Adobe Illustrator et les traceurs de découpe.
    """

    PIN_RADIUS_MM = 0.20  # Diamètre exact du trou de piquage = 0.40 mm

    def export_to_string(self, pattern_data: Dict[str, Any]) -> str:
        margin_mm = 10.0
        calibration_h_mm = 16.0

        pattern_w = float(pattern_data["width_mm"])
        pattern_h = float(pattern_data["height_mm"])

        total_w = pattern_w + 2 * margin_mm
        total_h = pattern_h + 2 * margin_mm + calibration_h_mm

        dwg = svgwrite.Drawing(
            size=(f"{total_w}mm", f"{total_h}mm"),
            viewBox=f"0 0 {total_w} {total_h}",
            profile="tiny",
        )

        # Arrière-plan blanc
        dwg.add(dwg.rect(insert=(0, 0), size=(total_w, total_h), fill="white"))

        # Groupe principal du carton (inversion axe Y pour correspondre au repère SVG)
        carton_group = dwg.g(id="lace-pattern")

        # Cadre délimitant le patron
        carton_group.add(
            dwg.rect(
                insert=(margin_mm, margin_mm),
                size=(pattern_w, pattern_h),
                fill="none",
                stroke="#CCCCCC",
                stroke_width=0.15,
            )
        )

        # Calques par zone (lignes de guidage + trous d'épingle)
        for zone in pattern_data.get("zones", []):
            z_group = dwg.g(id=zone["zone_id"])
            role = zone["role"]

            if role == "contour":
                stroke_color = "#3B73BF"
                stroke_w = 0.18
            elif role == "fill":
                stroke_color = "#737373"
                stroke_w = 0.14
            else:
                stroke_color = "#B8B8B8"
                stroke_w = 0.10

            for line in zone.get("guide_lines", []):
                x1 = margin_mm + line["x1"]
                y1 = margin_mm + (pattern_h - line["y1"])
                x2 = margin_mm + line["x2"]
                y2 = margin_mm + (pattern_h - line["y2"])

                svg_line = dwg.line(
                    start=(x1, y1),
                    end=(x2, y2),
                    stroke=stroke_color,
                    stroke_width=stroke_w,
                )
                style = line.get("style", "solid")
                if style == "dashed":
                    svg_line.dasharray([1.2, 0.8])
                elif style == "dotted":
                    svg_line.dasharray([0.3, 0.7])
                z_group.add(svg_line)

            for px, py in zone.get("pins", []):
                cx = margin_mm + px
                cy = margin_mm + (pattern_h - py)
                z_group.add(
                    dwg.circle(
                        center=(cx, cy),
                        r=self.PIN_RADIUS_MM,
                        fill="#000000",
                    )
                )

            carton_group.add(z_group)

        # Calque des ornements de bordure
        ornaments = pattern_data.get("ornaments", {})
        if ornaments:
            orn_group = dwg.g(id="border-ornaments")
            for line in ornaments.get("guide_lines", []):
                x1 = margin_mm + line["x1"]
                y1 = margin_mm + (pattern_h - line["y1"])
                x2 = margin_mm + line["x2"]
                y2 = margin_mm + (pattern_h - line["y2"])
                svg_line = dwg.line(
                    start=(x1, y1),
                    end=(x2, y2),
                    stroke="#A63333",
                    stroke_width=0.15,
                )
                if line.get("style") == "dotted":
                    svg_line.dasharray([0.3, 0.6])
                orn_group.add(svg_line)

            for px, py in ornaments.get("pins", []):
                cx = margin_mm + px
                cy = margin_mm + (pattern_h - py)
                orn_group.add(
                    dwg.circle(
                        center=(cx, cy),
                        r=self.PIN_RADIUS_MM,
                        fill="#000000",
                    )
                )
            carton_group.add(orn_group)

        dwg.add(carton_group)

        # Carré de calibration 10 x 10 mm en bas à droite
        cal_group = dwg.g(id="calibration-10x10mm")
        cal_x = total_w - margin_mm - 10.0
        cal_y = margin_mm + pattern_h + 4.0
        cal_group.add(
            dwg.rect(
                insert=(cal_x, cal_y),
                size=(10.0, 10.0),
                fill="none",
                stroke="#000000",
                stroke_width=0.25,
            )
        )
        cal_group.add(
            dwg.line(
                start=(cal_x + 5.0, cal_y),
                end=(cal_x + 5.0, cal_y + 10.0),
                stroke="#000000",
                stroke_width=0.1,
            )
        )
        cal_group.add(
            dwg.line(
                start=(cal_x, cal_y + 5.0),
                end=(cal_x + 10.0, cal_y + 5.0),
                stroke="#000000",
                stroke_width=0.1,
            )
        )
        dwg.add(cal_group)

        return dwg.tostring()
