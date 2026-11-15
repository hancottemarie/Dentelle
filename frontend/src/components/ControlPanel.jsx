import React from "react";
import { Upload, Download, Sliders, Sparkles, RotateCcw } from "lucide-react";
import StitchCatalog from "./StitchCatalog";

export default function ControlPanel({
  config,
  onChangeConfig,
  onUploadFile,
  onExport,
  stitches,
  knownStitchIds,
  onToggleStitch,
  overrideCount,
  onResetOverrides,
  isLoading,
  hasSession,
}) {
  return (
    <aside className="flex h-full w-88 shrink-0 flex-col border-r border-slate-800 bg-slate-900 text-slate-100">
      {/* En-tête */}
      <div className="border-b border-slate-800 p-4">
        <div className="flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-indigo-400" />
          <h1 className="text-base font-bold tracking-tight">
            Dentelle Aux Fuseaux 1:1
          </h1>
        </div>
        <p className="mt-1 text-xs text-slate-400">
          Générateur open-source de cartons techniques
        </p>

        {/* Bouton Import Image */}
        <label className="mt-3 flex cursor-pointer items-center justify-center gap-2 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-indigo-500">
          <Upload className="h-4 w-4" />
          <span>{hasSession ? "Changer d'image..." : "Importer une image"}</span>
          <input
            type="file"
            accept="image/png,image/jpeg,image/webp"
            className="hidden"
            onChange={(e) => {
              if (e.target.files?.[0]) onUploadFile(e.target.files[0]);
            }}
          />
        </label>
      </div>

      {/* Corps défilant des paramètres */}
      <div className="flex-1 space-y-5 overflow-y-auto p-4">
        {/* Section Dimensions & Grille */}
        <div className="space-y-3">
          <div className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-slate-400">
            <Sliders className="h-3.5 w-3.5" />
            <span>Dimensions & Grille</span>
          </div>

          {/* Largeur finale (mm) */}
          <div>
            <div className="flex justify-between text-xs">
              <span className="text-slate-300">Largeur du patron</span>
              <span className="font-mono font-semibold text-indigo-300">
                {config.targetWidthMm} mm
              </span>
            </div>
            <input
              type="range"
              min={50}
              max={300}
              step={5}
              value={config.targetWidthMm}
              onChange={(e) =>
                onChangeConfig({ targetWidthMm: Number(e.target.value) })
              }
              className="mt-1 w-full accent-indigo-500"
            />
          </div>

          {/* Pas de piquage (mm) */}
          <div>
            <div className="flex justify-between text-xs">
              <span className="text-slate-300">Pas de grille (piquage)</span>
              <span className="font-mono font-semibold text-indigo-300">
                {config.pitchMm.toFixed(1)} mm
              </span>
            </div>
            <input
              type="range"
              min={2.0}
              max={6.0}
              step={0.1}
              value={config.pitchMm}
              onChange={(e) =>
                onChangeConfig({ pitchMm: Number(e.target.value) })
              }
              className="mt-1 w-full accent-indigo-500"
            />
          </div>

          {/* Angle de maille */}
          <div>
            <span className="text-xs text-slate-300">Angle du réseau</span>
            <div className="mt-1.5 grid grid-cols-2 gap-2">
              {[
                { deg: 45, label: "45° (Torchon)" },
                { deg: 60, label: "60° (Cluny/Flandre)" },
              ].map((opt) => (
                <button
                  key={opt.deg}
                  type="button"
                  onClick={() => onChangeConfig({ angleDeg: opt.deg })}
                  className={`rounded-md border py-1.5 text-xs font-medium transition ${
                    config.angleDeg === opt.deg
                      ? "border-indigo-500 bg-indigo-500/20 text-indigo-200"
                      : "border-slate-700 bg-slate-800/50 text-slate-400 hover:border-slate-600"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Niveau de difficulté */}
          <div>
            <div className="flex justify-between text-xs">
              <span className="text-slate-300">Difficulté maximale</span>
              <span className="font-mono font-semibold text-indigo-300">
                {config.maxDifficulty} / 5
              </span>
            </div>
            <input
              type="range"
              min={1}
              max={5}
              step={1}
              value={config.maxDifficulty}
              onChange={(e) =>
                onChangeConfig({ maxDifficulty: Number(e.target.value) })
              }
              className="mt-1 w-full accent-indigo-500"
            />
          </div>

          {/* Densité de remplissage */}
          <div>
            <div className="flex justify-between text-xs">
              <span className="text-slate-300">Densité de remplissage</span>
              <span className="font-mono font-semibold text-indigo-300">
                {Math.round(config.density * 100)}%
              </span>
            </div>
            <input
              type="range"
              min={0.6}
              max={1.5}
              step={0.05}
              value={config.density}
              onChange={(e) =>
                onChangeConfig({ density: Number(e.target.value) })
              }
              className="mt-1 w-full accent-indigo-500"
            />
          </div>

          {/* Ornements de bordure */}
          <div>
            <span className="text-xs text-slate-300">Ornements de bordure</span>
            <select
              value={config.ornamentType}
              onChange={(e) =>
                onChangeConfig({ ornamentType: e.target.value })
              }
              className="mt-1 w-full rounded-md border border-slate-700 bg-slate-800 px-2.5 py-1.5 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
            >
              <option value="none">Aucun ornement extérieur</option>
              <option value="picots">Picots réguliers</option>
              <option value="shells">Coquilles (Éventails 5 épingles)</option>
              <option value="scallops">Festons (Grands éventails 7 épingles)</option>
            </select>
          </div>
        </div>

        {/* Bouton de réinitialisation des zones forcées au clic */}
        {overrideCount > 0 && (
          <button
            type="button"
            onClick={onResetOverrides}
            className="flex w-full items-center justify-center gap-1.5 rounded-md border border-slate-700 bg-slate-800/70 py-1.5 text-xs text-slate-300 hover:bg-slate-800"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            <span>Réinitialiser {overrideCount} zone(s) modifiée(s)</span>
          </button>
        )}

        <hr className="border-slate-800" />

        {/* Catalogue des points connus */}
        <StitchCatalog
          stitches={stitches}
          knownStitchIds={knownStitchIds}
          onToggleStitch={onToggleStitch}
          maxDifficulty={config.maxDifficulty}
          angleDeg={config.angleDeg}
        />
      </div>

      {/* Pied de panneau : Export 1:1 */}
      <div className="border-t border-slate-800 bg-slate-900/95 p-4">
        <div className="grid grid-cols-2 gap-2">
          <button
            type="button"
            disabled={!hasSession || isLoading}
            onClick={() => onExport("pdf")}
            className="flex items-center justify-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-2 text-xs font-semibold text-white transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-40"
          >
            <Download className="h-4 w-4" />
            <span>PDF 1:1</span>
          </button>
          <button
            type="button"
            disabled={!hasSession || isLoading}
            onClick={() => onExport("svg")}
            className="flex items-center justify-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs font-semibold text-slate-200 transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
          >
            <Download className="h-4 w-4" />
            <span>SVG (mm)</span>
          </button>
        </div>
      </div>
    </aside>
  );
}
