import React, { useState } from 'react';
import { 
  Sun, 
  ArrowRight, 
  AlertTriangle, 
  Layers, 
  Sliders, 
  ShieldCheck,
  CheckCircle,
  HelpCircle
} from 'lucide-react';

export default function MultiModalPipeline() {
  const [committeeAngle, setCommitteeAngle] = useState(110);
  const [scaleFactor, setScaleFactor] = useState(20);

  return (
    <div className="w-full max-w-6xl mx-auto p-4 md:p-6 space-y-6">
      {/* Title Header Card matching Snapshot 2 */}
      <div className="glass-panel p-6 border-l-4 border-l-purple-500 relative overflow-hidden">
        <div className="flex items-center justify-between mb-2">
          <h2 className="font-orbitron font-extrabold text-2xl text-white tracking-wider flex items-center gap-3">
            <Layers className="w-7 h-7 text-purple-400" />
            Multi-Modal Registration
          </h2>
          <span className="glass-pill text-amber-300 border-amber-500/40 font-mono text-xs">
            Chandrayaan-2 Payloads (OHRC • TMC-2 • IIRS)
          </span>
        </div>
        <p className="text-sm text-slate-300 max-w-3xl leading-relaxed">
          Background Image Registration aligns multi-sensor optical images taken under varying solar illumination angles, viewing geometries, and Ground Sampling Distances (GSD) into a unified lunar coordinate framework.
        </p>
      </div>

      {/* Sensor Pipeline Flow Diagram (Matching Snapshot 2) */}
      <div className="glass-panel p-6 md:p-8 relative">
        <div className="text-xs font-mono text-slate-400 mb-6 flex items-center justify-between">
          <span>SENSOR INPUTS & SOLAR ANGLE CONVERSION</span>
          <span className="text-purple-400 font-semibold">TMC-2 Reference Base</span>
        </div>

        {/* 3 Sensor Flow Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 relative items-center">
          {/* Sensor 1: OHRC (Narrow Angle) */}
          <div className="glass-panel p-4 flex flex-col items-center text-center relative group hover:border-amber-400/60">
            <div className="absolute -top-3 px-3 py-0.5 rounded-full bg-amber-400 text-black font-orbitron font-bold text-[10px]">
              OHRC (High Res)
            </div>
            <div className="w-full aspect-square rounded-xl overflow-hidden mb-3 border border-white/20 relative shadow-lg">
              <img
                src="/assets/tmc2.jpg"
                alt="OHRC Sensor"
                className="w-full h-full object-cover filter contrast-125 brightness-90 group-hover:scale-105 transition-all duration-500"
              />
              {/* Sun Angle Ray Overlay */}
              <div className="absolute top-2 left-2 flex items-center gap-1 bg-black/70 backdrop-blur-md px-2 py-1 rounded-full border border-amber-400/40">
                <Sun className="w-4 h-4 text-amber-400 sun-pulse" />
                <span className="text-[10px] font-mono text-amber-300 font-bold">Sun 42°</span>
              </div>
            </div>
            <h4 className="font-orbitron font-semibold text-sm text-white">OHRC Payload</h4>
            <span className="text-xs font-mono text-slate-400">Narrow Angle (0.25m GSD)</span>
          </div>

          {/* Connection 1: Sun Angle Shift */}
          <div className="hidden md:flex flex-col items-center justify-center space-y-2">
            <div className="flex items-center gap-2 text-amber-400 font-mono text-xs font-semibold bg-amber-400/10 px-3 py-1.5 rounded-full border border-amber-400/30">
              <Sun className="w-4 h-4 sun-pulse" />
              <span>dz: CaHls Conversion</span>
            </div>
            <ArrowRight className="w-6 h-6 text-purple-400 animate-pulse" />
          </div>

          {/* Sensor 2: TMC-2 (Normal Angle) */}
          <div className="glass-panel p-4 flex flex-col items-center text-center relative group hover:border-purple-400/60">
            <div className="absolute -top-3 px-3 py-0.5 rounded-full bg-purple-500 text-white font-orbitron font-bold text-[10px]">
              TMC-2 (Primary)
            </div>
            <div className="w-full aspect-square rounded-xl overflow-hidden mb-3 border border-white/20 relative shadow-lg">
              <img
                src="/assets/lronac.jpg"
                alt="TMC Sensor"
                className="w-full h-full object-cover filter contrast-115 group-hover:scale-105 transition-all duration-500"
              />
              <div className="absolute top-2 left-2 flex items-center gap-1 bg-black/70 backdrop-blur-md px-2 py-1 rounded-full border border-purple-400/40">
                <Sun className="w-4 h-4 text-amber-400 sun-pulse" />
                <span className="text-[10px] font-mono text-purple-300 font-bold">Sun 65°</span>
              </div>
            </div>
            <h4 className="font-orbitron font-semibold text-sm text-white">TMC Payload</h4>
            <span className="text-xs font-mono text-slate-400">Normal Angle (5.0m GSD)</span>
          </div>

          {/* Connection 2: Scaled Angle Shift */}
          <div className="hidden md:flex flex-col items-center justify-center space-y-2">
            <div className="flex items-center gap-2 text-cyan-400 font-mono text-xs font-semibold bg-cyan-400/10 px-3 py-1.5 rounded-full border border-cyan-400/30">
              <Sun className="w-4 h-4 sun-pulse" />
              <span>b: CaHls Scaled</span>
            </div>
            <ArrowRight className="w-6 h-6 text-cyan-400 animate-pulse" />
          </div>

          {/* Sensor 3: IIRS (Scaled Angle) */}
          <div className="glass-panel p-4 flex flex-col items-center text-center relative group hover:border-cyan-400/60">
            <div className="absolute -top-3 px-3 py-0.5 rounded-full bg-cyan-500 text-black font-orbitron font-bold text-[10px]">
              IIRS (Spectrometer)
            </div>
            <div className="w-full aspect-square rounded-xl overflow-hidden mb-3 border border-white/20 relative shadow-lg">
              <img
                src="/assets/tmc2.jpg"
                alt="IIRS Sensor"
                className="w-full h-full object-cover filter brightness-125 sepia-[0.3] group-hover:scale-105 transition-all duration-500"
              />
              <div className="absolute top-2 left-2 flex items-center gap-1 bg-black/70 backdrop-blur-md px-2 py-1 rounded-full border border-cyan-400/40">
                <Sun className="w-4 h-4 text-amber-400 sun-pulse" />
                <span className="text-[10px] font-mono text-cyan-300 font-bold">Sun 80°</span>
              </div>
            </div>
            <h4 className="font-orbitron font-semibold text-sm text-white">IIRS Payload</h4>
            <span className="text-xs font-mono text-slate-400">Scaled Angle (80m GSD)</span>
          </div>
        </div>

        {/* Warning Banner Box (Matching Snapshot 2) */}
        <div className="mt-8 p-4 rounded-xl bg-amber-500/10 border border-amber-500/40 flex items-start gap-3 backdrop-blur-md">
          <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
          <div>
            <h4 className="font-orbitron font-bold text-xs text-amber-300 tracking-wide">
              Sub-pixel Accuracy Notice
            </h4>
            <p className="text-xs text-amber-200/80 mt-1 font-mono leading-relaxed">
              Global homography alignment failed due to high illumination and scale variance across orbital passes. Switch to <strong>Tiled Constrained Matching</strong> for sub-pixel accuracy refinement.
            </p>
          </div>
        </div>

        {/* Bottom Accept Committee Slider (Matching Snapshot 2) */}
        <div className="mt-6 pt-6 border-t border-white/10 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-4 w-full sm:w-auto">
            <span className="text-xs font-mono text-slate-300 shrink-0">Accept Committee:</span>
            <div className="flex items-center gap-3 w-full sm:w-64">
              <input
                type="range"
                min="20"
                max="150"
                value={committeeAngle}
                onChange={(e) => setCommitteeAngle(Number(e.target.value))}
              />
              <span className="glass-pill text-amber-300 font-mono font-bold text-xs shrink-0">
                {committeeAngle}%
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3 text-xs font-mono text-slate-400">
            <span>Frame Index:</span>
            <span className="text-purple-300 font-bold bg-purple-900/40 px-3 py-1 rounded border border-purple-500/30">
              11095 / 306
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
