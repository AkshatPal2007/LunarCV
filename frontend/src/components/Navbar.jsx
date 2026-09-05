import React from 'react';
import { 
  Sparkles, 
  Layers, 
  Grid, 
  Sliders, 
  Compass, 
  ShieldCheck, 
  Activity,
  Maximize2
} from 'lucide-react';

export default function Navbar({ activeTab, setActiveTab }) {
  const tabs = [
    { id: 'matcher', label: 'Feature Matcher', icon: Sparkles },
    { id: 'multimodal', label: 'Multi-Modal Flow', icon: Layers },
    { id: 'tiled', label: 'Tiled Matching', icon: Grid },
    { id: 'registration', label: 'Split Visualizer', icon: Sliders },
    { id: 'footprint', label: 'Geo Footprint & Metrics', icon: Compass },
  ];

  return (
    <header className="relative z-20 w-full px-6 py-4 flex flex-wrap items-center justify-between gap-4 border-b border-white/10 bg-[#070814]/80 backdrop-blur-md">
      {/* Brand & Problem Statement */}
      <div className="flex items-center gap-4">
        <div className="relative flex items-center justify-center w-11 h-11 rounded-xl bg-gradient-to-tr from-cyan-400 via-indigo-500 to-purple-500 p-[1px] shadow-lg shadow-cyan-500/25">
          <div className="w-full h-full bg-[#090d16] rounded-[11px] flex items-center justify-center overflow-hidden">
            <img src="/assets/lunarcv_icon.png" alt="LunarCV Logo" className="w-full h-full object-cover rounded-[11px]" />
          </div>
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-orbitron font-bold text-lg md:text-xl tracking-wider text-white bg-clip-text text-transparent bg-gradient-to-r from-white via-slate-200 to-purple-300">
              LunarCV
            </h1>
            <span className="glass-pill text-amber-300 text-xs border-amber-500/30 flex items-center gap-1">
              <ShieldCheck className="w-3.5 h-3.5 text-amber-400" />
              ISRO #26166
            </span>
          </div>
          <p className="text-xs text-slate-400 font-mono flex items-center gap-2">
            <span>Chandrayaan-2 TMC-2 / OHRC</span>
            <span className="text-purple-400">•</span>
            <span>LRO NAC Reference</span>
          </p>
        </div>
      </div>

      {/* Navigation Tabs */}
      <nav className="flex items-center gap-1.5 p-1.5 rounded-2xl bg-slate-900/80 border border-white/10 shadow-inner">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-medium transition-all duration-300 ${
                isActive
                  ? 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-lg shadow-purple-600/30 border border-purple-400/40'
                  : 'text-slate-400 hover:text-white hover:bg-white/5'
              }`}
            >
              <Icon className={`w-4 h-4 ${isActive ? 'text-amber-300 animate-pulse' : 'text-slate-400'}`} />
              <span className="hidden sm:inline font-orbitron text-[11px] tracking-wide">{tab.label}</span>
            </button>
          );
        })}
      </nav>

      {/* Live Orbit Telemetry Badge */}
      <div className="hidden lg:flex items-center gap-3 glass-panel px-3.5 py-2 text-xs font-mono">
        <div className="flex items-center gap-2">
          <span className="relative flex h-2.5 w-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
          </span>
          <span className="text-emerald-400 font-semibold">TMC-2 ORBIT ACTIVE</span>
        </div>
        <div className="h-3 w-[1px] bg-white/20" />
        <div className="flex items-center gap-1 text-slate-300">
          <Activity className="w-3.5 h-3.5 text-purple-400" />
          <span>GSD: 5.0m / 0.5m</span>
        </div>
      </div>
    </header>
  );
}
