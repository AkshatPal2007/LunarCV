import React from 'react';
import { Compass, Globe, FileText, CheckCircle2, ShieldCheck, Cpu } from 'lucide-react';

export default function GeoFootprintMap() {
  // Homography 3x3 matrix values from registration pipeline
  const hMatrix = [
    ['0.9984', '-0.0124', '14.281'],
    ['0.0118', '0.9991', '-8.405'],
    ['0.0000', '0.0000', '1.0000'],
  ];

  return (
    <div className="w-full max-w-7xl mx-auto p-4 md:p-6 space-y-6">
      {/* Top Banner */}
      <div className="glass-panel p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="font-orbitron font-bold text-xl text-white tracking-wide flex items-center gap-2">
            <Compass className="w-6 h-6 text-cyan-400" />
            Geographic Overlap & Telemetry Scorecard
          </h2>
          <p className="text-xs text-slate-300 mt-1 font-mono">
            Lunar latitude/longitude footprint intersection & 3x3 projective homography matrix.
          </p>
        </div>

        <span className="glass-pill text-cyan-300 border-cyan-500/40 font-mono text-xs">
          Coordinates: 19.2°N, 43.1°E (Mare Tranquillitatis)
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Lat/Lon Geographic Footprint Overlay (Span 7) */}
        <div className="lg:col-span-7 glass-panel p-5 space-y-4">
          <div className="flex items-center justify-between text-xs font-mono">
            <span className="text-white font-semibold flex items-center gap-2">
              <Globe className="w-4 h-4 text-purple-400" />
              Lunar Footprint Intersection Map
            </span>
            <span className="text-emerald-400 font-bold">100% Georeferenced</span>
          </div>

          {/* Interactive Bounding Box Footprint Graphic */}
          <div className="relative w-full aspect-[16/10] rounded-xl overflow-hidden bg-[#070914] border border-white/20 p-4 flex items-center justify-center">
            {/* Lunar Grid lines */}
            <div className="absolute inset-0 bg-[radial-gradient(#38bdf8_1px,transparent_1px)] [background-size:24px_24px] opacity-20" />

            {/* Bounding Box 1: TMC-2 Footprint (Saffron Outline) */}
            <div className="absolute top-[15%] left-[20%] right-[25%] bottom-[20%] border-2 border-dashed border-amber-400 bg-amber-400/10 rounded-lg p-2 flex flex-col justify-between">
              <span className="text-[10px] font-mono text-amber-300 font-bold bg-black/80 px-2 py-0.5 rounded w-fit">
                Chandrayaan-2 TMC-2 Footprint (5.0m GSD)
              </span>
              <span className="text-[9px] font-mono text-amber-400 text-right">
                19.45°N / 42.80°E
              </span>
            </div>

            {/* Bounding Box 2: LRO NAC Reference (Cyan Outline) */}
            <div className="absolute top-[25%] left-[30%] right-[15%] bottom-[15%] border-2 border-cyan-400 bg-cyan-400/10 rounded-lg p-2 flex flex-col justify-between">
              <span className="text-[10px] font-mono text-cyan-300 font-bold bg-black/80 px-2 py-0.5 rounded w-fit self-end">
                LRO NAC Reference Swath (0.5m GSD)
              </span>
              <span className="text-[9px] font-mono text-cyan-400">
                18.90°N / 43.40°E
              </span>
            </div>

            {/* Intersection Highlight Box (Purple Glow) */}
            <div className="absolute top-[25%] left-[30%] right-[25%] bottom-[20%] border-2 border-purple-400 bg-purple-500/20 shadow-[0_0_20px_rgba(168,85,247,0.4)] rounded flex items-center justify-center">
              <div className="text-center bg-black/80 px-3 py-1.5 rounded border border-purple-400/40">
                <span className="text-xs font-orbitron font-bold text-purple-300 block">
                  GEOGRAPHIC OVERLAP REGION
                </span>
                <span className="text-[10px] font-mono text-slate-300">
                  Area: 42.8 km² • 100% Cropped
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Homography Matrix & Telemetry Scorecard (Span 5) */}
        <div className="lg:col-span-5 space-y-6">
          {/* Homography Matrix Card */}
          <div className="glass-panel p-5 space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-white/10">
              <h3 className="font-orbitron font-semibold text-sm text-white flex items-center gap-2">
                <Cpu className="w-4 h-4 text-purple-400" />
                MAGSAC++ Homography Matrix (H_3x3)
              </h3>
              <span className="text-[10px] font-mono text-purple-300">Sub-pixel Accurate</span>
            </div>

            {/* 3x3 Matrix Grid */}
            <div className="grid grid-cols-3 gap-2 p-3 bg-slate-950/80 rounded-xl border border-white/10 font-mono text-center text-xs">
              {hMatrix.map((row, rIdx) =>
                row.map((val, cIdx) => (
                  <div
                    key={`${rIdx}-${cIdx}`}
                    className="p-2.5 rounded bg-white/5 border border-white/10 text-amber-300 font-bold hover:border-purple-500/50 transition-all"
                  >
                    {val}
                  </div>
                ))
              )}
            </div>
            <p className="text-[10px] text-slate-400 font-mono">
              Projective transformation matrix mapping TMC-2 moving pixel coordinates `(x, y)` to LRO NAC reference `(x', y')`.
            </p>
          </div>

          {/* Project Summary Checklist Card */}
          <div className="glass-panel p-5 space-y-3">
            <h3 className="font-orbitron font-semibold text-sm text-white flex items-center gap-2 pb-2 border-b border-white/10">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              LunarCV Pipeline Status Checklist
            </h3>

            <div className="space-y-2 text-xs font-mono text-slate-300">
              <div className="flex items-center justify-between p-2 rounded bg-white/5">
                <span>✅ Memory mapped ~1.2 GB .img file</span>
                <span className="text-emerald-400 font-bold">Passed</span>
              </div>
              <div className="flex items-center justify-between p-2 rounded bg-white/5">
                <span>✅ CLAHE normalization & preprocessing</span>
                <span className="text-emerald-400 font-bold">Passed</span>
              </div>
              <div className="flex items-center justify-between p-2 rounded bg-white/5">
                <span>🐛 Homography direction bug fix</span>
                <span className="text-emerald-400 font-bold">Resolved</span>
              </div>
              <div className="flex items-center justify-between p-2 rounded bg-white/5">
                <span>🟡 Spatial uniformity tiled matching</span>
                <span className="text-amber-400 font-bold">Active Milestone</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
