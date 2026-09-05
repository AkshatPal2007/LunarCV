import React, { useState, useMemo } from 'react';
import { 
  RotateCcw, 
  Play, 
  CheckCircle2, 
  Info, 
  SlidersHorizontal,
  Target,
  Sparkles,
  Zap,
  Grid
} from 'lucide-react';

// Semicircular Arc Gauge matching user's Snapshot 1
function ArcGauge({ value, percent, color = '#c084fc', text }) {
  // Arc from (12, 48) to (88, 48) radius 38
  // Arc length is pi * 38 = ~119.38
  const arcLength = 119.4;
  const clamped = Math.min(Math.max(percent, 0), 1);
  const strokeDashoffset = arcLength * (1 - clamped);

  return (
    <div style={{ width: '130px', height: '65px', position: 'relative', margin: '0 auto' }}>
      <svg viewBox="0 0 100 55" style={{ width: '100%', height: '100%', overflow: 'visible' }}>
        {/* Background track arc */}
        <path
          d="M 12 48 A 38 38 0 0 1 88 48"
          fill="none"
          stroke="rgba(255, 255, 255, 0.12)"
          strokeWidth="10"
          strokeLinecap="round"
        />
        {/* Active colored arc */}
        <path
          d="M 12 48 A 38 38 0 0 1 88 48"
          fill="none"
          stroke={color}
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={arcLength}
          strokeDashoffset={strokeDashoffset}
          style={{ transition: 'stroke-dashoffset 0.4s ease' }}
        />
      </svg>
      {/* Centered value inside the arc */}
      <div 
        style={{ 
          position: 'absolute', 
          bottom: '2px', 
          left: 0, 
          right: 0, 
          textAlign: 'center', 
          fontFamily: 'JetBrains Mono, monospace', 
          fontSize: '11px', 
          fontWeight: 'bold', 
          color: color 
        }}
      >
        {text}
      </div>
    </div>
  );
}

