import { forwardRef, useCallback, useEffect, useImperativeHandle, useRef, useState } from "react";
import { Excalidraw } from "@excalidraw/excalidraw";
import "@excalidraw/excalidraw/index.css";
import { SYSTEM_DESIGN_SHAPES } from "../lib/systemDesignShapes";

const AUTOSAVE_DEBOUNCE_MS = 2000;
const SHAPE_INSERT_STEP = 24; // px cascade offset so repeated inserts of the same shape don't stack exactly on top of each other

const SystemDesignBoard = forwardRef(function SystemDesignBoard({ initialElements, onSave }, ref) {
  const [api, setApi] = useState(null);
  const restoredRef = useRef(false);
  const saveTimerRef = useRef(null);
  const insertCountRef = useRef(0);

  useImperativeHandle(ref, () => ({
    getElements: () => api?.getSceneElements() ?? [],
  }));

  // Restore a previously-saved diagram once, as soon as both the Excalidraw
  // API and the resumed data are available (whichever arrives second).
  useEffect(() => {
    if (!api || restoredRef.current || !initialElements?.length) return;
    restoredRef.current = true;
    api.updateScene({ elements: initialElements });
  }, [api, initialElements]);

  // Inserts a fresh copy of a recognizable system-design icon shape
  // (database, cache, load balancer, queue, CDN, API service) directly onto
  // the canvas, so candidates get a labeled component with one click instead
  // of building everything from generic rectangles — and without needing a
  // separate library panel alongside the drawing toolbar.
  const insertShape = useCallback((build) => {
    if (!api) return;
    const offset = 80 + (insertCountRef.current % 6) * SHAPE_INSERT_STEP;
    insertCountRef.current += 1;
    const newElements = build().map((el) => ({ ...el, x: el.x + offset, y: el.y + offset }));
    api.updateScene({ elements: [...api.getSceneElements(), ...newElements] });
  }, [api]);

  const handleChange = useCallback((elements) => {
    if (!onSave) return;
    if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    saveTimerRef.current = setTimeout(() => onSave(elements), AUTOSAVE_DEBOUNCE_MS);
  }, [onSave]);

  useEffect(() => () => {
    if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
  }, []);

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-white/5 px-5 py-4">
        <div>
          <span className="text-sm text-cream">Architecture board</span>
          <p className="mt-0.5 text-xs text-mute">Your diagram is shared with the interviewer whether or not it&apos;s complete</p>
        </div>
        <span className="inline-flex items-center gap-1.5 rounded-full bg-sage/15 px-3 py-1 text-xs text-sage">
          <span className="h-1.5 w-1.5 rounded-full bg-sage" />
          Live
        </span>
      </div>

      <div className="flex items-center gap-4 border-b border-white/5 bg-panelLight/30 px-5 py-2.5">
        <p className="text-xs text-mute">💡 Tips:</p>
        <p className="text-xs text-mute">Label your components clearly</p>
        <span className="text-white/10">·</span>
        <p className="text-xs text-mute">Use arrows to show data flow</p>
        <span className="text-white/10">·</span>
        <p className="text-xs text-mute">Think about scale &amp; failure points</p>
      </div>

      <div className="flex flex-wrap items-center gap-2 border-b border-white/5 px-5 py-2.5">
        <span className="text-xs text-mute">Shapes:</span>
        {SYSTEM_DESIGN_SHAPES.map((shape) => (
          <button
            key={shape.name}
            type="button"
            onClick={() => insertShape(shape.build)}
            disabled={!api}
            className="rounded-md border border-white/10 bg-panelLight/40 px-2.5 py-1 text-xs text-cream transition hover:border-sage/40 hover:bg-panelLight/70 disabled:opacity-50"
          >
            {shape.label}
          </button>
        ))}
      </div>

      <div className="relative flex-1" style={{ minHeight: "480px" }}>
        <Excalidraw
          excalidrawAPI={(a) => setApi(a)}
          onChange={handleChange}
          theme="dark"
          UIOptions={{
            canvasActions: {
              export: { saveFileToDisk: false },
              loadScene: false,
              saveToActiveFile: false,
              toggleTheme: false,
            },
            tools: { image: false },
          }}
        />
      </div>
    </div>
  );
});

export default SystemDesignBoard;
