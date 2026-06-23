import { forwardRef, useImperativeHandle, useState } from "react";
import { Excalidraw } from "@excalidraw/excalidraw";
import "@excalidraw/excalidraw/index.css";

const SystemDesignBoard = forwardRef(function SystemDesignBoard(_props, ref) {
  const [api, setApi] = useState(null);

  useImperativeHandle(ref, () => ({
    getElements: () => api?.getSceneElements() ?? [],
  }));

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-white/5 px-5 py-4">
        <span className="text-sm text-mute">Architecture board</span>
        <span className="text-xs text-mute">Sketch your design — the interviewer can read it</span>
      </div>
      <div className="relative flex-1" style={{ minHeight: "480px" }}>
        <Excalidraw
          excalidrawAPI={(a) => setApi(a)}
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
