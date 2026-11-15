import React, { useEffect, useRef, useState } from "react";
import { Stage, Layer, Line, Circle, Rect, Image as KonvaImage, Group } from "react-konva";
import { Eye, EyeOff, ZoomIn, ZoomOut, Maximize2, Lock, Unlock } from "lucide-react";

const PX_PER_MM = 4.5; // Échelle d'affichage de base sur écran

export default function LaceCanvas({
  pattern,
  sourceImageUrl,
  stitches,
  zoneOverrides,
  onSelectZoneStitch,
}) {
  const containerRef = useRef(null);
  const [stageSize, setStageSize] = useState({ width: 900, height: 700 });
  const [scale, setScale] = useState(1);
  const [position, setPosition] = useState({ x: 60, y: 60 });
  const [showSourceImage, setShowSourceImage] = useState(true);
  const [hoveredZoneId, setHoveredZoneId] = useState(null);
  const [selectedZone, setSelectedZone] = useState(null); // { zone, screenX, screenY }
  const [bgImg, setBgImg] = useState(null);

  // Adaptation automatique aux dimensions du conteneur
  useEffect(() => {
    const updateSize = () => {
      if (containerRef.current) {
        setStageSize({
          width: containerRef.current.offsetWidth,
          height: containerRef.current.offsetHeight,
        });
      }
    };
    updateSize();
    window.addEventListener("resize", updateSize);
    return () => window.removeEventListener("resize", updateSize);
  }, []);

  // Chargement de l'image d'origine pour l'overlay semi-transparent
  useEffect(() => {
    if (!sourceImageUrl) {
      setBgImg(null);
      return;
    }
    const img = new window.Image();
    img.src = sourceImageUrl;
    img.onload = () => setBgImg(img);
  }, [sourceImageUrl]);

  // Centrer automatiquement le patron lors d'un nouvel import
  const fitToScreen = () => {
    if (!pattern) return;
    const patW = pattern.width_mm * PX_PER_MM;
    const patH = pattern.height_mm * PX_PER_MM;
    const fitScale = Math.min(
      (stageSize.width - 120) / patW,
      (stageSize.height - 120) / patH,
      2.5
    );
    setScale(Math.max(0.3, fitScale));
    setPosition({
      x: (stageSize.width - patW * fitScale) / 2,
      y: (stageSize.height - patH * fitScale) / 2,
    });
  };

  useEffect(() => {
    fitToScreen();
  }, [pattern?.width_mm, pattern?.height_mm]);

  // Zoom centré sur le pointeur de la souris
  const handleWheel = (e) => {
    e.evt.preventDefault();
    const stage = e.target.getStage();
    const oldScale = stage.scaleX();
    const pointer = stage.getPointerPosition();

    const mousePointTo = {
      x: (pointer.x - stage.x()) / oldScale,
      y: (pointer.y - stage.y()) / oldScale,
    };

    const direction = e.evt.deltaY > 0 ? -1 : 1;
    const factor = 1.12;
    const newScale = Math.min(
      8,
      Math.max(0.25, direction > 0 ? oldScale * factor : oldScale / factor)
    );

    setScale(newScale);
    setPosition({
      x: pointer.x - mousePointTo.x * newScale,
      y: pointer.y - mousePointTo.y * newScale,
    });
  };

  if (!pattern) {
    return (
      <div
        ref={containerRef}
        className="flex flex-1 flex-col items-center justify-center bg-slate-950 text-slate-400"
      >
        <div className="max-w-md rounded-2xl border border-dashed border-slate-700 bg-slate-900/50 p-8 text-center">
          <p className="text-base font-medium text-slate-200">
            Aucun patron chargé
          </p>
          <p className="mt-2 text-sm text-slate-400">
            Importez une photo, un dessin ou une silhouette depuis le panneau de
            gauche pour générer instantanément votre carton de dentelle à
            l'échelle 1:1.
          </p>
        </div>
      </div>
    );
  }

  const patWidthPx = pattern.width_mm * PX_PER_MM;
  const patHeightPx = pattern.height_mm * PX_PER_MM;

  return (
    <div
      ref={containerRef}
      className="relative flex-1 overflow-hidden bg-slate-950 select-none"
    >
      {/* Barre d'outils flottante supérieure */}
      <div className="absolute top-4 left-4 z-10 flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-900/90 px-3 py-1.5 text-xs text-slate-200 shadow-lg backdrop-blur">
        <span className="font-mono text-slate-400">
          {pattern.width_mm} × {pattern.height_mm} mm
        </span>
        <span className="text-slate-700">|</span>
        <button
          type="button"
          onClick={() => setShowSourceImage((v) => !v)}
          className="flex items-center gap-1 rounded px-2 py-1 hover:bg-slate-800"
        >
          {showSourceImage ? (
            <Eye className="h-3.5 w-3.5 text-indigo-400" />
          ) : (
            <EyeOff className="h-3.5 w-3.5 text-slate-500" />
          )}
          <span>Calque image</span>
        </button>
        <span className="text-slate-700">|</span>
        <button
          type="button"
          onClick={() => setScale((s) => Math.min(8, s * 1.2))}
          className="rounded p-1 hover:bg-slate-800"
          title="Zoom +"
        >
          <ZoomIn className="h-3.5 w-3.5" />
        </button>
        <span className="w-10 text-center font-mono">
          {Math.round(scale * 100)}%
        </span>
        <button
          type="button"
          onClick={() => setScale((s) => Math.max(0.25, s / 1.2))}
          className="rounded p-1 hover:bg-slate-800"
          title="Zoom -"
        >
          <ZoomOut className="h-3.5 w-3.5" />
        </button>
        <button
          type="button"
          onClick={fitToScreen}
          className="rounded p-1 hover:bg-slate-800"
          title="Ajuster à l'écran"
        >
          <Maximize2 className="h-3.5 w-3.5" />
        </button>
      </div>

      {/* Indication d'interaction */}
      <div className="absolute bottom-4 left-4 z-10 rounded-lg border border-slate-800 bg-slate-900/80 px-3 py-1.5 text-[11px] text-slate-400">
        Cliquez sur une zone du patron pour lui assigner manuellement un point •
        Molette pour zoomer
      </div>

      {/* Stage Konva */}
      <Stage
        width={stageSize.width}
        height={stageSize.height}
        scaleX={scale}
        scaleY={scale}
        x={position.x}
        y={position.y}
        draggable
        onWheel={handleWheel}
        onDragEnd={(e) => {
          if (e.target === e.target.getStage()) {
            setPosition({ x: e.target.x(), y: e.target.y() });
          }
        }}
        onClick={(e) => {
          if (e.target === e.target.getStage()) {
            setSelectedZone(null);
          }
        }}
      >
        {/* Calque 1 : Feuille blanche + image source semi-transparente */}
        <Layer>
          <Rect
            x={0}
            y={0}
            width={patWidthPx}
            height={patHeightPx}
            fill="#ffffff"
            shadowColor="black"
            shadowBlur={24}
            shadowOpacity={0.45}
          />
          {showSourceImage && bgImg && (
            <KonvaImage
              image={bgImg}
              x={0}
              y={0}
              width={patWidthPx}
              height={patHeightPx}
              opacity={0.14}
              listening={false}
            />
          )}
        </Layer>

        {/* Calque 2 : Zones interactives, lignes de guidage et trous d'épingle */}
        <Layer>
          {pattern.zones.map((zone) => {
            const isHovered = hoveredZoneId === zone.zone_id;
            const isLocked = Boolean(zoneOverrides[zone.zone_id]);

            // Conversion des coordonnées cartésiennes (mm) -> coordonnées écran Konva
            const flatBoundary = zone.boundary_mm.flatMap(([x, y]) => [
              x * PX_PER_MM,
              (pattern.height_mm - y) * PX_PER_MM,
            ]);

            const strokeColor =
              zone.role === "contour"
                ? "#3B73BF"
                : zone.role === "fill"
                ? "#52525B"
                : "#A1A1AA";

            return (
              <Group
                key={zone.zone_id}
                onMouseEnter={() => {
                  setHoveredZoneId(zone.zone_id);
                  document.body.style.cursor = "pointer";
                }}
                onMouseLeave={() => {
                  setHoveredZoneId(null);
                  document.body.style.cursor = "default";
                }}
                onClick={(e) => {
                  e.cancelBubble = true;
                  const stage = e.target.getStage();
                  const pointer = stage.getPointerPosition();
                  setSelectedZone({
                    zone,
                    screenX: Math.min(pointer.x, stageSize.width - 260),
                    screenY: Math.min(pointer.y, stageSize.height - 280),
                  });
                }}
              >
                {/* Polygone cliquable de la zone */}
                {flatBoundary.length >= 6 && (
                  <Line
                    points={flatBoundary}
                    closed
                    fill={
                      isHovered
                        ? "rgba(99, 102, 241, 0.14)"
                        : isLocked
                        ? "rgba(16, 185, 129, 0.06)"
                        : "transparent"
                    }
                    stroke={isHovered ? "#6366F1" : "transparent"}
                    strokeWidth={1.2 / scale}
                  />
                )}

                {/* Lignes de guidage des fuseaux */}
                {zone.guide_lines.map((line, idx) => (
                  <Line
                    key={idx}
                    points={[
                      line.x1 * PX_PER_MM,
                      (pattern.height_mm - line.y1) * PX_PER_MM,
                      line.x2 * PX_PER_MM,
                      (pattern.height_mm - line.y2) * PX_PER_MM,
                    ]}
                    stroke={strokeColor}
                    strokeWidth={0.75}
                    dash={
                      line.style === "dashed"
                        ? [4, 3]
                        : line.style === "dotted"
                        ? [1.5, 2.5]
                        : undefined
                    }
                    listening={false}
                  />
                ))}

                {/* Trous d'épingle (diamètre 0.4 mm à l'échelle) */}
                {zone.pins.map(([px, py], idx) => (
                  <Circle
                    key={idx}
                    x={px * PX_PER_MM}
                    y={(pattern.height_mm - py) * PX_PER_MM}
                    radius={0.22 * PX_PER_MM}
                    fill="#09090B"
                    listening={false}
                  />
                ))}
              </Group>
            );
          })}

          {/* Ornements de bordure (picots, coquilles, festons) */}
          {pattern.ornaments?.guide_lines?.map((line, idx) => (
            <Line
              key={`orn-l-${idx}`}
              points={[
                line.x1 * PX_PER_MM,
                (pattern.height_mm - line.y1) * PX_PER_MM,
                line.x2 * PX_PER_MM,
                (pattern.height_mm - line.y2) * PX_PER_MM,
              ]}
              stroke="#B91C1C"
              strokeWidth={0.75}
              dash={line.style === "dotted" ? [1.5, 2] : undefined}
              listening={false}
            />
          ))}
          {pattern.ornaments?.pins?.map(([px, py], idx) => (
            <Circle
              key={`orn-p-${idx}`}
              x={px * PX_PER_MM}
              y={(pattern.height_mm - py) * PX_PER_MM}
              radius={0.22 * PX_PER_MM}
              fill="#09090B"
              listening={false}
            />
          ))}
        </Layer>
      </Stage>

      {/* Menu contextuel au clic sur une zone pour forcer un point spécifique */}
      {selectedZone && (
        <div
          style={{ left: selectedZone.screenX, top: selectedZone.screenY }}
          className="absolute z-20 w-60 rounded-xl border border-slate-700 bg-slate-900 p-3 text-xs text-slate-200 shadow-2xl"
        >
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <div>
              <span className="font-semibold text-indigo-300">
                Zone : {selectedZone.zone.role.toUpperCase()}
              </span>
              <p className="text-[11px] text-slate-400">
                Actuel : {selectedZone.zone.stitch_name}
              </p>
            </div>
            {zoneOverrides[selectedZone.zone.zone_id] ? (
              <Lock className="h-3.5 w-3.5 text-emerald-400" />
            ) : (
              <Unlock className="h-3.5 w-3.5 text-slate-500" />
            )}
          </div>

          <div className="mt-2 max-h-48 space-y-1 overflow-y-auto">
            <button
              type="button"
              onClick={() => {
                onSelectZoneStitch(selectedZone.zone.zone_id, null);
                setSelectedZone(null);
              }}
              className="w-full rounded px-2 py-1.5 text-left text-slate-300 hover:bg-slate-800"
            >
              Automatique (selon difficulté)
            </button>
            {stitches.map((st) => (
              <button
                key={st.id}
                type="button"
                onClick={() => {
                  onSelectZoneStitch(selectedZone.zone.zone_id, st.id);
                  setSelectedZone(null);
                }}
                className={`flex w-full items-center justify-between rounded px-2 py-1.5 text-left hover:bg-indigo-600/20 ${
                  selectedZone.zone.stitch_id === st.id
                    ? "bg-indigo-600/30 font-semibold text-indigo-200"
                    : "text-slate-200"
                }`}
              >
                <span className="truncate">{st.name}</span>
                <span className="ml-2 text-[10px] text-slate-400">
                  Niv.{st.difficulty}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