export default function FeatureMatchCanvas() {
  // Sliders matching Snapshot 1 & 3
  const [clahe, setClahe] = useState(85);
  const [magsac, setMagsac] = useState(42);
  const [tileSize, setTileSize] = useState(65);
  const [subpixel, setSubpixel] = useState(78);
  const [showGrid, setShowGrid] = useState(true);
  const [isProcessing, setIsProcessing] = useState(false);
  const [frameProgress, setFrameProgress] = useState(8);

  // Synchronized metrics dynamically computed from sliders
  const syncedMetrics = useMemo(() => {
    // RMSE decreases as subpixel & magsac are refined
    const rmse = (134.505 * (42 / Math.max(magsac, 10)) * (0.8 + (100 - subpixel) * 0.003)).toFixed(3);
    const rmseArcPct = Math.min(0.8, Math.max(0.1, (100 - Number(rmse) * 0.5) / 100));
    const rmseText = (0.237 * (subpixel / 78)).toFixed(3);

    // Inlier count depends on CLAHE and MAGSAC threshold
    const inliers = Math.floor(155.281 * (clahe / 85) * (magsac / 42));
    const inlierArcPct = Math.min(1.0, (inliers / 200));
    const inlierText = `${(0.27 * (magsac / 42)).toFixed(2)}%`;

    // Spatial Coverage %
    const coverage = (111.209 * (tileSize / 65) * (magsac / 42)).toFixed(3);
    const coverageArcPct = Math.min(1.0, Number(coverage) / 150);
    const coverageText = `${(10.0 * (tileSize / 65)).toFixed(1)}%`;

    // Grid Occupancy
    const occ = (30.28 * (tileSize / 65) * (clahe / 85)).toFixed(2);
    const occFormatted = `00.${occ.replace('.', '.')} %`;
    const occArcPct = Math.min(1.0, (Number(occ) / 100));
    const occText = `${(3.0 * (tileSize / 65)).toFixed(1)}%`;

    return {
      rmse,
      rmseArcPct,
      rmseText,
      inliers,
      inlierArcPct,
      inlierText,
      coverage,
      coverageArcPct,
      coverageText,
      occFormatted,
      occArcPct,
      occText,
    };
  }, [clahe, magsac, tileSize, subpixel]);

  // Master keypoints
  const allMatches = [
    { id: 1, x1: 22, y1: 30, x2: 24, y2: 32, label: 'Tycho Rim', inlierThreshold: 15 },
    { id: 2, x1: 52, y1: 18, x2: 48, y2: 22, label: 'Central Peak', inlierThreshold: 25 },
    { id: 3, x1: 82, y1: 45, x2: 80, y2: 48, label: 'East Ejecta', inlierThreshold: 35 },
    { id: 4, x1: 30, y1: 65, x2: 32, y2: 68, label: 'South Ridge', inlierThreshold: 45 },
    { id: 5, x1: 70, y1: 82, x2: 74, y2: 84, label: 'Secondary Crater', inlierThreshold: 55 },
    { id: 6, x1: 44, y1: 50, x2: 45, y2: 52, label: 'Basin Floor', inlierThreshold: 70 },
    { id: 7, x1: 88, y1: 22, x2: 86, y2: 26, label: 'North Terrace', inlierThreshold: 85 },
  ];

  // Active matches based on MAGSAC++ slider
  const activeMatches = allMatches.filter((m) => magsac >= m.inlierThreshold);

  const handleRunProcessing = () => {
    setIsProcessing(true);
    let p = 0;
    const interval = setInterval(() => {
      p += 15;
      if (p >= 100) {
        clearInterval(interval);
        setIsProcessing(false);
        setFrameProgress(8);
      } else {
        setFrameProgress(p);
      }
    }, 120);
  };

  const handleReset = () => {
    setClahe(85);
    setMagsac(42);
    setTileSize(65);
    setSubpixel(78);
  };

  // Image filter dynamically synchronized to CLAHE slider
  const imageFilterStyle = {
    filter: `contrast(${0.85 + (clahe / 100) * 0.6}) brightness(${0.9 + (clahe / 100) * 0.25})`,
    transition: 'filter 0.2s ease',
  };

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '16px' }}>
      {/* Top Banner Header */}
      <div 
        className="glass-panel"
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '12px',
          padding: '14px 20px',
          marginBottom: '16px'
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h2 className="font-orbitron" style={{ fontSize: '18px', fontWeight: 'bold', color: '#ffffff', letterSpacing: '1px' }}>
              Feature Matching & Constellation Registration
            </h2>
            <span className="glass-pill" style={{ color: '#c084fc', borderColor: 'rgba(192, 132, 252, 0.4)' }}>
              LoFTR + MAGSAC++
            </span>
          </div>
          <p style={{ fontSize: '12px', color: '#94a3b8', fontFamily: 'JetBrains Mono, monospace', marginTop: '3px' }}>
            Chandrayaan-2 TMC-2 (Left) aligned to LRO NAC Reference (Right) • All sliders interactively synchronize the dashboard.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <button
            onClick={() => setShowGrid(!showGrid)}
            className="glass-pill"
            style={{
              cursor: 'pointer',
              color: showGrid ? '#4ade80' : '#94a3b8',
              borderColor: showGrid ? 'rgba(74, 222, 128, 0.4)' : 'rgba(255,255,255,0.15)',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <Grid style={{ width: '13px', height: '13px' }} />
            <span>Tile Grid: {showGrid ? 'ON' : 'OFF'}</span>
          </button>

          <button
            onClick={handleRunProcessing}
            disabled={isProcessing}
            className="font-orbitron"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '8px 18px',
              borderRadius: '10px',
              fontSize: '12px',
              fontWeight: 'bold',
              color: '#000000',
              background: 'linear-gradient(90deg, #fbbf24 0%, #fef08a 100%)',
              border: 'none',
              cursor: 'pointer',
              boxShadow: '0 0 15px rgba(251, 191, 36, 0.4)',
              transition: 'transform 0.15s ease'
            }}
          >
            {isProcessing ? (
              <>
                <Zap style={{ width: '14px', height: '14px', animation: 'spin 1s linear infinite' }} />
                <span>SYNCING ({frameProgress}%)</span>
              </>
            ) : (
              <>
                <Play style={{ width: '14px', height: '14px', fill: '#000000' }} />
                <span>RE-RUN MAGSAC++</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Main Cockpit Layout: 2 Columns */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '16px' }}>
        
        {/* Left Section (Dual Viewport + 4 Gauge Cards) */}
        <div style={{ gridColumn: 'span 2', minWidth: '0' }}>
          {/* Dual Image Frame with SVG Constellation Vectors */}
          <div className="glass-panel" style={{ padding: '16px', marginBottom: '16px', position: 'relative' }}>
            
            {/* Viewport Top Header */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px', fontSize: '12px', fontFamily: 'JetBrains Mono, monospace' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#c084fc', boxShadow: '0 0 8px #c084fc' }} />
                <span style={{ color: '#ffffff', fontWeight: 'bold' }}>Chandrayaan-2 TMC-2</span>
                <span style={{ color: '#94a3b8', fontSize: '10px' }}>(5.0m GSD)</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <span style={{ color: '#ffffff', fontWeight: 'bold' }}>LRO NAC Reference</span>
                <span style={{ color: '#94a3b8', fontSize: '10px' }}>(0.5m GSD)</span>
                <span className="glass-pill" style={{ color: '#fbbf24', fontSize: '10px' }}>
                  LIVE {isProcessing ? frameProgress : 0} / 8%
                </span>
              </div>
            </div>

            {/* Dual Images Viewport */}
            <div 
              style={{ 
                position: 'relative', 
                width: '100%', 
                height: '340px', 
                borderRadius: '12px', 
                overflow: 'hidden', 
                backgroundColor: '#050711',
                border: '1px solid rgba(255, 255, 255, 0.15)',
                display: 'flex',
                gap: '4px',
                padding: '4px'
              }}
            >
              {/* Image 1: TMC-2 */}
              <div style={{ position: 'relative', width: '50%', height: '100%', borderRadius: '8px', overflow: 'hidden', border: '1px solid rgba(192, 132, 252, 0.3)' }}>
                <img
                  src="/assets/tmc2.jpg"
                  alt="Chandrayaan-2 TMC-2"
                  style={{ width: '100%', height: '100%', objectFit: 'cover', ...imageFilterStyle }}
                />
                <div style={{ position: 'absolute', top: '8px', left: '8px', padding: '3px 8px', backgroundColor: 'rgba(0,0,0,0.75)', borderRadius: '4px', fontSize: '10px', fontFamily: 'JetBrains Mono', color: '#c084fc' }}>
                  TMC-2 • CLAHE {clahe}%
                </div>

                {/* Dynamic Tile Grid Overlay */}
                {showGrid && (
                  <div 
                    style={{ 
                      position: 'absolute', 
                      inset: 0, 
                      backgroundImage: 'linear-gradient(to right, rgba(74, 222, 128, 0.25) 1px, transparent 1px), linear-gradient(to bottom, rgba(74, 222, 128, 0.25) 1px, transparent 1px)',
                      backgroundSize: `${tileSize}px ${tileSize}px`,
                      pointerEvents: 'none'
                    }} 
                  />
                )}
              </div>

              {/* Image 2: LRO NAC */}
              <div style={{ position: 'relative', width: '50%', height: '100%', borderRadius: '8px', overflow: 'hidden', border: '1px solid rgba(56, 189, 248, 0.3)' }}>
                <img
                  src="/assets/lronac.jpg"
                  alt="LRO NAC Reference"
                  style={{ width: '100%', height: '100%', objectFit: 'cover', ...imageFilterStyle }}
                />
                <div style={{ position: 'absolute', top: '8px', right: '8px', padding: '3px 8px', backgroundColor: 'rgba(0,0,0,0.75)', borderRadius: '4px', fontSize: '10px', fontFamily: 'JetBrains Mono', color: '#38bdf8' }}>
                  LRO NAC • Tile: {tileSize}px
                </div>

                {/* Dynamic Tile Grid Overlay */}
                {showGrid && (
                  <div 
                    style={{ 
                      position: 'absolute', 
                      inset: 0, 
                      backgroundImage: 'linear-gradient(to right, rgba(56, 189, 248, 0.25) 1px, transparent 1px), linear-gradient(to bottom, rgba(56, 189, 248, 0.25) 1px, transparent 1px)',
                      backgroundSize: `${tileSize}px ${tileSize}px`,
                      pointerEvents: 'none'
                    }} 
                  />
                )}
              </div>

              {/* Synchronized Constellation Lines SVG */}
              <svg style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', pointerEvents: 'none', zIndex: 10 }}>
                <defs>
                  <linearGradient id="purpleCyanGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stopColor="#c084fc" stopOpacity="0.9" />
                    <stop offset="50%" stopColor="#e879f9" stopOpacity="1" />
                    <stop offset="100%" stopColor="#38bdf8" stopOpacity="0.9" />
                  </linearGradient>
                  <filter id="laserGlow" x="-20%" y="-20%" width="140%" height="140%">
                    <feGaussianBlur stdDeviation="3" result="glow" />
                    <feComposite in="SourceGraphic" in2="glow" operator="over" />
                  </filter>
                </defs>

                {activeMatches.map((m) => {
                  const x1 = (m.x1 * 0.5);
                  const y1 = m.y1;
                  const x2 = (50 + m.x2 * 0.5);
                  const y2 = m.y2;

                  return (
                    <g key={m.id}>
                      {/* Laser Connecting Line */}
                      <line
                        x1={`${x1}%`}
                        y1={`${y1}%`}
                        x2={`${x2}%`}
                        y2={`${y2}%`}
                        stroke="url(#purpleCyanGrad)"
                        strokeWidth={subpixel > 50 ? '2.5' : '1.8'}
                        filter="url(#laserGlow)"
                        className="laser-line"
                      />

                      {/* Left Keypoint Node */}
                      <circle cx={`${x1}%`} cy={`${y1}%`} r="5" fill="#c084fc" stroke="#ffffff" strokeWidth="2" className="anim-node" />
                      <circle cx={`${x1}%`} cy={`${y1}%`} r="10" fill="none" stroke="#c084fc" strokeWidth="1" opacity="0.6" />

                      {/* Right Keypoint Node */}
                      <circle cx={`${x2}%`} cy={`${y2}%`} r="5" fill="#38bdf8" stroke="#ffffff" strokeWidth="2" className="anim-node" />
                      <circle cx={`${x2}%`} cy={`${y2}%`} r="10" fill="none" stroke="#38bdf8" strokeWidth="1" opacity="0.6" />
                    </g>
                  );
                })}
              </svg>

              {/* Viewport Bottom HUD Bar (Matching Snapshot 1) */}
              <div 
                style={{ 
                  position: 'absolute', 
                  bottom: '8px', 
                  left: '8px', 
                  right: '8px', 
                  padding: '6px 12px', 
                  backgroundColor: 'rgba(11, 14, 30, 0.85)', 
                  backdropFilter: 'blur(10px)', 
                  borderRadius: '8px', 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'space-between', 
                  border: '1px solid rgba(255, 255, 255, 0.1)', 
                  zIndex: 20, 
                  fontSize: '11px', 
                  fontFamily: 'JetBrains Mono, monospace', 
                  color: '#cbd5e1' 
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <span style={{ color: '#c084fc', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <Sparkles style={{ width: '13px', height: '13px' }} />
                    <span>{activeMatches.length} Active Keypoints</span>
                  </span>
                  <span style={{ color: '#fbbf24', fontWeight: 'bold' }}>
                    MAGSAC++ Inlier Ratio: {syncedMetrics.inlierArcPct > 0.6 ? 'PASSED 99.2%' : 'LOCAL CLUSTERED ⚠️'}
                  </span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ color: '#94a3b8' }}>Sub-pixel Refinement: {subpixel}%</span>
                  <span style={{ color: '#4ade80', fontWeight: 'bold' }}>H_3x3 Computed</span>
                </div>
              </div>
            </div>
          </div>

          {/* 4 Metric Cards with Semi-Circular Arc Gauges (Matching Snapshot 1 Exactly) */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '12px' }}>
            
            {/* Card 1: RMSE */}
            <div className="glass-panel" style={{ padding: '14px', textAlign: 'center', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '11px', color: '#94a3b8', fontFamily: 'JetBrains Mono' }}>
                <span>RMSE</span>
                <Target style={{ width: '13px', height: '13px', color: '#c084fc' }} />
              </div>
              <div className="font-orbitron" style={{ fontSize: '18px', fontWeight: 'bold', color: '#ffffff', margin: '4px 0', textShadow: '0 0 10px rgba(192, 132, 252, 0.6)' }}>
                {syncedMetrics.rmse}
              </div>
              <ArcGauge value={syncedMetrics.rmse} percent={syncedMetrics.rmseArcPct} color="#c084fc" text={syncedMetrics.rmseText} />
              <div style={{ fontSize: '10px', color: '#94a3b8', fontFamily: 'JetBrains Mono', marginTop: '4px' }}>
                Target &lt; 0.50 px
              </div>
            </div>

            {/* Card 2: Inlier Count */}
            <div className="glass-panel" style={{ padding: '14px', textAlign: 'center', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '11px', color: '#94a3b8', fontFamily: 'JetBrains Mono' }}>
                <span>Inlier Count</span>
                <CheckCircle2 style={{ width: '13px', height: '13px', color: '#38bdf8' }} />
              </div>
              <div className="font-orbitron" style={{ fontSize: '18px', fontWeight: 'bold', color: '#ffffff', margin: '4px 0', textShadow: '0 0 10px rgba(56, 189, 248, 0.6)' }}>
                {syncedMetrics.inliers}.281
              </div>
              <ArcGauge value={syncedMetrics.inliers} percent={syncedMetrics.inlierArcPct} color="#c084fc" text={syncedMetrics.inlierText} />
              <div style={{ fontSize: '10px', color: '#94a3b8', fontFamily: 'JetBrains Mono', marginTop: '4px' }}>
                Filtered MAGSAC++
              </div>
            </div>

            {/* Card 3: Spatial Coverage % */}
            <div className="glass-panel" style={{ padding: '14px', textAlign: 'center', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '11px', color: '#94a3b8', fontFamily: 'JetBrains Mono' }}>
                <span>Spatial Coverage %</span>
                <Info style={{ width: '13px', height: '13px', color: '#fbbf24' }} />
              </div>
              <div className="font-orbitron" style={{ fontSize: '18px', fontWeight: 'bold', color: '#ffffff', margin: '4px 0', textShadow: '0 0 10px rgba(251, 191, 36, 0.6)' }}>
                {syncedMetrics.coverage} %
              </div>
              <ArcGauge value={syncedMetrics.coverage} percent={syncedMetrics.coverageArcPct} color="#fbbf24" text={syncedMetrics.coverageText} />
              <div style={{ fontSize: '10px', color: '#94a3b8', fontFamily: 'JetBrains Mono', marginTop: '4px' }}>
                Uniform Distribution
              </div>
            </div>

            {/* Card 4: Grid Occupancy */}
            <div className="glass-panel" style={{ padding: '14px', textAlign: 'center', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '11px', color: '#94a3b8', fontFamily: 'JetBrains Mono' }}>
                <span>Grid Occupancy</span>
                <Grid style={{ width: '13px', height: '13px', color: '#4ade80' }} />
              </div>
              <div className="font-orbitron" style={{ fontSize: '18px', fontWeight: 'bold', color: '#ffffff', margin: '4px 0', textShadow: '0 0 10px rgba(74, 222, 128, 0.6)' }}>
                {syncedMetrics.occFormatted}
              </div>
              <ArcGauge value={syncedMetrics.occFormatted} percent={syncedMetrics.occArcPct} color="#fbbf24" text={syncedMetrics.occText} />
              <div style={{ fontSize: '10px', color: '#94a3b8', fontFamily: 'JetBrains Mono', marginTop: '4px' }}>
                Uniform 4x4 Grid
              </div>
            </div>

          </div>
        </div>

        {/* Right Section: Parameter Adjustment Panel (Matching Snapshot 1 & 3) */}
        <div className="glass-panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', minWidth: '280px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingBottom: '12px', borderBottom: '1px solid rgba(255, 255, 255, 0.1)', marginBottom: '16px' }}>
              <h3 className="font-orbitron" style={{ fontSize: '14px', fontWeight: 'bold', color: '#ffffff', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <SlidersHorizontal style={{ width: '16px', height: '16px', color: '#fbbf24' }} />
                Pipeline Parameters
              </h3>
              <button
                onClick={handleReset}
                style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', padding: '4px' }}
                title="Reset to defaults"
              >
                <RotateCcw style={{ width: '14px', height: '14px' }} />
              </button>
            </div>

            {/* Slider 1: CLAHE Preprocessing */}
            <div style={{ marginBottom: '18px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '12px', fontFamily: 'JetBrains Mono', marginBottom: '6px' }}>
                <span style={{ color: '#e2e8f0' }}>CLAHE Preprocessing</span>
                <span style={{ color: '#fbbf24', fontWeight: 'bold' }}>{clahe}%</span>
              </div>
              <input
                type="range"
                min="10"
                max="100"
                value={clahe}
                onChange={(e) => setClahe(Number(e.target.value))}
              />
              <p style={{ fontSize: '10px', color: '#94a3b8', fontFamily: 'JetBrains Mono', marginTop: '4px' }}>
                Adaptive histogram contrast enhancement for illumination invariance.
              </p>
            </div>

            {/* Slider 2: MAGSAC++ Threshold */}
            <div style={{ marginBottom: '18px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '12px', fontFamily: 'JetBrains Mono', marginBottom: '6px' }}>
                <span style={{ color: '#e2e8f0' }}>MAGSAC++ Threshold</span>
                <span style={{ color: '#fbbf24', fontWeight: 'bold' }}>{magsac} px</span>
              </div>
              <input
                type="range"
                min="10"
                max="100"
                value={magsac}
                onChange={(e) => setMagsac(Number(e.target.value))}
              />
              <p style={{ fontSize: '10px', color: '#94a3b8', fontFamily: 'JetBrains Mono', marginTop: '4px' }}>
                Epipolar outlier rejection threshold for scale & sun angle variance.
              </p>
            </div>

            {/* Slider 3: Tile Size */}
            <div style={{ marginBottom: '18px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '12px', fontFamily: 'JetBrains Mono', marginBottom: '6px' }}>
                <span style={{ color: '#e2e8f0' }}>Tile Size</span>
                <span style={{ color: '#fbbf24', fontWeight: 'bold' }}>{tileSize} px</span>
              </div>
              <input
                type="range"
                min="24"
                max="128"
                value={tileSize}
                onChange={(e) => setTileSize(Number(e.target.value))}
              />
              <p style={{ fontSize: '10px', color: '#94a3b8', fontFamily: 'JetBrains Mono', marginTop: '4px' }}>
                Sub-grid partitioning size for spatially distributed keypoints.
              </p>
            </div>

            {/* Slider 4: Sub-pixel Refinement */}
            <div style={{ marginBottom: '18px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '12px', fontFamily: 'JetBrains Mono', marginBottom: '6px' }}>
                <span style={{ color: '#e2e8f0' }}>Sub-pixel Refinement</span>
                <span style={{ color: '#fbbf24', fontWeight: 'bold' }}>{subpixel}%</span>
              </div>
              <input
                type="range"
                min="10"
                max="100"
                value={subpixel}
                onChange={(e) => setSubpixel(Number(e.target.value))}
              />
              <p style={{ fontSize: '10px', color: '#94a3b8', fontFamily: 'JetBrains Mono', marginTop: '4px' }}>
                Lucas-Kanade intensity peak interpolation for sub-pixel accuracy.
              </p>
            </div>
          </div>

          {/* Footer apply buttons */}
          <div style={{ paddingTop: '16px', borderTop: '1px solid rgba(255, 255, 255, 0.1)' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '11px', fontFamily: 'JetBrains Mono', color: '#94a3b8', marginBottom: '10px' }}>
              <span>Status:</span>
              <span style={{ color: '#4ade80', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '4px' }}>
                <CheckCircle2 style={{ width: '13px', height: '13px' }} /> Synchronized & Ready
              </span>
            </div>
            <button
              onClick={handleRunProcessing}
              className="font-orbitron"
              style={{
                width: '100%',
                padding: '10px',
                borderRadius: '10px',
                fontSize: '12px',
                fontWeight: 'bold',
                color: '#ffffff',
                background: 'linear-gradient(90deg, #9333ea 0%, #6366f1 100%)',
                border: '1px solid rgba(192, 132, 252, 0.5)',
                cursor: 'pointer',
                boxShadow: '0 4px 15px rgba(147, 51, 234, 0.3)'
              }}
            >
              APPLY PARAMETERS & RE-RUN
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}
