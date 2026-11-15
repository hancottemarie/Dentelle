import React from "react";
import { CheckSquare, Square, AlertTriangle } from "lucide-react";

export default function StitchCatalog({
  stitches,
  knownStitchIds,
  onToggleStitch,
  maxDifficulty,
  angleDeg,
}) {
  const activeCount = stitches.filter(
    (s) =>
      knownStitchIds.includes(s.id) &&
      s.difficulty <= maxDifficulty &&
      s.grid_angles.includes(angleDeg)
  ).length;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          Points maîtrisés ({knownStitchIds.length}/{stitches.length})
        </h3>
        <span className="text-xs text-slate-400">
          {activeCount} actif(s)
        </span>
      </div>

      {activeCount === 0 && (
        <div className="flex items-start gap-2 rounded-lg border border-amber-500/40 bg-amber-500/10 p-2.5 text-xs text-amber-200">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-400" />
          <span>
            Aucun point coché ne correspond à la difficulté ≤ {maxDifficulty} et
            l'angle {angleDeg}°. Le Point Toilé sera utilisé par défaut.
          </span>
        </div>
      )}

      <div className="space-y-1.5">
        {stitches.map((stitch) => {
          const isChecked = knownStitchIds.includes(stitch.id);
          const isCompatible =
            stitch.difficulty <= maxDifficulty &&
            stitch.grid_angles.includes(angleDeg);

          return (
            <button
              key={stitch.id}
              type="button"
              onClick={() => onToggleStitch(stitch.id)}
              className={`w-full rounded-lg border p-2.5 text-left transition ${
                isChecked
                  ? isCompatible
                    ? "border-indigo-500/50 bg-indigo-500/10 text-slate-100"
                    : "border-slate-700 bg-slate-800/40 text-slate-400"
                  : "border-slate-800 bg-slate-900/60 text-slate-500 hover:border-slate-700"
              }`}
            >
              <div className="flex items-start gap-2.5">
                {isChecked ? (
                  <CheckSquare className="mt-0.5 h-4 w-4 shrink-0 text-indigo-400" />
                ) : (
                  <Square className="mt-0.5 h-4 w-4 shrink-0 text-slate-600" />
                )}

                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate text-sm font-medium">
                      {stitch.name}
                    </span>
                    <span
                      className={`shrink-0 rounded px-1.5 py-0.5 text-[10px] font-semibold ${
                        stitch.difficulty <= 2
                          ? "bg-emerald-500/20 text-emerald-300"
                          : stitch.difficulty <= 3
                          ? "bg-amber-500/20 text-amber-300"
                          : "bg-rose-500/20 text-rose-300"
                      }`}
                    >
                      Niv. {stitch.difficulty}/5
                    </span>
                  </div>
                  <p className="mt-0.5 line-clamp-2 text-xs text-slate-400">
                    {stitch.description}
                  </p>
                  <div className="mt-1 flex items-center gap-2 text-[10px] text-slate-500">
                    <span>Grille : {stitch.grid_angles.join("° / ")}°</span>
                    <span>•</span>
                    <span>Pas min : {stitch.min_pitch_mm} mm</span>
                  </div>
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
