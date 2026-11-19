import { useCallback, useEffect, useState } from "react";
import {
  ArrowDownToLine,
  ArrowRight,
  Check,
  ChevronRight,
  Crosshair,
  Layers,
  LoaderCircle,
  Orbit,
  Play,
  RefreshCw,
  ShieldCheck,
  Terminal,
  Upload,
  X,
} from "lucide-react";
import type {
  Job,
  Metrics,
  Pair,
  Product,
  Request,
  Results,
  Visualization,
} from "./types";
import { api, artifact } from "./api";
import Viewer from "./Viewer";
import NumberList from "./NumberList";
const terminal = (status: string) =>
  ["completed", "failed", "cancelled"].includes(status);
const number = (value: number | undefined, digits = 2) =>
  value === undefined ? "—" : value.toFixed(digits);
const errorText = (error: unknown) =>
  error instanceof Error ? error.message : String(error);
function Coverage({
  name,
  coverage,
}: {
  name: string;
  coverage: Metrics["coverage_source"];
}) {
  return (
    <div className="coverage">
      <div>
        <strong>{name}</strong>
        <span>{number(coverage.occupancy_pct, 1)}% occupied</span>
      </div>
      <div className="coverage-grid">
        {coverage.grid_counts.flat().map((count, i) => (
          <div
            key={i}
            style={{
              background: count ? "#deb977" : "#e6e9e3",
              color: "#172321",
            }}
            title={`${name} tile ${i + 1}: ${count} points`}
          >
            {count}
          </div>
        ))}
      </div>
      <small>
        Hull {number(coverage.hull_coverage_pct, 1)}% · CV {number(coverage.cv)}
      </small>
    </div>
  );
}
export default function Workspace() {
  const [apiKey, setApiKey] = useState("");
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [pairs, setPairs] = useState<Pair[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [history, setHistory] = useState<Job[]>([]);
  const [job, setJob] = useState<Job | null>(null);
  const [result, setResult] = useState<Results | null>(null);
  const [visual, setVisual] = useState<Visualization | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [request, setRequest] = useState<Request>({
    source_image_id: "",
    reference_image_id: "",
    matcher: "ensemble",
    features: "aliked",
    model: "affine",
  });
  const [prior, setPrior] = useState(
    "User-selected products. No independent controls supplied.",
  );
  const refresh = useCallback(
    async (signal?: AbortSignal) => {
      const [p, images, jobs] = await Promise.all([
        api<Pair[]>("/pairs", apiKey, { signal }),
        api<Product[]>("/images", apiKey, { signal }),
        api<Job[]>("/jobs", apiKey, { signal }),
      ]);
      setPairs(p);
      setProducts(images);
      setHistory(jobs);
      setConnected(true);
    },
    [apiKey],
  );
  useEffect(() => {
    const abort = new AbortController();
    // Synchronize connection state with the external API, never a simulated status.
    void (async () => {
      try {
        await refresh(abort.signal);
      } catch (e) {
        if (!abort.signal.aborted) {
          setConnected(false);
          setError(errorText(e));
        }
      }
    })();
    return () => abort.abort();
  }, [refresh]);
  const jobId = job?.job_id;
  useEffect(() => {
    if (!jobId) return;
    const abort = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      try {
        const status = await api<Job>(`/jobs/${jobId}`, apiKey, {
          signal: abort.signal,
        });
        if (abort.signal.aborted) return;
        setJob((previous) =>
          previous?.job_id === jobId ? { ...previous, ...status } : previous,
        );
        setConnected(true);
        if (terminal(status.status)) {
          const [r, v] = await Promise.all([
            api<Results>(`/jobs/${jobId}/results`, apiKey, {
              signal: abort.signal,
            }),
            api<Visualization>(`/jobs/${jobId}/visualization`, apiKey, {
              signal: abort.signal,
            }),
          ]);
          if (!abort.signal.aborted) {
            setResult(r);
            setVisual(v);
            setSelected(v.points[0]?.point_id ?? null);
            await refresh(abort.signal);
          }
        } else timer = setTimeout(poll, 1500);
      } catch (e) {
        if (!abort.signal.aborted) {
          setConnected(false);
          setError(errorText(e));
          timer = setTimeout(poll, 5000);
        }
      }
    };
    void poll();
    return () => {
      abort.abort();
      clearTimeout(timer);
    };
  }, [jobId, apiKey, refresh]);
  const choosePair = (pair: Pair) => {
    setRequest({
      ...pair.registration_request,
      matcher: "ensemble",
      features: "aliked",
      model: "affine",
    });
    setPrior(pair.prior_description);
    setNotice(
      "Development scene selected. Accuracy is not independently validated.",
    );
  };
  async function run() {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const created = await api<Job>("/register", apiKey, {
        method: "POST",
        body: JSON.stringify(request),
      });
      setResult(null);
      setVisual(null);
      setJob({
        ...created,
        source_name: products.find((p) => p.file_id === request.source_image_id)
          ?.filename,
        reference_name: products.find(
          (p) => p.file_id === request.reference_image_id,
        )?.filename,
      });
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  async function upload(file: File | undefined) {
    if (!file) return;
    setBusy(true);
    setError("");
    try {
      const body = new FormData();
      body.set("file", file);
      const uploaded = await api<{ file_id: string; filename: string }>(
        "/upload",
        apiKey,
        { method: "POST", body },
      );
      await refresh();
      setNotice(
        `Uploaded ${uploaded.filename}. Product ID: ${uploaded.file_id}. Select it below; OHRC IMG also needs its XML label.`,
      );
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  async function label(file: File | undefined, id: string) {
    if (!file || !id) return;
    setBusy(true);
    try {
      const body = new FormData();
      body.set("file", file);
      await api(`/upload/${id}/label`, apiKey, { method: "POST", body });
      setNotice("XML label attached to source product.");
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  async function download(name: string, path: string) {
    try {
      const blob = await artifact(path, apiKey);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = name;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) {
      setError(errorText(e));
    }
  }
  const metrics = result?.metrics;
  const point = visual?.points.find((p) => p.point_id === selected);
  const active = !!job && !terminal(job.status);
  const update = (key: keyof Request, value: Request[keyof Request]) =>
    setRequest({ ...request, [key]: value });
  return (
    <div className="app-shell">
      <a className="skip-link" href="#workspace">
        Skip to workspace
      </a>
      <aside className="sidebar">
        <a className="brand" href="/" aria-label="LunarCV home">
          <Orbit size={30} />
          <span>
            LunarCV<small>MISSION IMAGE REGISTRATION</small>
          </span>
        </a>
        <div className="sidebar-label">WORKSPACE</div>
        <div className="nav-current">
          <Crosshair size={18} /> Registration lab <span>01</span>
        </div>
        <div className="sidebar-label history-label">
          RECENT RUNS{" "}
          <button
            aria-label="Refresh job history"
            onClick={() => void refresh().catch((e) => setError(errorText(e)))}
          >
            <RefreshCw size={14} />
          </button>
        </div>
        <div className="history">
          {history.length ? (
            history.map((item) => (
              <button
                key={item.job_id}
                className={job?.job_id === item.job_id ? "current" : ""}
                onClick={() => {
                  setResult(null);
                  setVisual(null);
                  setJob(item);
                }}
              >
                <span className={`status-dot ${item.status}`} />
                <span>
                  <b>{item.job_id.slice(0, 8)}</b>
                  <small>{item.quality_decision || item.status}</small>
                </span>
                <ChevronRight size={13} />
              </button>
            ))
          ) : (
            <p>Completed and queued jobs appear here.</p>
          )}
        </div>
        <div className="sidebar-bottom">
          <ShieldCheck size={18} />
          <div>
            Evidence before accuracy<small>Development workspace · v0.3</small>
          </div>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <span>
            Workspace <ChevronRight size={13} /> Registration lab
          </span>
          <div className="connection">
            <span
              className={`status-dot ${connected ? "completed" : "failed"}`}
            />
            {connected ? "Backend connected" : "Backend unavailable"}
            <label>
              API key
              <input
                aria-label="API key"
                type="password"
                autoComplete="off"
                value={apiKey}
                onChange={(e) => {
                  setError("");
                  setApiKey(e.target.value);
                }}
                placeholder="Local session only"
              />
            </label>
          </div>
        </header>
        <main id="workspace">
          <div className="page-heading">
            <div>
              <div className="eyebrow">CROSS-SENSOR / LUNAR SURFACE</div>
              <h1>
                Registration lab<span>.</span>
              </h1>
              <p>Align mission imagery. Inspect every correspondence.</p>
            </div>
            <span className="development-badge">
              <span /> DEVELOPMENT DEMO
            </span>
          </div>
          {error && (
            <div className="alert error" role="alert">
              <X size={18} />
              <div>
                <strong>Action could not complete</strong>
                <p>{error}</p>
              </div>
              <button aria-label="Dismiss error" onClick={() => setError("")}>
                <X size={16} />
              </button>
            </div>
          )}
          {notice && (
            <div className="alert notice" role="status">
              <Check size={18} />
              {notice}
            </div>
          )}
          <section className="inputs card">
            <div className="section-title">
              <h2>
                <Layers size={17} /> Image pair
              </h2>
              <span>01 / Configure inputs</span>
            </div>
            <div className="pair-select">
              <label>
                Available real scene
                <select
                  aria-label="Available real scene"
                  defaultValue=""
                  onChange={(e) => {
                    const p = pairs.find((p) => p.pair_id === e.target.value);
                    if (p) choosePair(p);
                  }}
                >
                  <option value="">
                    Select a scene or configure products below
                  </option>
                  {pairs.map((p) => (
                    <option
                      key={p.pair_id}
                      disabled={!p.available}
                      value={p.pair_id}
                    >
                      {p.name}
                      {p.available ? "" : " · files unavailable"}
                    </option>
                  ))}
                </select>
              </label>
              <label className="upload-button">
                <Upload size={15} /> Upload mission image
                <input
                  type="file"
                  accept=".img,.tif,.tiff,.png,.jpg,.jpeg"
                  disabled={busy}
                  onChange={(e) => {
                    void upload(e.target.files?.[0]);
                    e.target.value = "";
                  }}
                />
              </label>
            </div>
            <div className="product-row">
              {(["source", "reference"] as const).map((side, i) => (
                <div className="product-config" key={side}>
                  <label>
                    <span className="eyebrow">
                      0{i + 1} / {side.toUpperCase()}
                    </span>
                    <select
                      aria-label={`${side} product`}
                      value={request[`${side}_image_id`]}
                      onChange={(e) => {
                        setPrior(
                          "User-selected products; explicit windows are search priors, not ground truth.",
                        );
                        setRequest({
                          ...request,
                          [`${side}_image_id`]: e.target.value,
                          [`${side}_bounds`]: undefined,
                        });
                      }}
                    >
                      <option value="">Select real product</option>
                      {products.map((p) => (
                        <option value={p.file_id} key={p.file_id}>
                          {p.filename}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Search window · x0, y0, x1, y1 (exclusive)
                    <NumberList
                      label={`${side} bounds`}
                      placeholder="Entire product (up to 32M pixels)"
                      value={request[`${side}_bounds`]}
                      onChange={(value) => update(`${side}_bounds`, value)}
                    />
                  </label>
                </div>
              ))}
            </div>
            <details className="advanced">
              <summary>
                Processing settings{" "}
                <span>
                  ALIKED + LightGlue / RIFT2 ·{" "}
                  {request.model === "similarity" ? "RANSAC" : "MAGSAC++"}
                </span>
              </summary>
              <div className="settings-row">
                <label>
                  Matcher
                  <select
                    value={request.matcher}
                    onChange={(e) => update("matcher", e.target.value)}
                  >
                    <option value="ensemble">LightGlue + RIFT2</option>
                    <option value="lightglue">LightGlue</option>
                    <option value="rift2">RIFT2</option>
                  </select>
                </label>
                <label>
                  Transform
                  <select
                    value={request.model}
                    onChange={(e) => update("model", e.target.value)}
                  >
                    {["similarity", "affine", "homography"].map((v) => (
                      <option key={v}>{v}</option>
                    ))}
                  </select>
                </label>
                <label>
                  Source scale divisors · x, y
                  <NumberList
                    label="Source scale divisors"
                    value={request.source_scale_xy || [1, 1]}
                    onChange={(value) => update("source_scale_xy", value)}
                  />
                </label>
                <label>
                  OHRC source XML label
                  <input
                    type="file"
                    accept=".xml"
                    disabled={busy || !request.source_image_id}
                    onChange={(e) =>
                      void label(e.target.files?.[0], request.source_image_id)
                    }
                  />
                </label>
              </div>
            </details>
            <div className="input-footer">
              <p>{prior}</p>
              <button
                className="primary"
                disabled={
                  busy ||
                  active ||
                  !connected ||
                  !request.source_image_id ||
                  !request.reference_image_id
                }
                onClick={() => void run()}
              >
                {busy || active ? (
                  <LoaderCircle className="spin" size={16} />
                ) : (
                  <Play size={15} />
                )}{" "}
                {active ? "Processing" : "Run registration"}
                <ArrowRight size={15} />
              </button>
            </div>
          </section>
          {job && (
            <section className="job-strip" aria-live="polite">
              <div>
                <span className={`status-dot ${job.status}`} />
                <b>{job.status}</b>
                <code>{job.job_id.slice(0, 8)}</code>
                {job.source_name && (
                  <span className="job-products">
                    {job.source_name} → {job.reference_name}
                  </span>
                )}
                <span>{job.message || "Job accepted"}</span>
              </div>
              {active && (
                <button
                  onClick={() =>
                    void api(`/jobs/${job.job_id}`, apiKey, {
                      method: "DELETE",
                    })
                      .then(() =>
                        setNotice(
                          "Cancellation requested; checked at stage boundaries.",
                        ),
                      )
                      .catch((e) => setError(errorText(e)))
                  }
                >
                  Cancel job
                </button>
              )}
              <progress
                aria-label="Registration progress"
                max="100"
                value={job.progress || 0}
              />
            </section>
          )}
          {metrics && (
            <>
              <div
                className={`quality-banner ${metrics.quality_decision === "REJECT" ? "rejected" : ""}`}
              >
                <ShieldCheck size={24} />
                <div>
                  <strong>
                    {metrics.quality_decision === "REJECT"
                      ? "Quality gate rejected this registration"
                      : "Geometrically usable · accuracy unvalidated"}
                  </strong>
                  <p>
                    {metrics.quality_reasons.join(" · ") ||
                      "Independent geometric checks are required before any accuracy claim."}
                  </p>
                </div>
                <span>FIXED QUALITY GATES</span>
              </div>
              <div className="metric-row">
                {[
                  [
                    "Fit RMSE",
                    `${number(metrics.fit_reprojection_rmse_px, 3)} px`,
                    "Native reference residual · not accuracy",
                  ],
                  [
                    "Geometric inliers",
                    `${metrics.magsac_inliers} / ${metrics.candidate_matches}`,
                    `${number(metrics.inlier_ratio * 100, 1)}% candidate inlier ratio`,
                  ],
                  [
                    "Source occupancy",
                    `${number(metrics.coverage_source.occupancy_pct, 1)}%`,
                    "Required ≥ 50% · 4 × 4 grid",
                  ],
                  [
                    "Engine time",
                    `${number(metrics.execution_time_s)} s`,
                    metrics.cache_hit
                      ? "Match cache hit · import time excluded"
                      : "Fresh matching · import time excluded",
                  ],
                ].map(([title, value, note]) => (
                  <div className="metric card" key={title}>
                    <span>{title}</span>
                    <strong>{value}</strong>
                    <small>{note}</small>
                  </div>
                ))}
              </div>
            </>
          )}
          <div className="analysis-layout">
            <section className="analysis-main card">
              <div className="section-title">
                <h2>
                  <Crosshair size={17} /> Registration products
                </h2>
                <span>02 / Inspect evidence</span>
              </div>
              {visual?.mapping ? (
                <Viewer
                  data={visual}
                  apiKey={apiKey}
                  selected={selected}
                  onSelect={setSelected}
                />
              ) : (
                <div className="empty-state">
                  <div className="orbital-mark">
                    <Crosshair size={44} />
                  </div>
                  <h3>
                    {active
                      ? "Registration is running"
                      : "Your mission images, in alignment."}
                  </h3>
                  <p>
                    {active
                      ? "Progress comes from the backend. Products appear when the job reaches a terminal state."
                      : "Choose a real image pair and run the pipeline. Image products and measured diagnostics will appear here."}
                  </p>
                  <div>
                    <span>01 Select products</span>
                    <ArrowRight size={15} />
                    <span>02 Register</span>
                    <ArrowRight size={15} />
                    <span>03 Verify</span>
                  </div>
                </div>
              )}
              {result?.error && (
                <div className="alert error" role="alert">
                  <Terminal size={20} />
                  <div>
                    <strong>Processing failed</strong>
                    <p>{result.error}</p>
                  </div>
                </div>
              )}
              {metrics && (
                <div className="coverage-section">
                  <div>
                    <h3>Spatial support</h3>
                    <p>
                      Coverage is measured across the entire processing window,
                      including empty cells.
                    </p>
                  </div>
                  <Coverage name="Source" coverage={metrics.coverage_source} />
                  <Coverage
                    name="Reference"
                    coverage={metrics.coverage_reference}
                  />
                </div>
              )}
            </section>
            <aside className="inspector card">
              <div className="section-title">
                <h2>Evidence inspector</h2>
                <span>03</span>
              </div>
              <div className="inspector-section">
                <div className="eyebrow">INDEPENDENT ACCURACY</div>
                <strong className="validation-status">
                  {metrics?.independent_validation.status === "unavailable"
                    ? "Not measured"
                    : metrics?.independent_validation.status ||
                      "Awaiting a run"}
                </strong>
                <p>
                  {metrics?.independent_validation.reason ||
                    "Fit residuals describe internal consistency. They do not measure absolute registration accuracy."}
                </p>
                {metrics?.independent_validation.rmse_reference_px != null && (
                  <p>
                    {number(
                      metrics.independent_validation.rmse_reference_px,
                      3,
                    )}{" "}
                    native reference px
                  </p>
                )}
              </div>
              <div className="inspector-section">
                <div className="eyebrow">SELECTED CORRESPONDENCE</div>
                {point ? (
                  <>
                    <label>
                      Point
                      <select
                        aria-label="Selected correspondence"
                        value={selected ?? ""}
                        onChange={(e) => setSelected(Number(e.target.value))}
                      >
                        {visual?.points.map((p) => (
                          <option key={p.point_id} value={p.point_id}>
                            #{p.point_id}
                          </option>
                        ))}
                      </select>
                    </label>
                    <dl>
                      <dt>Source native x, y</dt>
                      <dd>
                        {point.source.map((v) => number(v, 3)).join(", ")}
                      </dd>
                      <dt>Reference native x, y</dt>
                      <dd>
                        {point.reference.map((v) => number(v, 3)).join(", ")}
                      </dd>
                      <dt>Fit residual</dt>
                      <dd>
                        {number(point.fit_residual_reference_px, 3)} ref px
                      </dd>
                      <dt>Primary model confidence</dt>
                      <dd>
                        {number(point.confidence, 4)}{" "}
                        <small>(not accuracy)</small>
                      </dd>
                      <dt>RIFT2 agreement / refined</dt>
                      <dd>
                        {point.secondary_agreement ? "Yes" : "No"} /{" "}
                        {point.refined ? "Yes" : "No"}
                      </dd>
                    </dl>
                  </>
                ) : (
                  <p>
                    Select a correspondence in a completed run to trace its
                    original pixels.
                  </p>
                )}
              </div>
              <div className="inspector-section">
                <details>
                  <summary>Transformation matrix</summary>
                  {visual?.mapping ? (
                    <>
                      <p>
                        {visual.mapping.model} · native source → native
                        reference
                      </p>
                      <pre>
                        {visual.mapping.matrix
                          .map((row) => row.map((v) => v.toFixed(6)).join("  "))
                          .join("\n")}
                      </pre>
                      <p>{visual.mapping.pixel_convention}</p>
                      <small>{visual.mapping.georeferencing_status}</small>
                    </>
                  ) : (
                    <p>No fitted transformation.</p>
                  )}
                </details>
              </div>
              <div className="inspector-section">
                <details>
                  <summary>Stage timings</summary>
                  {metrics &&
                    Object.entries(metrics.stage_timings_s).map(
                      ([stage, time]) => (
                        <div className="timing" key={stage}>
                          <span>{stage.replaceAll("_", " ")}</span>
                          <code>{time.toFixed(3)}s</code>
                        </div>
                      ),
                    )}
                </details>
              </div>
              <div className="inspector-section">
                <h3>Export evidence</h3>
                <p>
                  Diagnostic products retain the quality decision. A rejected
                  warp is not a validated map.
                </p>
                <div className="downloads">
                  {Object.entries(visual?.artifacts || {})
                    .filter(
                      ([name]) =>
                        ![
                          "source.png",
                          "reference.png",
                          "valid_mask.png",
                          "support_mask.png",
                        ].includes(name),
                    )
                    .map(([name, path]) => (
                      <button
                        key={name}
                        onClick={() => void download(name, path)}
                      >
                        <ArrowDownToLine size={13} />
                        {name}
                      </button>
                    ))}
                </div>
              </div>
            </aside>
          </div>
          <footer className="workspace-footer">
            <span>LunarCV / Mission registration workspace</span>
            <span>
              Real imagery. Traceable pixels. Transparent limitations.
            </span>
          </footer>
        </main>
      </div>
    </div>
  );
}
