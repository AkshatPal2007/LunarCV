import { useState } from "react";
import type { Mapping, Point, Visualization } from "./types";
import { useArtifact } from "./useArtifact";
import { processingPoint } from "./coordinates";
function Pane({
  name,
  path,
  apiKey,
  shape,
  points,
  frame,
  side,
  selected,
  onSelect,
  grid,
}: {
  name: string;
  path?: string;
  apiKey: string;
  shape: number[];
  points: Point[];
  frame: number[][];
  side: "source" | "reference";
  selected: number | null;
  onSelect: (id: number) => void;
  grid: boolean;
}) {
  const { url, error } = useArtifact(path, apiKey);
  const [height, width] = shape;
  return (
    <div className="image-pane">
      <div className="pane-label">
        {name}
        <span>
          {width} × {height} processing px
        </span>
      </div>
      {error ? (
        <p role="alert">{error}</p>
      ) : url ? (
        <svg
          role="group"
          aria-label={`${name} correspondence map`}
          viewBox={`0 0 ${width} ${height}`}
        >
          <image href={url} width={width} height={height} />
          {grid &&
            [1, 2, 3].map((i) => (
              <g key={i} className="grid-lines">
                <line
                  x1={(width * i) / 4}
                  x2={(width * i) / 4}
                  y1="0"
                  y2={height}
                />
                <line
                  x1="0"
                  x2={width}
                  y1={(height * i) / 4}
                  y2={(height * i) / 4}
                />
              </g>
            ))}
          {points.map((p) => {
            const [x, y] = processingPoint(p[side], frame);
            return (
              <g
                key={p.point_id}
                role="button"
                tabIndex={0}
                aria-label={`Select correspondence ${p.point_id} on ${side}`}
                onClick={() => onSelect(p.point_id)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onSelect(p.point_id);
                  }
                }}
                className={selected === p.point_id ? "match selected" : "match"}
              >
                <circle cx={x} cy={y} r={width / 60} />
                <path
                  d={`M${x - width / 90},${y}h${width / 45}M${x},${y - width / 90}v${width / 45}`}
                />
              </g>
            );
          })}
        </svg>
      ) : (
        <div className="image-loading">Loading real image…</div>
      )}
    </div>
  );
}
function Overlay({ data, apiKey }: { data: Visualization; apiKey: string }) {
  const [opacity, setOpacity] = useState(50);
  const ref = useArtifact(data.artifacts["reference.png"], apiKey);
  const reg = useArtifact(data.artifacts["registered.png"], apiKey);
  const support = useArtifact(data.artifacts["support_mask.png"], apiKey);
  const [showSupport, setShowSupport] = useState(false);
  return (
    <>
      <div className="overlay-stage">
        {ref.url && <img src={ref.url} alt="Reference processing window" />}
        {reg.url && (
          <img
            style={{ opacity: opacity / 100 }}
            src={reg.url}
            alt="Registered source quicklook"
          />
        )}
        {showSupport && support.url && (
          <img
            className="support"
            src={support.url}
            alt="Convex hull of fitted correspondences; not an accuracy confidence map"
          />
        )}
      </div>
      <div className="viewer-controls">
        <label>
          Source opacity{" "}
          <input
            aria-label="Source opacity"
            type="range"
            value={opacity}
            onChange={(e) => setOpacity(Number(e.target.value))}
          />{" "}
          {opacity}%
        </label>
        <label>
          <input
            type="checkbox"
            checked={showSupport}
            onChange={(e) => setShowSupport(e.target.checked)}
          />{" "}
          Show correspondence support hull
        </label>
      </div>
      <p className="caption">
        The support hull marks where correspondences exist. Pixels outside it
        are extrapolated. It does not establish accuracy.
      </p>
    </>
  );
}
function ArtifactView({
  path,
  apiKey,
  name,
}: {
  path?: string;
  apiKey: string;
  name: string;
}) {
  const { url, error } = useArtifact(path, apiKey);
  return error ? (
    <p role="alert">{error}</p>
  ) : url ? (
    <img className="single-product" src={url} alt={name} />
  ) : (
    <p>Product unavailable.</p>
  );
}
export default function Viewer({
  data,
  apiKey,
  selected,
  onSelect,
}: {
  data: Visualization;
  apiKey: string;
  selected: number | null;
  onSelect: (id: number) => void;
}) {
  const [mode, setMode] = useState("Correspondences");
  const [grid, setGrid] = useState(true);
  const [zoom, setZoom] = useState(100);
  const m: Mapping | null = data.mapping;
  return (
    <section className="viewer">
      <div className="viewer-toolbar">
        <div role="group" aria-label="Product view">
          {["Correspondences", "Overlay", "Checkerboard", "Registered"].map(
            (name) => (
              <button
                key={name}
                aria-pressed={mode === name}
                onClick={() => setMode(name)}
              >
                {name}
              </button>
            ),
          )}
        </div>
        <label className="zoom">
          Zoom{" "}
          <select
            aria-label="Image zoom"
            value={zoom}
            onChange={(e) => setZoom(Number(e.target.value))}
          >
            {[100, 150, 200].map((n) => (
              <option key={n}>{n}</option>
            ))}
          </select>
          %
        </label>
      </div>
      <div className="viewer-scroll">
        <div style={{ width: `${zoom}%` }}>
          {mode === "Correspondences" && m ? (
            <>
              <div className="image-pair">
                <Pane
                  name="01 / Source"
                  path={data.artifacts["source.png"]}
                  apiKey={apiKey}
                  shape={m.source_processing_shape}
                  points={data.points}
                  frame={m.source_processing_to_native}
                  side="source"
                  selected={selected}
                  onSelect={onSelect}
                  grid={grid}
                />
                <Pane
                  name="02 / Reference"
                  path={data.artifacts["reference.png"]}
                  apiKey={apiKey}
                  shape={m.output_shape}
                  points={data.points}
                  frame={m.reference_processing_to_native}
                  side="reference"
                  selected={selected}
                  onSelect={onSelect}
                  grid={grid}
                />
              </div>
              <div className="viewer-controls">
                <label>
                  <input
                    type="checkbox"
                    checked={grid}
                    onChange={(e) => setGrid(e.target.checked)}
                  />{" "}
                  4 × 4 coverage grid
                </label>
                <span>Click a crosshair to inspect its native pixels</span>
              </div>
            </>
          ) : mode === "Overlay" ? (
            <Overlay data={data} apiKey={apiKey} />
          ) : (
            <ArtifactView
              path={
                data.artifacts[
                  mode === "Checkerboard"
                    ? "checkerboard.png"
                    : "registered.png"
                ]
              }
              apiKey={apiKey}
              name={mode}
            />
          )}
        </div>
      </div>
    </section>
  );
}
