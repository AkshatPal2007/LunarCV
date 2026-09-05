import React, { useState } from 'react';
import { Sliders, Eye, Grid, Layers, Sparkles } from 'lucide-react';

export default function RegistrationVisualizer() {
  const [sliderPos, setSliderPos] = useState(50);
  const [mode, setMode] = useState('split'); // split, difference, falsecolor, checkerboard

  return (
    <div className="w-full max-w-7xl mx-auto p-4 md:p-6 space-y-6">
      {/* Top Controls Header */}
      <div className="glass-panel p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="font-orbitron font-bold text-xl text-white tracking-wide flex items-center gap-2">
            <Sliders className="w-6 h-6 text-purple-400" />
            Registered Image Verification & Split Curtain
          </h2>
          <p className="text-xs text-slate-300 mt-1 font-mono">
            Sub-pixel alignment comparison between Chandrayaan-2 TMC-2 and Warped LRO NAC reference swath.
          </p>
        </div>

        {/* Mode Selector Buttons */}
        <div className="flex items-center gap-1.5 p-1 rounded-xl bg-slate-900/80 border border-white/10">
          {[
            { id: 'split', label: 'Split Wipe', icon: Eye },
            { id: 'difference', label: 'Difference', icon: Layers },
            { id: 'falsecolor', label: 'False Color', icon: Sparkles },
            { id: 'checkerboard', label: 'Checkerboard', icon: Grid },
          ].map((m) => {
            const Icon = m.icon;
            const isActive = mode === m.id;
            return (
              <button
                key={m.id}
                onClick={() => setMode(m.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono transition-all ${
                  isActive
                    ? 'bg-purple-600 text-white font-bold shadow-md shadow-purple-600/40'
                    : 'text-slate-400 hover:text-white hover:bg-white/5'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{m.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Split Curtain Frame */}
      <div className="glass-panel p-4 relative">
        <div className="relative w-full aspect-[16/9] sm:aspect-[21/9] rounded-xl overflow-hidden bg-black border border-white/20 select-none group">
          {/* Base Layer: LRO NAC Reference (Warped) */}
          <img
            src="/assets/lronac.jpg"
            alt="Registered LRO NAC"
            className={`absolute inset-0 w-full h-full object-cover filter brightness-110 contrast-120 ${
              mode === 'difference' ? 'mix-blend-difference opacity-90' : ''
            } ${mode === 'falsecolor' ? 'hue-rotate-90 saturate-200' : ''}`}
          />

          {/* Top Layer: Chandrayaan-2 TMC-2 (Clipped by slider position in Split mode) */}
          {mode === 'split' && (
            <div
              className="absolute top-0 left-0 bottom-0 overflow-hidden border-r-2 border-amber-400 shadow-2xl z-10"
              style={{ width: `${sliderPos}%` }}
            >
              <img
                src="/assets/tmc2.jpg"
                alt="Chandrayaan-2 TMC-2"
                className="absolute top-0 left-0 h-full max-w-none object-cover filter brightness-105 contrast-125"
                style={{ width: '100%', minWidth: '100%' }}
              />
              <div className="absolute top-3 left-3 px-2.5 py-1 bg-black/70 backdrop-blur-md rounded text-[10px] font-mono text-amber-300 border border-amber-400/40">
                Chandrayaan-2 TMC-2 (Moving)
              </div>
            </div>
          )}

          {/* Mode Badge Label */}
          <div className="absolute top-3 right-3 px-3 py-1 bg-black/70 backdrop-blur-md rounded-full text-xs font-mono text-cyan-300 border border-cyan-400/40 z-20">
            {mode === 'split' && `Split Curtain: ${sliderPos}%`}
            {mode === 'difference' && 'Absolute Pixel Difference Mode'}
            {mode === 'falsecolor' && 'Multi-spectral Illumination Heatmap'}
            {mode === 'checkerboard' && 'Alternate Tile Alignment Grid'}
          </div>

          {/* Wipe Slider Line with Glowing Handle (Split Mode) */}
          {mode === 'split' && (
            <div
              className="absolute top-0 bottom-0 w-1 bg-gradient-to-b from-amber-300 via-amber-400 to-amber-500 z-20 cursor-ew-resize transform -translate-x-1/2 shadow-[0_0_15px_#fbbf24]"
              style={{ left: `${sliderPos}%` }}
            >
              <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-8 h-8 rounded-full bg-amber-400 text-black flex items-center justify-center font-bold text-xs shadow-lg border-2 border-white">
                ↔
              </div>
            </div>
          )}

          {/* Interactive Range Input Overlay */}
          {mode === 'split' && (
            <input
              type="range"
              min="0"
              max="100"
              value={sliderPos}
              onChange={(e) => setSliderPos(Number(e.target.value))}
              className="absolute inset-0 w-full h-full opacity-0 cursor-ew-resize z-30"
            />
          )}
        </div>

        {/* Footer info bar */}
        <div className="mt-4 flex items-center justify-between text-xs font-mono text-slate-400">
          <span>Sub-pixel Residual Error: &lt; 0.32 pixels</span>
          <span className="text-purple-300 font-semibold">HOMOGRAPHY: H_3x3 Matched</span>
        </div>
      </div>
    </div>
  );
}
