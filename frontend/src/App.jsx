import React, { useEffect, useState } from "react";
import ControlPanel from "./components/ControlPanel";
import LaceCanvas from "./components/LaceCanvas";
import {
  downloadExportFile,
  fetchStitchesCatalog,
  generatePattern,
  uploadImage,
} from "./api/laceApi";

const STORAGE_KEY_KNOWN = "dentelle_known_stitches_v1";

export default function App() {
  const [stitches, setStitches] = useState([]);
  const [knownStitchIds, setKnownStitchIds] = useState(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY_KNOWN);
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });

  const [sessionId, setSessionId] = useState(null);
  const [sourceImageUrl, setSourceImageUrl] = useState(null);
  const [pattern, setPattern] = useState(null);
  const [zoneOverrides, setZoneOverrides] = useState({});
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);

  const [config, setConfig] = useState({
    targetWidthMm: 120,
    pitchMm: 3.0,
    angleDeg: 45,
    maxDifficulty: 3,
    density: 1.0,
    ornamentType: "none",
  });

  // Chargement initial du catalogue des points
  useEffect(() => {
    fetchStitchesCatalog()
      .then((list) => {
        setStitches(list);
        if (!knownStitchIds) {
          setKnownStitchIds(list.map((s) => s.id));
        }
      })
      .catch((err) => setErrorMsg(err.message));
  }, []);

  // Persistance des points maîtrisés dans localStorage
  useEffect(() => {
    if (knownStitchIds) {
      localStorage.setItem(STORAGE_KEY_KNOWN, JSON.stringify(knownStitchIds));
    }
  }, [knownStitchIds]);

  // Recalcul temps réel (debounce 150ms) à chaque changement de curseur ou de point
  useEffect(() => {
    if (!sessionId || !knownStitchIds) return;

    const timer = setTimeout(() => {
      setIsLoading(true);
      generatePattern(
        {
          session_id: sessionId,
          pitch_mm: config.pitchMm,
          angle_deg: config.angleDeg,
          max_difficulty: config.maxDifficulty,
          known_stitch_ids: knownStitchIds,
          density: config.density,
          ornament_type: config.ornamentType,
          zone_overrides: zoneOverrides,
        },
        config.targetWidthMm
      )
        .then((updated) => {
          setPattern(updated);
          setErrorMsg(null);
        })
        .catch((err) => setErrorMsg(err.message))
        .finally(() => setIsLoading(false));
    }, 150);

    return () => clearTimeout(timer);
  }, [sessionId, config, knownStitchIds, zoneOverrides]);

  const handleUploadFile = async (file) => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const previewUrl = URL.createObjectURL(file);
      setSourceImageUrl(previewUrl);
      setZoneOverrides({});

      const data = await uploadImage(file, config.targetWidthMm);
      setSessionId(data.session_id);
      setPattern(data.pattern);
    } catch (err) {
      setErrorMsg(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleToggleStitch = (stitchId) => {
    setKnownStitchIds((prev) =>
      prev.includes(stitchId)
        ? prev.filter((id) => id !== stitchId)
        : [...prev, stitchId]
    );
  };

  const handleSelectZoneStitch = (zoneId, stitchId) => {
    setZoneOverrides((prev) => {
      const next = { ...prev };
      if (stitchId === null) {
        delete next[zoneId];
      } else {
        next[zoneId] = stitchId;
      }
      return next;
    });
  };

  const handleExport = async (format) => {
    if (!sessionId) return;
    setIsLoading(true);
    try {
      await downloadExportFile(
        format,
        {
          session_id: sessionId,
          pitch_mm: config.pitchMm,
          angle_deg: config.angleDeg,
          max_difficulty: config.maxDifficulty,
          known_stitch_ids: knownStitchIds,
          density: config.density,
          ornament_type: config.ornamentType,
          zone_overrides: zoneOverrides,
        },
        config.targetWidthMm
      );
    } catch (err) {
      setErrorMsg(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-slate-950 font-sans">
      <ControlPanel
        config={config}
        onChangeConfig={(patch) => setConfig((c) => ({ ...c, ...patch }))}
        onUploadFile={handleUploadFile}
        onExport={handleExport}
        stitches={stitches}
        knownStitchIds={knownStitchIds || []}
        onToggleStitch={handleToggleStitch}
        overrideCount={Object.keys(zoneOverrides).length}
        onResetOverrides={() => setZoneOverrides({})}
        isLoading={isLoading}
        hasSession={Boolean(sessionId)}
      />

      <main className="relative flex flex-1 flex-col">
        {errorMsg && (
          <div className="absolute top-4 right-4 z-30 rounded-lg border border-rose-500/50 bg-rose-950/90 px-4 py-2 text-xs text-rose-200 shadow-lg">
            {errorMsg}
          </div>
        )}

        <LaceCanvas
          pattern={pattern}
          sourceImageUrl={sourceImageUrl}
          stitches={stitches}
          zoneOverrides={zoneOverrides}
          onSelectZoneStitch={handleSelectZoneStitch}
        />
      </main>
    </div>
  );
}
