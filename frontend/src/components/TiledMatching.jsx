import React, { useState } from 'react';
import { Grid, CheckCircle2, Circle, ArrowRight, ShieldCheck, RefreshCw } from 'lucide-react';

export default function TiledMatching() {
  const [activeStep, setActiveStep] = useState(2); // Step 2: Tiled matching

  const steps = [
    { id: 1, title: 'Cropping Overlap', status: 'completed', color: 'text-amber-400', bg: 'bg-amber-400' },
    { id: 2, title: 'Tiled Matching', status: 'active', color: 'text-emerald-400', bg: 'bg-emerald-400' },
    { id: 3, title: 'Sub-Pixel Refinement', status: 'pending', color: 'text-cyan-400', bg: 'bg-cyan-400' },
    { id: 4, title: 'Spatial Uniformity Filter', status: 'pending', color: 'text-cyan-400', bg: 'bg-cyan-400' },
    { id: 5, title: 'Evaluation & Scorecard', status: 'pending', color: 'text-purple-400', bg: 'bg-purple-400' },
  ];

  // Generate 80 green keypoints spread over 4 quadrants
  const greenPoints = Array.from({ length: 72 }, (_, i) => ({
    id: i,
    x: 10 + (i % 8) * 11 + Math.random() * 4,
    y: 10 + Math.floor(i / 8) * 9 + Math.random() * 3,
  }));

  // Yellow cross-quadrant match vectors
  const vectors = [
    { x1: 25, y1: 20, x2: 65, y2: 30 },
    { x1: 35, y1: 45, x2: 78, y2: 50 },
    { x1: 18, y1: 75, x2: 62, y2: 70 },
    { x1: 42, y1: 85, x2: 85, y2: 80 },
    { x1: 30, y1: 35, x2: 70, y2: 25 },
  ];

  return (
    <div className="w-full max-w-7xl mx-auto p-4 md:p-6 space-y-6">
      {/* Top Title Banner */}
      <div className="glass-panel p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="font-orbitron font-bold text-xl text-white tracking-wide flex items-center gap-2">
              <Grid className="w-6 h-6 text-emerald-400" />
              Tiled Constrained Matching
            </h2>
            <span className="glass-pill text-emerald-300 border-emerald-500/40 font-mono text-xs">
              Solution for Clustered Keypoints
            </span>
          </div>
          <p className="text-xs text-slate-300 mt-1 font-mono">
            Partitioning image overlap region into sub-tiles guarantees spatially uniform feature distribution and eliminates homography drift.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <span className="glass-pill text-amber-300 font-mono text-xs">
            Grid: 4x4 Tiles • 1024x1024 px
          </span>
        </div>
      </div>

      {/* Grid Content: 4-Quadrant View + Right Step Timeline (Matching Snapshot 5) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: 4-Tile Grid View (Span 8) */}
        <div className="lg:col-span-8 glass-panel p-5 relative overflow-hidden">
          <div className="flex items-center justify-between mb-3 text-xs font-mono">
            <span className="text-white font-semibold">TMC-2 & LRO NAC Overlap Quadrants</span>
            <span className="text-emerald-400 font-bold flex items-center gap-1">
              <CheckCircle2 className="w-3.5 h-3.5" /> 72 Green Inliers Distributed
            </span>
          </div>

          {/* 4 Quadrant Tile Box */}
          <div className="relative w-full aspect-[4/3] rounded-xl overflow-hidden border border-white/20 bg-black/80">
            {/* 4 Grid Background Image Tiles */}
            <div className="grid grid-cols-2 grid-rows-2 w-full h-full gap-1 p-1 bg-slate-900">
              <div className="relative overflow-hidden rounded border border-emerald-500/30">
                <img src="/assets/tmc2.jpg" alt="Tile 1" className="w-full h-full object-cover filter contrast-120" />
                <span className="absolute top-2 left-2 px-2 py-0.5 bg-black/70 rounded text-[9px] font-mono text-emerald-300">
                  Tile 1 (NW)
                </span>
              </div>
              <div className="relative overflow-hidden rounded border border-emerald-500/30">
                <img src="/assets/lronac.jpg" alt="Tile 2" className="w-full h-full object-cover filter contrast-110" />
                <span className="absolute top-2 right-2 px-2 py-0.5 bg-black/70 rounded text-[9px] font-mono text-emerald-300">
                  Tile 2 (NE)
                </span>
              </div>
              <div className="relative overflow-hidden rounded border border-emerald-500/30">
                <img src="/assets/lronac.jpg" alt="Tile 3" className="w-full h-full object-cover filter contrast-115" />
                <span className="absolute bottom-2 left-2 px-2 py-0.5 bg-black/70 rounded text-[9px] font-mono text-emerald-300">
                  Tile 3 (SW)
                </span>
              </div>
              <div className="relative overflow-hidden rounded border border-emerald-500/30">
                <img src="/assets/tmc2.jpg" alt="Tile 4" className="w-full h-full object-cover filter contrast-125" />
                <span className="absolute bottom-2 right-2 px-2 py-0.5 bg-black/70 rounded text-[9px] font-mono text-emerald-300">
                  Tile 4 (SE)
                </span>
              </div>
            </div>

            {/* SVG Overlay: Green Points & Yellow Match Lines (Matching Snapshot 5) */}
            <svg className="absolute inset-0 w-full h-full pointer-events-none z-10">
              {/* Yellow match vectors */}
              {vectors.map((v, idx) => (
                <line
                  key={`vec-${idx}`}
                  x1={`${v.x1}%`}
                  y1={`${v.y1}%`}
                  x2={`${v.x2}%`}
                  y2={`${v.y2}%`}
                  stroke="#fbbf24"
                  strokeWidth="2"
                  strokeDasharray="4,4"
                  className="animate-pulse"
                />
              ))}

              {/* Green Distributed Points */}
              {greenPoints.map((p) => (
                <circle
                  key={`pt-${p.id}`}
                  cx={`${p.x}%`}
                  cy={`${p.y}%`}
                  r="4"
                  fill="#4ade80"
                  stroke="#ffffff"
                  strokeWidth="1"
                  className="opacity-90 hover:opacity-100 hover:scale-125 transition-all"
                />
              ))}
            </svg>
          </div>
        </div>

        {/* Right Column: Step Timeline Panel (Span 4) (Matching Snapshot 5) */}
        <div className="lg:col-span-4 glass-panel p-6 flex flex-col justify-between">
          <div>
            <h3 className="font-orbitron font-semibold text-sm text-white mb-6 flex items-center justify-between pb-3 border-b border-white/10">
              <span>Pipeline Stage Progression</span>
              <span className="text-xs font-mono text-emerald-400">Phase 2/5</span>
            </h3>

            {/* Step Timeline Items */}
            <div className="space-y-6 relative before:absolute before:left-3.5 before:top-3 before:bottom-3 before:w-[2px] before:bg-white/10">
              {steps.map((s) => {
                const isCurrent = s.id === activeStep;
                const isDone = s.id < activeStep;

                return (
                  <div key={s.id} className="flex items-start gap-4 relative z-10 group cursor-pointer" onClick={() => setActiveStep(s.id)}>
                    <div
                      className={`w-7 h-7 rounded-full flex items-center justify-center border-2 transition-all ${
                        isDone
                          ? 'bg-amber-400 border-amber-400 text-black'
                          : isCurrent
                          ? 'bg-emerald-500 border-white text-black shadow-lg shadow-emerald-500/40 animate-bounce'
                          : 'bg-slate-900 border-white/20 text-slate-500'
                      }`}
                    >
                      {isDone ? (
                        <CheckCircle2 className="w-4 h-4" />
                      ) : (
                        <span className="font-mono text-xs font-bold">{s.id}</span>
                      )}
                    </div>

                    <div className="flex-1 pt-0.5">
                      <h4
                        className={`font-orbitron text-xs font-semibold tracking-wide ${
                          isCurrent
                            ? 'text-emerald-300 font-bold text-sm'
                            : isDone
                            ? 'text-amber-300'
                            : 'text-slate-400'
                        }`}
                      >
                        {s.title}
                      </h4>
                      <p className="text-[11px] font-mono text-slate-400 mt-0.5">
                        {s.id === 1 && 'Metadata crop area calculated'}
                        {s.id === 2 && 'Partitioning 4x4 sub-grid & matching'}
                        {s.id === 3 && 'Lucas-Kanade intensity interpolation'}
                        {s.id === 4 && 'Grid occupancy density check'}
                        {s.id === 5 && 'Final registered raster export'}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="pt-6 border-t border-white/10 mt-6">
            <button
              onClick={() => setActiveStep((prev) => (prev % 5) + 1)}
              className="w-full py-2.5 rounded-xl font-orbitron font-semibold text-xs text-black bg-gradient-to-r from-emerald-400 to-teal-400 hover:from-emerald-300 hover:to-teal-300 shadow-lg shadow-emerald-400/20 transition-all flex items-center justify-center gap-2"
            >
              <span>ADVANCE TO NEXT STEP</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
