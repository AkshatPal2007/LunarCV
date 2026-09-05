import React, { useState, useEffect, useRef, useMemo } from 'react';

export default function App() {
  // Navigation: 'educate' is placed FIRST before 'console'
  const [activeTab, setActiveTab] = useState('educate');

  // Controls state
  const [claheOn, setClaheOn] = useState(true);
  const [magsacThreshold, setMagsacThreshold] = useState(2.4);
  const [tileSize, setTileSize] = useState(256);
  const [subpixelOn, setSubpixelOn] = useState(true);
  const [uniformityOn, setUniformityOn] = useState(false);
  const [currentTile, setCurrentTile] = useState(8);
  const totalTiles = 24;

  // Video-like playback sequence state
  const [isPlaying, setIsPlaying] = useState(true);
  const [sequencePhase, setSequencePhase] = useState('green-scan');

  // Multi-spectral scanning positions: Green on Image 1, Blue on Image 2, then Yellow sync
  const [scanPosA, setScanPosA] = useState(0);
  const [scanPosB, setScanPosB] = useState(0);
  const [scanPosGreen, setScanPosGreen] = useState(0);
  const [scanPosBlue, setScanPosBlue] = useState(0);
  const [scanPosYellow, setScanPosYellow] = useState(0);

  // Dense green feature keypoints extracted on Image 1 (TMC-2)
  const greenFeaturePoints = useMemo(() => [
    { id: 'gp1', x: 65, y: 48, r: 4.5 },
    { id: 'gp2', x: 115, y: 38, r: 3.5 },
    { id: 'gp3', x: 175, y: 48, r: 4.0 },
    { id: 'gp4', x: 235, y: 36, r: 3.5 },
    { id: 'gp5', x: 295, y: 44, r: 4.2 },
    { id: 'gp6', x: 350, y: 38, r: 4.8 },
    { id: 'gp7', x: 415, y: 52, r: 3.5 },
    { id: 'gp8', x: 55, y: 92, r: 4.0 },
    { id: 'gp9', x: 110, y: 82, r: 4.5 },
    { id: 'gp10', x: 145, y: 112, r: 3.8 },
    { id: 'gp11', x: 195, y: 88, r: 4.2 },
    { id: 'gp12', x: 250, y: 98, r: 4.6 },
    { id: 'gp13', x: 305, y: 82, r: 3.6 },
    { id: 'gp14', x: 375, y: 94, r: 4.5 },
    { id: 'gp15', x: 440, y: 112, r: 3.8 },
    { id: 'gp16', x: 48, y: 152, r: 4.2 },
    { id: 'gp17', x: 95, y: 138, r: 3.6 },
    { id: 'gp18', x: 155, y: 148, r: 5.0 },
    { id: 'gp19', x: 215, y: 136, r: 4.0 },
    { id: 'gp20', x: 275, y: 158, r: 3.8 },
    { id: 'gp21', x: 330, y: 144, r: 4.2 },
    { id: 'gp22', x: 395, y: 162, r: 4.5 },
    { id: 'gp23', x: 450, y: 178, r: 3.6 },
    { id: 'gp24', x: 68, y: 208, r: 4.5 },
    { id: 'gp25', x: 125, y: 192, r: 4.0 },
    { id: 'gp26', x: 185, y: 218, r: 3.8 },
    { id: 'gp27', x: 245, y: 202, r: 5.0 },
    { id: 'gp28', x: 305, y: 222, r: 4.2 },
    { id: 'gp29', x: 365, y: 208, r: 4.6 },
    { id: 'gp30', x: 425, y: 228, r: 3.6 },
    { id: 'gp31', x: 82, y: 268, r: 4.2 },
    { id: 'gp32', x: 138, y: 252, r: 3.8 },
    { id: 'gp33', x: 198, y: 278, r: 4.5 },
    { id: 'gp34', x: 258, y: 262, r: 4.0 },
    { id: 'gp35', x: 318, y: 288, r: 3.6 },
    { id: 'gp36', x: 378, y: 272, r: 4.6 },
    { id: 'gp37', x: 438, y: 292, r: 4.0 },
  ], []);

  // Continuous line shoot progression: 0.0 to 1.0
  const [shootProgress, setShootProgress] = useState(0);

  // Dynamic Animated Circle Gauges
  const [gaugeProgress, setGaugeProgress] = useState(0);

  // In-viewer display mode: 'dual' or 'split'
  const [viewerMode, setViewerMode] = useState('dual');
  const [splitPos, setSplitPos] = useState(50);
  const [splitMode, setSplitMode] = useState('wipe');

  // Active roadmap step
  const [activeStep, setActiveStep] = useState(3);

  // Multi-Modal Tab State
  const [mmActiveSensor, setMmActiveSensor] = useState('tmc');
  const [mmActiveTool, setMmActiveTool] = useState('sensors');
  const [sunAngleDeg, setSunAngleDeg] = useState(48);

  // Tactical Telemetry & View Screens Switcher (Reference Dashboard inspired)
  const [activeScreenId, setActiveScreenId] = useState('sarabhai');
  const viewScreensList = [
    {
      id: 'pragyan',
      agency: 'ISRO · CH-3 PRAGYAN',
      missionHeadline: 'ISRO CHANDRAYAAN-3',
      missionTag: 'ISRO CH-3',
      featureShort: 'LUNAR SOUTH POLE',
      feedStatus: 'CHANDRAYAAN-3 FEED ACTIVE | IMAGE SELECTED',
      title: 'Shiv Shakti Point & 4m South Pole Crater',
      coords: '69.37°S 32.35°E',
      resolution: '0.12 m/px · NavCam NavPath',
      sourceImg: '/assets/isro_pragyan_crater.jpg',
      refImg: '/assets/ch3_vikram_shivshakti.jpg',
      refTag: 'VIKRAM LANDER SHIV SHAKTI',
      desc: 'Historic August 27 encounter of 4-meter lunar crater safely traversed by Pragyan Rover near Moon South Pole.',
      telemetry: { sunAngle: '84.2°', elevation: 'Surface', fov: '22.0 m', temp: '-142°C' },
    },
    {
      id: 'vikram',
      agency: 'ISRO · CH-3 VIKRAM',
      missionHeadline: 'ISRO CHANDRAYAAN-3',
      missionTag: 'ISRO CH-3',
      featureShort: 'SHIV SHAKTI POINT',
      feedStatus: 'CHANDRAYAAN-3 FEED ACTIVE | IMAGE SELECTED',
      title: 'Vikram Lander Touchdown at Shiv Shakti',
      coords: '69.37°S 32.35°E',
      resolution: '0.28 m/px · Lander Imager',
      sourceImg: '/assets/ch3_vikram_shivshakti.jpg',
      refImg: '/assets/isro_pragyan_crater.jpg',
      refTag: 'PRAGYAN ROVER TRAVERSAL',
      desc: 'Historic landing coordinates of Chandrayaan-3 Vikram Lander at Shiv Shakti Point near the Moon south pole.',
      telemetry: { sunAngle: '82.5°', elevation: 'Surface', fov: '15.0 m', temp: '-138°C' },
    },
    {
      id: 'sarabhai',
      agency: 'ISRO · CH-2 TMC-2',
      missionHeadline: 'ISRO CHANDRAYAAN-2',
      missionTag: 'ISRO CH-2',
      featureShort: 'SARABHAI CRATER',
      feedStatus: 'CHANDRAYAAN-2 FEED ACTIVE | IMAGE SELECTED',
      title: 'Sarabhai Crater (Mare Serenitatis)',
      coords: '24.75°N 21.00°E',
      resolution: '5.0 m/px · 1.7 km depth',
      sourceImg: '/assets/ch2_sarabhai_crater.jpg',
      refImg: '/assets/copernicus_crater.jpg',
      refTag: 'NASA SVS COPERNICUS',
      desc: 'Named after Dr. Vikram Sarabhai; pristine circular impact basin with 1.7km depth captured by Chandrayaan-2 TMC-2.',
      telemetry: { sunAngle: '53.4°', elevation: '1.7 km', fov: '18.4 km', temp: '-128°C' },
    },
    {
      id: 'ohrc',
      agency: 'ISRO · CH-2 OHRC',
      missionHeadline: 'ISRO CHANDRAYAAN-2',
      missionTag: 'ISRO OHRC',
      featureShort: 'SUB-METER BOULDERS',
      feedStatus: 'CHANDRAYAAN-2 OHRC FEED ACTIVE | IMAGE SELECTED',
      title: 'South Pole High-Res Boulder Field',
      coords: '89.20°S 00.45°W',
      resolution: '0.25 m/px · Sub-Meter Optical',
      sourceImg: '/assets/ch2_ohrc_super_res.jpg',
      refImg: '/assets/shackleton_south_pole.jpg',
      refTag: 'NASA LRO SHACKLETON RIM',
      desc: 'Orbiter High Resolution Camera (OHRC) capturing sharpest boulder field and micro-craters on the Moon.',
      telemetry: { sunAngle: '86.5°', elevation: '100 km', fov: '12.0 km', temp: '-185°C' },
    },
    {
      id: 'earth_moon',
      agency: 'ISRO · CH-2 LI4',
      missionHeadline: 'ISRO CHANDRAYAAN-2',
      missionTag: 'ISRO LI4',
      featureShort: 'EARTH-MOON LOOKBACK',
      feedStatus: 'CHANDRAYAAN-2 TRANSLUNAR ACTIVE | IMAGE SELECTED',
      title: 'Earth-Moon Orbital Alignment',
      coords: 'GEO → TRANSLUNAR',
      resolution: 'Deep Space Optical Telemetry',
      sourceImg: '/assets/ch2_earth_moon.jpg',
      refImg: '/assets/dazzling_nebula.jpg',
      refTag: 'JWST NGC-346 DEEP FIELD',
      desc: 'Iconic look-back photograph showing Earth and Moon in celestial orbit captured during lunar transfer trajectory.',
      telemetry: { sunAngle: '38.0°', elevation: '149.45M km', fov: 'Macro', temp: '-268°C' },
    },
    {
      id: 'tycho',
      agency: 'NASA · LRO NAC',
      missionHeadline: 'NASA LRO NAC',
      missionTag: 'NASA LRO',
      featureShort: 'COPERNICUS RIM',
      feedStatus: 'NASA LRO NAC FEED ACTIVE | IMAGE SELECTED',
      title: 'Copernicus Crater & Terraced Rim',
      coords: '09.62°N 20.08°W',
      resolution: '0.50 m/px · 2.4 km Central Peak',
      sourceImg: '/assets/copernicus_crater.jpg',
      refImg: '/assets/lronac.jpg',
      refTag: 'LRO NAC REF',
      desc: 'Rebounded 2,400m central peak inside 85km Copernicus Crater with rayed ejecta blanket stretching across lunar nearside.',
      telemetry: { sunAngle: '22.0°', elevation: '50 km', fov: '85.0 km', temp: '-95°C' },
    },
    {
      id: 'shackleton',
      agency: 'NASA / ISRO JOINT',
      missionHeadline: 'NASA / ISRO JOINT',
      missionTag: 'NASA/ISRO',
      featureShort: 'SHACKLETON RIM',
      feedStatus: 'LUNAR RECONNAISSANCE ACTIVE | IMAGE SELECTED',
      title: 'Shackleton Crater Permanently Shadowed Rim',
      coords: '89.90°S 00.00°E',
      resolution: '1.20 m/px · Lunar South Pole Ice',
      sourceImg: '/assets/shackleton_south_pole.jpg',
      refImg: '/assets/pole_crater.jpg',
      refTag: 'LRO LOLA ALTIMETRY',
      desc: 'The eternal peak of light and deep crater interior shielding volatile water-ice deposits at lunar south pole.',
      telemetry: { sunAngle: '88.1°', elevation: '50 km', fov: '21.0 km', temp: '-230°C' },
    },
  ];

  // Active Selected View Screen
  const selectedScreen = useMemo(
    () => viewScreensList.find((s) => s.id === activeScreenId) || viewScreensList[0],
    [activeScreenId]
  );

  // Starfield canvas ref
  const canvasRef = useRef(null);

  // Twinkling stars effect
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let animationFrame;

    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    resize();
    window.addEventListener('resize', resize);

    const stars = Array.from({ length: 190 }, () => ({
      x: Math.random() * window.innerWidth,
      y: Math.random() * window.innerHeight,
      r: Math.random() * 1.5 + 0.3,
      tw: Math.random() * Math.PI * 2,
      speed: Math.random() * 0.015 + 0.005,
      gold: Math.random() > 0.65,
    }));

    const drawStars = (t) => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      for (const s of stars) {
        const alpha = 0.35 + 0.65 * Math.abs(Math.sin(s.tw + t * s.speed));
        ctx.beginPath();
        ctx.fillStyle = s.gold
          ? `rgba(251, 191, 36, ${alpha})`
          : `rgba(240, 235, 255, ${alpha})`;
        ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
        ctx.fill();
      }
      animationFrame = requestAnimationFrame(drawStars);
    };

    animationFrame = requestAnimationFrame(drawStars);

    return () => {
      window.removeEventListener('resize', resize);
      cancelAnimationFrame(animationFrame);
    };
  }, []);

  // Initial entrance gauge loading
  useEffect(() => {
    let frameId;
    const startTime = performance.now();
    const duration = 1000;
    const easeOutCubic = (x) => 1 - Math.pow(1 - x, 3);

    const animateGauges = (now) => {
      const elapsed = now - startTime;
      const t = Math.min(1, elapsed / duration);
      setGaugeProgress(easeOutCubic(t));
      if (t < 1) {
        frameId = requestAnimationFrame(animateGauges);
      }
    };

    frameId = requestAnimationFrame(animateGauges);
    return () => cancelAnimationFrame(frameId);
  }, []);

  // Automated video scan loop for Console:
  // 1. Green Scan on Image 1 (TMC-2 Optical Feature Detection)
  // 2. Blue Scan on Image 2 (NASA LRO-NAC Holographic Grid Targeting)
  // 3. Yellow Scan across both images (Dual-Sensor Correlation Synchronization)
  // 4. Final Mapping (Golden constellation homography vector shooting)
  // 5. Registration Locked hold
  useEffect(() => {
    if (!isPlaying || viewerMode !== 'dual') return;

    let frameId;
    let start = performance.now();
    let lastUpdate = 0;

    const greenTime = 2200;
    const blueTime = 2200;
    const yellowTime = 2200;
    const shootTime = 2600;
    const holdTime = 2400;
    const totalCycle = greenTime + blueTime + yellowTime + shootTime + holdTime;

    const tick = (now) => {
      frameId = requestAnimationFrame(tick);
      if (now - lastUpdate < 50) return;
      lastUpdate = now;

      const elapsed = (now - start) % totalCycle;

      // Continuously advance active pipeline stage through all 6 stages
      const stepIdx = Math.min(6, Math.max(1, Math.floor((elapsed / totalCycle) * 6) + 1));
      setActiveStep(stepIdx);

      if (elapsed < greenTime) {
        setSequencePhase('green-scan');
        const pGreen = elapsed / greenTime;
        setScanPosGreen(pGreen * 100);
        setScanPosBlue(0);
        setScanPosYellow(0);
        setShootProgress(0);
        setScanPosA(pGreen * 100);
        setScanPosB(0);
      } else if (elapsed < greenTime + blueTime) {
        setSequencePhase('blue-scan');
        setScanPosGreen(100);
        const pBlue = (elapsed - greenTime) / blueTime;
        setScanPosBlue(pBlue * 100);
        setScanPosYellow(0);
        setShootProgress(0);
        setScanPosA(100);
        setScanPosB(pBlue * 100);
      } else if (elapsed < greenTime + blueTime + yellowTime) {
        setSequencePhase('yellow-scan');
        setScanPosGreen(100);
        setScanPosBlue(100);
        const pYellow = (elapsed - (greenTime + blueTime)) / yellowTime;
        setScanPosYellow(pYellow * 100);
        setShootProgress(0);
        setScanPosA(pYellow * 100);
        setScanPosB(pYellow * 100);
      } else if (elapsed < greenTime + blueTime + yellowTime + shootTime) {
        setSequencePhase('mapping');
        setScanPosGreen(100);
        setScanPosBlue(100);
        setScanPosYellow(100);
        const pShoot = (elapsed - (greenTime + blueTime + yellowTime)) / shootTime;
        setShootProgress(pShoot);
        setScanPosA(100);
        setScanPosB(100);
      } else {
        setSequencePhase('locked');
        setScanPosGreen(100);
        setScanPosBlue(100);
        setScanPosYellow(100);
        setShootProgress(1);
        setScanPosA(100);
        setScanPosB(100);
      }
    };

    frameId = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frameId);
  }, [isPlaying, viewerMode]);

  // Continuously advance roadmap stage smoothly even if laser scan is paused
  useEffect(() => {
    if (isPlaying) return;
    const interval = setInterval(() => {
      setActiveStep((prev) => (prev % 6) + 1);
    }, 2400);
    return () => clearInterval(interval);
  }, [isPlaying]);

  // Dynamically coupled computer vision metrics derived directly from slider physics and active tile
  const targetMetrics = useMemo(() => {
    // 1. RMSE (Root Mean Square Error in pixels)
    // Physical Photogrammetry Coupling:
    // Sub-pixel 2D Taylor interpolation drops residual quantization from ~1.15px down to ~0.16px
    // MAGSAC++ threshold directly tightens or loosens geometric outlier margin
    // CLAHE contrast enhancement improves corner gradient response
    const subpixelBase = subpixelOn ? 0.15 : 0.95;
    const magsacError = (magsacThreshold / 5.0) * (subpixelOn ? 0.24 : 0.80);
    const claheBonus = claheOn ? -0.04 : 0.08;
    const tileRefineBonus = ((currentTile - 1) / (totalTiles - 1 || 1)) * -0.05;
    const targetRmseVal = Math.max(0.12, +(subpixelBase + magsacError + claheBonus + tileRefineBonus).toFixed(2));
    // Accuracy %: mapped inversely from RMSE (0.15px -> 98%, 0.35px -> 91%, 1.2px -> 68%, 2.0px -> 45%)
    const targetRmsePct = Math.min(99, Math.max(18, Math.round(100 - (targetRmseVal * 28))));

    // 2. Inlier Count
    // Smaller quad-tree tiles force independent feature extraction across each local patch:
    // 64px = 64 tiles -> ~270 local points
    // 128px = 16 tiles -> ~140 points
    // 256px = 4 tiles -> ~75 points
    // 512px = 1 tile -> ~35 points
    // Higher MAGSAC threshold accepts more inlier pairs (+15 pts per px)
    // CLAHE adds +38 inliers in shadow basins
    // Uniformity ANMS culls redundant clusters (-18 pts) to maintain uniform spacing
    const tileFeatureBase = Math.round(Math.pow(512 / tileSize, 1.15) * 24);
    const magsacInliers = Math.round(magsacThreshold * 15);
    const claheInlierCount = claheOn ? 38 : 8;
    const uniformityPenalty = uniformityOn ? -18 : 0;
    const tileAccumulation = Math.round((currentTile / totalTiles) * 26);
    const targetInliers = Math.max(30, tileFeatureBase + magsacInliers + claheInlierCount + uniformityPenalty + tileAccumulation);
    const targetInlierPct = Math.min(100, Math.max(15, Math.round((targetInliers / 360) * 100)));

    // 3. Spatial Coverage %
    // Uniformity ANMS filter guarantees balanced distribution across entire lunar quad
    // Smaller tiles enforce distributed coverage across all crater zones
    const uniformityCoverage = uniformityOn ? 88 : 42;
    const tileCoverage = Math.round(((512 - tileSize) / 448) * 16);
    const claheCoverage = claheOn ? 6 : 0;
    const targetCoverage = Math.min(99, Math.max(25, uniformityCoverage + tileCoverage + claheCoverage));

    // 4. Grid Occupancy %
    // Populated cells in the 4x4 spatial hashing quad grid
    const targetGrid = Math.min(98, Math.max(30, Math.round(targetCoverage * 0.88 + (uniformityOn ? 10 : 0) + (claheOn ? 4 : -2))));

    return {
      rmseVal: targetRmseVal,
      rmsePct: targetRmsePct,
      inliers: targetInliers,
      inlierPct: targetInlierPct,
      coverage: targetCoverage,
      grid: targetGrid,
    };
  }, [claheOn, magsacThreshold, tileSize, subpixelOn, uniformityOn, currentTile, totalTiles]);

  // Live synchronous metrics directly reflecting slider physics with instant response
  const currentMetrics = useMemo(() => {
    const p = gaugeProgress;
    return {
      rmsePct: Math.round(targetMetrics.rmsePct * p),
      rmseVal: targetMetrics.rmseVal.toFixed(2),
      inlierPct: Math.round(targetMetrics.inlierPct * p),
      inlierCount: Math.round(targetMetrics.inliers * p),
      coveragePct: Math.round(targetMetrics.coverage * p),
      gridPct: Math.round(targetMetrics.grid * p),
    };
  }, [gaugeProgress, targetMetrics]);

  // Dynamic Constellation Nodes & Vectors based on tile size, threshold, and filters
  const { constellationNodes, constellationLines } = useMemo(() => {
    // Base core keypoints
    const baseNodes = [
      { id: 't1', x: 125, y: 95, label: 'Tycho North', isSource: true },
      { id: 't2', x: 350, y: 35, label: 'Top Basin', isSource: true },
      { id: 't3', x: 180, y: 140, label: 'Central Peak', isSource: true },
      { id: 't4', x: 250, y: 185, label: 'South Ejecta', isSource: true },
      { id: 't5', x: 90, y: 290, label: 'Deep Crater', isSource: true },
      { id: 'l1', x: 510, y: 70, label: 'Boundary Inlier', isSource: false },
      { id: 'l2', x: 720, y: 65, label: 'North Terrace', isSource: false },
      { id: 'l3', x: 950, y: 195, label: 'East Wall', isSource: false },
      { id: 'l4', x: 890, y: 300, label: 'Secondary Rim', isSource: false },
    ];

    // Additional quad-tree nodes unlocked when tile size is <= 256px
    if (tileSize <= 256) {
      baseNodes.push(
        { id: 't6', x: 290, y: 120, label: 'Basin Floor', isSource: true },
        { id: 't7', x: 60, y: 180, label: 'West Escarpment', isSource: true },
        { id: 'l5', x: 610, y: 160, label: 'Central Terrace', isSource: false },
        { id: 'l6', x: 790, y: 220, label: 'Ridge Peak', isSource: false },
      );
    }

    // Dense sub-tile nodes when tile size is <= 160px
    if (tileSize <= 160) {
      baseNodes.push(
        { id: 't9', x: 380, y: 150, label: 'Quad Ejecta C', isSource: true },
        { id: 't10', x: 160, y: 240, label: 'Quad Floor D', isSource: true },
        { id: 'l8', x: 840, y: 110, label: 'Terrace Step B', isSource: false },
        { id: 'l9', x: 580, y: 260, label: 'Inner Plain B', isSource: false },
      );
    }

    // CLAHE contrast nodes unlocked in dark shadowed craters
    if (claheOn) {
      baseNodes.push(
        { id: 'tc1', x: 310, y: 285, label: 'Shadow Basin A', isSource: true },
        { id: 'lc1', x: 740, y: 310, label: 'Shadow Terrace A', isSource: false },
      );
    }

    // Spatial uniformity nodes distributed across all 4 quadrants
    if (uniformityOn) {
      baseNodes.push(
        { id: 't8', x: 420, y: 260, label: 'Uniform Quadrant 4', isSource: true },
        { id: 'l7', x: 680, y: 290, label: 'Uniform Ground Inlier', isSource: false },
      );
    }

    const lines = [
      { from: 't2', to: 'l1', order: 0 },
      { from: 't1', to: 'l2', order: 1 },
      { from: 't3', to: 'l2', order: 2 },
      { from: 't3', to: 'l3', order: 3 },
      { from: 't4', to: 'l3', order: 4 },
      { from: 't5', to: 'l4', order: 5 },
      { from: 't1', to: 't2', order: 1 },
      { from: 't1', to: 't3', order: 2 },
      { from: 't3', to: 't4', order: 3 },
      { from: 't4', to: 't5', order: 4 },
      { from: 'l1', to: 'l2', order: 3 },
      { from: 'l2', to: 'l3', order: 4 },
      { from: 'l2', to: 'l4', order: 5 },
      { from: 'l3', to: 'l4', order: 5 },
    ];

    if (tileSize <= 256) {
      lines.push(
        { from: 't6', to: 'l5', order: 2 },
        { from: 't7', to: 'l6', order: 3 },
      );
    }

    if (tileSize <= 160) {
      lines.push(
        { from: 't9', to: 'l8', order: 1 },
        { from: 't10', to: 'l9', order: 4 },
      );
    }

    if (claheOn) {
      lines.push(
        { from: 'tc1', to: 'lc1', order: 5 },
      );
    }

    if (uniformityOn) {
      lines.push(
        { from: 't8', to: 'l7', order: 4 },
      );
    }

    // High MAGSAC threshold admits looser cross-vector candidates
    if (magsacThreshold >= 3.0) {
      lines.push(
        { from: 't2', to: 'l2', order: 3 },
        { from: 't4', to: 'l4', order: 4 },
      );
    }

    return { constellationNodes: baseNodes, constellationLines: lines };
  }, [tileSize, uniformityOn, magsacThreshold, claheOn]);

  const getNode = (id) => constellationNodes.find((n) => n.id === id);

  return (
    <div>
      {/* Ultra-Vivid JWST NGC 346 Cosmic Backdrop with Slow Continuous Zoom In / Zoom Out */}
      <div className="backdrop">
        <img
          src="/assets/dazzling_nebula.jpg"
          alt="JWST NGC 346 Nebula"
          className="dazzling-bg"
        />
        <div className="backdrop-vignette"></div>
        <canvas id="stars" ref={canvasRef}></canvas>
      </div>

      <div className="stage">
        {/* Topbar: Unified, Elegant, Perfectly Balanced Single-Row Header */}
        <div
          className="topbar"
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '6px 14px',
            gap: '8px',
            flexWrap: 'nowrap',
            boxSizing: 'border-box',
            width: '100%',
            overflow: 'hidden',
          }}
        >
          {/* Brand Left */}
          <div
            className="brand"
            style={{
              display: 'flex',
              alignItems: 'center',
              flexShrink: 0,
              gap: '10px',
              cursor: 'pointer',
              userSelect: 'none',
            }}
            onClick={() => setActiveTab('educate')}
            title="LunarCV · Chandrayaan-2 Optical Registration Engine"
          >
            <div
              style={{
                width: '36px',
                height: '36px',
                borderRadius: '50%',
                padding: '1.5px',
                background: 'linear-gradient(135deg, #38bdf8, #818cf8, #c084fc)',
                boxShadow: '0 0 16px rgba(56, 189, 248, 0.5)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                overflow: 'hidden',
                flexShrink: 0,
              }}
            >
              <img
                src="/assets/lunarcv_icon.png"
                alt="LunarCV Aperture Emblem"
                style={{
                  width: '100%',
                  height: '100%',
                  borderRadius: '50%',
                  objectFit: 'cover',
                }}
              />
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span className="name" style={{ fontSize: '18px', fontWeight: 900, letterSpacing: '-0.02em', color: '#ffffff', display: 'flex', alignItems: 'center' }}>
                LUNAR<span style={{ color: '#38bdf8', textShadow: '0 0 10px rgba(56, 189, 248, 0.6)' }}>CV</span>
              </span>
              <span style={{ fontSize: '9.5px', fontFamily: 'var(--mono)', background: 'rgba(56, 189, 248, 0.18)', color: '#38bdf8', padding: '1.5px 6px', borderRadius: '4px', border: '1px solid rgba(56, 189, 248, 0.5)', fontWeight: 800, letterSpacing: '0.04em' }}>
                CH-2
              </span>
            </div>
          </div>

          {/* Navigation Center */}
          <div
            className="nav-pills"
            style={{
              background: 'rgba(0, 0, 0, 0.65)',
              border: '1.5px solid rgba(255, 255, 255, 0.18)',
              padding: '3px',
              flexShrink: 1,
              gap: '3px',
            }}
          >
            <button
              className={`nav-btn ${activeTab === 'educate' ? 'active' : ''}`}
              onClick={() => setActiveTab('educate')}
              style={{ padding: '5px 10px', fontSize: '11.5px', whiteSpace: 'nowrap' }}
            >
              🌙 Overview
            </button>
            <button
              className={`nav-btn ${activeTab === 'console' ? 'active' : ''}`}
              onClick={() => setActiveTab('console')}
              style={{ padding: '5px 10px', fontSize: '11.5px', whiteSpace: 'nowrap' }}
            >
              Console
            </button>
            <button
              className={`nav-btn ${activeTab === 'multimodal' ? 'active' : ''}`}
              onClick={() => setActiveTab('multimodal')}
              style={{ padding: '5px 10px', fontSize: '11.5px', whiteSpace: 'nowrap' }}
            >
              Multi-Modal Flow
            </button>
            <button
              className={`nav-btn ${activeTab === 'alignment' ? 'active' : ''}`}
              onClick={() => setActiveTab('alignment')}
              style={{ padding: '5px 10px', fontSize: '11.5px', whiteSpace: 'nowrap' }}
            >
              Alignment & Footprint
            </button>
          </div>

          {/* Official Mission, Ministry of Education, & SIH Logos Right */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              flexShrink: 0,
            }}
          >
            {/* ISRO Official Emblem */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
                background: 'rgba(255, 255, 255, 0.06)',
                border: '1px solid rgba(255, 255, 255, 0.15)',
                padding: '3px 6px',
                borderRadius: '6px',
              }}
              title="Indian Space Research Organisation"
            >
              <img
                src="/assets/isro_logo.svg"
                alt="ISRO Logo"
                style={{ width: '20px', height: '20px', objectFit: 'contain', filter: 'drop-shadow(0 0 6px rgba(255,153,51,0.6))' }}
              />
              <span style={{ fontSize: '11px', fontFamily: 'var(--mono)', fontWeight: 800, color: '#ff9933' }}>ISRO</span>
            </div>

            {/* Chandrayaan Mission Emblem */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
                background: 'rgba(138, 107, 255, 0.12)',
                border: '1px solid rgba(138, 107, 255, 0.35)',
                padding: '3px 6px',
                borderRadius: '6px',
                boxShadow: '0 0 8px rgba(138, 107, 255, 0.25)',
              }}
              title="Chandrayaan Lunar Exploration Programme"
            >
              <img
                src="/assets/chandrayaan_logo.svg"
                alt="Chandrayaan Logo"
                style={{ width: '20px', height: '20px', objectFit: 'contain', filter: 'drop-shadow(0 0 6px rgba(168,85,247,0.7))' }}
              />
              <span style={{ fontSize: '11px', fontFamily: 'var(--mono)', fontWeight: 800, color: '#d8b4fe', letterSpacing: '0.02em' }}>
                Chandrayaan
              </span>
            </div>

            {/* Merged Single Badge: Ministry of Education, SIH 2024, and #26166 */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
                background: '#ffffff',
                border: '1.5px solid #fbbf24',
                borderRadius: '7px',
                padding: '2px 7px',
                boxShadow: '0 0 10px rgba(251, 191, 36, 0.4)',
                flexShrink: 0,
              }}
              title="Ministry of Education & Smart India Hackathon 2024 · Problem Statement #26166"
            >
              <img
                src="/assets/sih_logo_tight.png"
                alt="Ministry of Education & Smart India Hackathon 2024"
                style={{
                  height: '24px',
                  width: 'auto',
                  objectFit: 'contain',
                  display: 'block',
                }}
              />
              <div style={{ width: '1.5px', height: '16px', background: '#cbd5e1' }} />
              <span style={{ fontSize: '11px', fontFamily: 'var(--mono)', fontWeight: 900, color: '#b45309', letterSpacing: '0.02em', whiteSpace: 'nowrap' }}>
                #26166
              </span>
            </div>
          </div>
        </div>

        {/* TAB 1: LUNAR CV (BORDERLESS, SEAMLESS, IMMERSIVE WITH REAL SATELLITE CROPS) */}
        {activeTab === 'educate' && (
          <div style={{ marginTop: '36px', maxWidth: '860px', margin: '36px auto 0' }}>
            {/* Header Title Banner */}
            <div
              style={{
                textAlign: 'center',
                marginBottom: '44px',
                background: 'rgba(8, 5, 22, 0.45)',
                backdropFilter: 'blur(16px)',
                WebkitBackdropFilter: 'blur(16px)',
                border: '1px solid rgba(255, 255, 255, 0.16)',
                borderRadius: '20px',
                padding: '32px 24px',
                boxShadow: '0 8px 32px rgba(0, 0, 0, 0.45)',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
              }}
            >
              <div
                style={{
                  marginBottom: '20px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <img
                  src="/assets/lunarcv_brand_logo.png"
                  alt="LunarCV Official Mission Logo"
                  style={{
                    height: '115px',
                    width: 'auto',
                    borderRadius: '16px',
                    boxShadow: '0 0 28px rgba(56, 189, 248, 0.35), 0 8px 32px rgba(0, 0, 0, 0.7)',
                    border: '1px solid rgba(56, 189, 248, 0.25)',
                  }}
                />
              </div>

              <div style={{ fontFamily: 'var(--mono)', fontSize: '13px', color: 'var(--amber)', marginBottom: '12px', letterSpacing: '0.08em', fontWeight: 700 }}>
                LUNARCV · THE IDEA, EXPLAINED SIMPLY
              </div>
              <h1 style={{ fontSize: '34px', fontWeight: 800, margin: '0 auto 16px', color: '#ffffff', lineHeight: 1.25, letterSpacing: '-0.01em', textShadow: '0 2px 20px rgba(0,0,0,0.95)' }}>
                Why lining up two photos of the Moon is harder than it sounds.
              </h1>
              <p style={{ color: '#f0ecfc', fontSize: '16px', lineHeight: 1.75, maxWidth: '660px', margin: '0 auto', fontWeight: 500, textShadow: '0 2px 12px rgba(0,0,0,0.9)' }}>
                A plain-language walk through the problem LunarCV solves, the science behind it, and where it fits into India's Moon missions.
              </p>
            </div>

            {/* Section 1: The Idea (With Real High-Res Lunar Satellite Images) */}
            <div style={{ borderTop: '1px solid var(--panel-edge)', paddingTop: '36px', marginBottom: '44px' }}>
              {/* Frosted Text Box Scrim for Section 1 */}
              <div
                style={{
                  background: 'rgba(8, 5, 22, 0.38)',
                  backdropFilter: 'blur(12px)',
                  WebkitBackdropFilter: 'blur(12px)',
                  border: '1px solid rgba(255, 255, 255, 0.16)',
                  borderRadius: '16px',
                  padding: '22px 26px',
                  marginBottom: '26px',
                  boxShadow: '0 8px 28px rgba(0, 0, 0, 0.35)',
                }}
              >
                <div style={{ fontFamily: 'var(--mono)', fontSize: '12px', color: 'var(--violet)', marginBottom: '8px', fontWeight: 700, letterSpacing: '0.06em' }}>THE IDEA</div>
                <h2 style={{ fontSize: '26px', fontWeight: 700, margin: '0 0 14px', color: '#ffffff', textShadow: '0 2px 14px rgba(0,0,0,0.9)' }}>Two photos, same place, different cameras.</h2>
                <p style={{ fontSize: '16px', lineHeight: 1.8, color: '#f0ecfc', margin: '0 0 14px', fontWeight: 500, textShadow: '0 2px 10px rgba(0,0,0,0.9)' }}>
                  Imagine two people photograph the same street one at noon, one at sunset, one standing close, one far away. The street is identical, but the two photos look nothing alike. <strong style={{ color: '#ffffff', fontWeight: 800 }}>Image registration</strong> is the process of lining those two photos up so the same landmark sits in the same spot in both.
                </p>
                <p style={{ fontSize: '16px', lineHeight: 1.8, color: '#f0ecfc', margin: '0', fontWeight: 500, textShadow: '0 2px 10px rgba(0,0,0,0.9)' }}>
                  LunarCV does this for the Moon: it lines up photos of the same lunar terrain taken by <strong style={{ color: '#ffffff', fontWeight: 800 }}>Chandrayaan-2</strong>'s cameras with photos of the same terrain taken by NASA's <strong style={{ color: '#ffffff', fontWeight: 800 }}>LRO</strong> spacecraft so scientists can trust that a crater in one image is the same crater in the other.
                </p>
              </div>

              {/* Realistic High-Fidelity Satellite Correspondence Display */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr auto 1fr',
                  alignItems: 'center',
                  gap: '20px',
                  background: 'rgba(8, 5, 20, 0.75)',
                  borderRadius: '18px',
                  padding: '24px',
                  border: '1.5px solid rgba(255, 255, 255, 0.22)',
                  backdropFilter: 'blur(16px)',
                  boxShadow: '0 12px 40px rgba(0, 0, 0, 0.65)',
                }}
              >
                {/* Source: Chandrayaan-2 TMC-2 */}
                <div style={{ position: 'relative', borderRadius: '14px', overflow: 'hidden', border: '2px solid var(--violet)', boxShadow: '0 0 24px rgba(138, 107, 255, 0.45)' }}>
                  <img src="/assets/ch2_crater_source.jpg" alt="Chandrayaan-2 TMC-2 Crater" style={{ width: '100%', height: '240px', objectFit: 'cover', display: 'block' }} />
                  <div style={{ position: 'absolute', top: '12px', left: '12px', background: 'rgba(0,0,0,0.85)', padding: '5px 10px', borderRadius: '6px', fontSize: '12px', fontFamily: 'var(--mono)', color: '#c4b5fd', fontWeight: 800, letterSpacing: '0.04em', border: '1px solid var(--violet)' }}>
                    CHANDRAYAAN-2 TMC-2
                  </div>
                  <div style={{ position: 'absolute', top: '48%', left: '46%', transform: 'translate(-50%, -50%)', width: '36px', height: '36px', borderRadius: '50%', border: '2.5px solid var(--amber)', boxShadow: '0 0 16px var(--amber)' }}></div>
                  <div style={{ position: 'absolute', top: '48%', left: '46%', transform: 'translate(-50%, -50%)', width: '8px', height: '8px', borderRadius: '50%', background: '#ffffff', boxShadow: '0 0 8px #ffffff' }}></div>
                </div>

                {/* Laser Correlation Vector */}
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px', padding: '0 6px' }}>
                  <div style={{ fontFamily: 'var(--mono)', fontSize: '11px', color: 'var(--amber)', fontWeight: 800, textAlign: 'center', letterSpacing: '0.08em' }}>
                    HOMOGRAPHY
                  </div>
                  <div style={{ width: '50px', height: '3px', background: 'linear-gradient(90deg, #8a6bff, #fbbf24)', boxShadow: '0 0 14px #fbbf24', borderRadius: '2px' }}></div>
                  <div style={{ fontSize: '22px', color: '#fbbf24', filter: 'drop-shadow(0 0 8px #fbbf24)' }}>➔</div>
                </div>

                {/* Reference: NASA LRO NAC */}
                <div style={{ position: 'relative', borderRadius: '14px', overflow: 'hidden', border: '2px solid var(--amber)', boxShadow: '0 0 24px rgba(251, 191, 36, 0.45)' }}>
                  <img src="/assets/lro_crater_reference.jpg" alt="NASA LRO NAC Reference" style={{ width: '100%', height: '240px', objectFit: 'cover', display: 'block' }} />
                  <div style={{ position: 'absolute', top: '12px', right: '12px', background: 'rgba(0,0,0,0.85)', padding: '5px 10px', borderRadius: '6px', fontSize: '12px', fontFamily: 'var(--mono)', color: 'var(--amber)', fontWeight: 800, letterSpacing: '0.04em', border: '1px solid var(--amber)' }}>
                    LRO NAC REFERENCE
                  </div>
                  <div style={{ position: 'absolute', top: '47%', left: '46%', transform: 'translate(-50%, -50%)', width: '36px', height: '36px', borderRadius: '50%', border: '2.5px solid #34d399', boxShadow: '0 0 16px #34d399' }}></div>
                  <div style={{ position: 'absolute', top: '47%', left: '46%', transform: 'translate(-50%, -50%)', width: '8px', height: '8px', borderRadius: '50%', background: '#ffffff', boxShadow: '0 0 8px #ffffff' }}></div>
                </div>
              </div>
              <div style={{ fontFamily: 'var(--mono)', fontSize: '12px', color: '#d4cee9', textAlign: 'center', marginTop: '14px', fontWeight: 600 }}>
                Matching the exact crater geometry between Chandrayaan-2 and NASA LRO ground truth
              </div>
            </div>

            {/* Section 2: Why It's Hard (Physical Constraints) */}
            <div style={{ borderTop: '1px solid var(--panel-edge)', paddingTop: '36px', marginBottom: '44px' }}>
              <div
                style={{
                  background: 'rgba(8, 5, 22, 0.38)',
                  backdropFilter: 'blur(12px)',
                  WebkitBackdropFilter: 'blur(12px)',
                  border: '1px solid rgba(255, 255, 255, 0.16)',
                  borderRadius: '16px',
                  padding: '22px 26px',
                  marginBottom: '22px',
                  boxShadow: '0 8px 28px rgba(0, 0, 0, 0.35)',
                }}
              >
                <div style={{ fontFamily: 'var(--mono)', fontSize: '12px', color: 'var(--violet)', marginBottom: '8px', fontWeight: 700, letterSpacing: '0.06em' }}>WHY IT'S HARD</div>
                <h2 style={{ fontSize: '26px', fontWeight: 700, margin: '0 0 14px', color: '#ffffff', textShadow: '0 2px 14px rgba(0,0,0,0.9)' }}>The Moon looks different depending on how you catch it.</h2>
                <p style={{ fontSize: '16px', lineHeight: 1.8, color: '#f0ecfc', margin: 0, fontWeight: 500, textShadow: '0 2px 10px rgba(0,0,0,0.9)' }}>
                  Two physical variables make lunar alignment dramatically trickier than ordinary photos: extreme shifts in incident solar shadows and substantial sensor ground-resolution disparities.
                </p>
              </div>

              {/* Real Solar Angle Comparison Images */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', margin: '22px 0' }}>
                <div style={{ border: '1.5px solid rgba(251, 191, 36, 0.4)', borderRadius: '16px', background: 'rgba(8, 5, 20, 0.75)', padding: '16px', textAlign: 'center', boxShadow: '0 8px 30px rgba(0,0,0,0.5)' }}>
                  <div style={{ position: 'relative', height: '170px', borderRadius: '10px', overflow: 'hidden', marginBottom: '14px', border: '1px solid var(--panel-edge)' }}>
                    <img src="/assets/sun_angle_low.jpg" alt="Low Sun Angle" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                    <div style={{ position: 'absolute', top: '8px', left: '8px', background: 'rgba(0,0,0,0.85)', padding: '3px 8px', borderRadius: '6px', fontSize: '11px', fontFamily: 'var(--mono)', color: 'var(--amber)', fontWeight: 700 }}>
                      SUN ELEVATION: 22° (OBLIQUE)
                    </div>
                  </div>
                  <div style={{ fontSize: '16px', fontWeight: 700, color: '#ffffff', marginBottom: '6px' }}>☀️ Sun Angle & Deep Shadows</div>
                  <div style={{ fontSize: '13.5px', color: '#d4cee9', lineHeight: 1.6, fontWeight: 500 }}>
                    The same crater throws elongated shadows on opposite sides as solar elevation changes often reversing apparent brightness and crater walls.
                  </div>
                </div>

                <div style={{ border: '1.5px solid rgba(138, 107, 255, 0.4)', borderRadius: '16px', background: 'rgba(8, 5, 20, 0.75)', padding: '16px', textAlign: 'center', boxShadow: '0 8px 30px rgba(0,0,0,0.5)' }}>
                  <div style={{ position: 'relative', height: '170px', borderRadius: '10px', overflow: 'hidden', marginBottom: '14px', border: '1px solid var(--panel-edge)' }}>
                    <img src="/assets/sun_angle_high.jpg" alt="High Sun Angle" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                    <div style={{ position: 'absolute', top: '8px', right: '8px', background: 'rgba(0,0,0,0.85)', padding: '3px 8px', borderRadius: '6px', fontSize: '11px', fontFamily: 'var(--mono)', color: 'var(--violet)', fontWeight: 700 }}>
                      SUN ELEVATION: 78° (HIGH NOON)
                    </div>
                  </div>
                  <div style={{ fontSize: '16px', fontWeight: 700, color: '#ffffff', marginBottom: '6px' }}>🔍 Scale & Spatial Resolution</div>
                  <div style={{ fontSize: '13.5px', color: '#d4cee9', lineHeight: 1.6, fontWeight: 500 }}>
                    Sensors photograph at different orbital altitudes: TMC-2 is 5m GSD, while LRO NAC is 0.5m GSD (a 10x spatial resolution difference).
                  </div>
                </div>
              </div>

              <div
                style={{
                  background: 'rgba(8, 5, 22, 0.38)',
                  backdropFilter: 'blur(12px)',
                  WebkitBackdropFilter: 'blur(12px)',
                  border: '1px solid rgba(255, 255, 255, 0.16)',
                  borderRadius: '14px',
                  padding: '16px 22px',
                  boxShadow: '0 8px 24px rgba(0, 0, 0, 0.3)',
                }}
              >
                <p style={{ fontSize: '15.5px', lineHeight: 1.75, color: '#f0ecfc', margin: 0, fontWeight: 500, textShadow: '0 2px 10px rgba(0,0,0,0.9)' }}>
                  A robust lunar registration pipeline must recognize <strong style={{ color: '#ffffff', fontWeight: 800 }}>"that is the exact same crater"</strong> even when the lighting direction has flipped and the size has scaled tenfold.
                </p>
              </div>
            </div>

            {/* Section 3: How The Matching Works */}
            <div style={{ borderTop: '1px solid var(--panel-edge)', paddingTop: '36px', marginBottom: '44px' }}>
              {/* Frosted Text Box Scrim for Section 3 */}
              <div
                style={{
                  background: 'rgba(8, 5, 22, 0.38)',
                  backdropFilter: 'blur(12px)',
                  WebkitBackdropFilter: 'blur(12px)',
                  border: '1px solid rgba(255, 255, 255, 0.16)',
                  borderRadius: '16px',
                  padding: '22px 26px',
                  boxShadow: '0 8px 28px rgba(0, 0, 0, 0.35)',
                }}
              >
                <div style={{ fontFamily: 'var(--mono)', fontSize: '12px', color: 'var(--violet)', marginBottom: '8px', fontWeight: 700, letterSpacing: '0.06em' }}>HOW THE MATCHING WORKS</div>
                <h2 style={{ fontSize: '26px', fontWeight: 700, margin: '0 0 14px', color: '#ffffff', textShadow: '0 2px 14px rgba(0,0,0,0.9)' }}>Finding landmarks, like connecting the dots.</h2>
                <p style={{ fontSize: '16px', lineHeight: 1.8, color: '#f0ecfc', margin: '0 0 14px', fontWeight: 500, textShadow: '0 2px 10px rgba(0,0,0,0.9)' }}>
                  The pipeline identifies distinctive features in both images crater rims, boulders, and central ridge peaks creating confident correspondency vectors.
                </p>
                <p style={{ fontSize: '16px', lineHeight: 1.8, color: '#f0ecfc', margin: '0 0 14px', fontWeight: 500, textShadow: '0 2px 10px rgba(0,0,0,0.9)' }}>
                  Once sufficient match points exist across the image, the software computes an optimal 3x3 projective homography transformation matrix to warp, rotate, and align the two images with sub-pixel residual error.
                </p>
                <p style={{ fontSize: '16px', lineHeight: 1.8, color: '#f0ecfc', margin: '0', fontWeight: 500, textShadow: '0 2px 10px rgba(0,0,0,0.9)' }}>
                  <strong style={{ color: '#ffffff', fontWeight: 800 }}>Tiled Re-matching:</strong> Early feature matching tends to cluster on high-contrast regions. LunarCV segments the image into a 4x4 uniform grid to enforce spatially balanced matches across the entire lunar surface.
                </p>
              </div>
            </div>

            {/* Section 4: India on the Moon (Chandrayaan Timeline) */}
            <div style={{ borderTop: '1px solid var(--panel-edge)', paddingTop: '36px', paddingBottom: '20px' }}>
              <div style={{ fontFamily: 'var(--mono)', fontSize: '12px', color: 'var(--violet)', marginBottom: '8px', fontWeight: 700, letterSpacing: '0.06em' }}>INDIA ON THE MOON</div>
              <h2 style={{ fontSize: '26px', fontWeight: 700, margin: '0 0 18px', color: '#ffffff', textShadow: '0 2px 14px rgba(0,0,0,0.9)' }}>Where this fits ISRO's Chandrayaan missions.</h2>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '22px' }}>
                <div style={{ display: 'grid', gridTemplateColumns: '70px 20px 1fr', gap: '16px', background: 'rgba(8, 5, 20, 0.75)', padding: '16px', borderRadius: '12px', border: '1px solid var(--panel-edge)' }}>
                  <div style={{ fontFamily: 'var(--mono)', fontSize: '15px', color: 'var(--amber)', fontWeight: 800 }}>2008</div>
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                    <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: 'var(--violet)', boxShadow: '0 0 10px rgba(138,107,255,0.9)', flex: 'none', marginTop: '4px' }}></div>
                    <div style={{ width: '2px', flex: 1, background: 'var(--panel-edge)', marginTop: '4px' }}></div>
                  </div>
                  <div>
                    <div style={{ fontWeight: 800, color: '#ffffff', fontSize: '16px', marginBottom: '6px' }}>Chandrayaan-1</div>
                    <div style={{ color: '#d4cee9', fontSize: '14px', lineHeight: 1.6, fontWeight: 500 }}>
                      India's first Moon mission. Its instruments confirmed the presence of water molecules on the lunar surface a landmark global discovery.
                    </div>
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '70px 20px 1fr', gap: '16px', background: 'rgba(8, 5, 20, 0.75)', padding: '16px', borderRadius: '12px', border: '1px solid var(--panel-edge)' }}>
                  <div style={{ fontFamily: 'var(--mono)', fontSize: '15px', color: 'var(--amber)', fontWeight: 800 }}>2019</div>
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                    <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: 'var(--violet)', boxShadow: '0 0 10px rgba(138,107,255,0.9)', flex: 'none', marginTop: '4px' }}></div>
                    <div style={{ width: '2px', flex: 1, background: 'var(--panel-edge)', marginTop: '4px' }}></div>
                  </div>
                  <div>
                    <div style={{ fontWeight: 800, color: '#ffffff', fontSize: '16px', marginBottom: '6px' }}>Chandrayaan-2</div>
                    <div style={{ color: '#d4cee9', fontSize: '14px', lineHeight: 1.6, fontWeight: 500 }}>
                      Orbiter reached lunar orbit successfully and remains fully active today, continuously capturing the high-resolution TMC-2 and OHRC datasets LunarCV registers.
                    </div>
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '70px 20px 1fr', gap: '16px', background: 'rgba(8, 5, 20, 0.75)', padding: '16px', borderRadius: '12px', border: '1px solid var(--panel-edge)' }}>
                  <div style={{ fontFamily: 'var(--mono)', fontSize: '15px', color: 'var(--amber)', fontWeight: 800 }}>2023</div>
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                    <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: 'var(--amber)', boxShadow: '0 0 12px rgba(251,191,36,1)', flex: 'none', marginTop: '4px' }}></div>
                  </div>
                  <div>
                    <div style={{ fontWeight: 800, color: '#ffffff', fontSize: '16px', marginBottom: '6px' }}>Chandrayaan-3</div>
                    <div style={{ color: '#d4cee9', fontSize: '14px', lineHeight: 1.6, fontWeight: 500 }}>
                      Vikram lander successfully touched down near the Moon's south pole making India the first country to land there, and fourth to achieve a soft landing.
                    </div>
                  </div>
                </div>
              </div>

              <div
                style={{
                  border: '1.5px solid rgba(138, 107, 255, 0.45)',
                  borderRadius: '16px',
                  padding: '20px 24px',
                  marginTop: '28px',
                  background: 'linear-gradient(135deg, rgba(138,107,255,0.18), rgba(233,183,104,0.1))',
                  boxShadow: '0 8px 30px rgba(0,0,0,0.5)',
                }}
              >
                <p style={{ color: '#ffffff', fontSize: '15px', margin: 0, lineHeight: 1.7, fontWeight: 600 }}>
                  Better image registration means better maps of the lunar surface the same maps used to pinpoint safe, scientifically rich landing sites for missions like Chandrayaan-3, and future planetary exploration.
                </p>
              </div>
            </div>

            {/* Section 5: Tactical Lunar Imagery & Space Agency View Screens (Retro CRT LCARS Terminal) */}
            {(() => {
              const currentScreenIndex = Math.max(0, viewScreensList.findIndex((s) => s.id === activeScreenId));
              const totalScreens = viewScreensList.length;
              const prevScreenIndex = (currentScreenIndex - 1 + totalScreens) % totalScreens;
              const nextScreenIndex = (currentScreenIndex + 1) % totalScreens;
              const prevScreen = viewScreensList[prevScreenIndex];
              const nextScreen = viewScreensList[nextScreenIndex];

              return (
                <div
                  style={{
                    borderTop: '1px solid var(--panel-edge)',
                    paddingTop: '36px',
                    marginBottom: '40px',
                  }}
                >
                  {/* Outer Retro LCARS Sci-Fi Terminal Unit */}
                  <div
                    style={{
                      background: 'rgba(11, 7, 24, 0.88)',
                      backdropFilter: 'blur(16px)',
                      WebkitBackdropFilter: 'blur(16px)',
                      border: '1px solid rgba(56, 189, 248, 0.3)',
                      borderRadius: '24px',
                      overflow: 'hidden',
                      boxShadow: '0 12px 45px rgba(0, 0, 0, 0.6), 0 0 35px rgba(6, 182, 212, 0.15)',
                    }}
                  >
                    {/* Top LCARS Header Accent Band */}
                    <div
                      style={{
                        height: '18px',
                        background: 'linear-gradient(90deg, #4ade80 0%, #2dd4bf 45%, #38bdf8 100%)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '0 20px',
                      }}
                    >
                      <span style={{ fontSize: '9px', fontFamily: 'var(--mono)', fontWeight: 900, color: '#041d14', letterSpacing: '0.12em' }}>
                        LCARS TERMINAL // ARCHIVE FEED 88-LUNAR
                      </span>
                      <span style={{ fontSize: '9px', fontFamily: 'var(--mono)', fontWeight: 800, color: '#041d14' }}>
                        SYS.ON · 122,333 PW
                      </span>
                    </div>

                    {/* Main Console Grid: Left Vertical Rail + CRT Monitor + Right View Screens Sidebar */}
                    <div className="retro-lcars-grid">
                      {/* Left LCARS Status Rail */}
                      <div
                        style={{
                          borderRight: '1px solid rgba(56, 189, 248, 0.2)',
                          padding: '16px 4px',
                          display: 'flex',
                          flexDirection: 'column',
                          alignItems: 'center',
                          gap: '10px',
                          background: 'rgba(5, 3, 14, 0.65)',
                        }}
                      >
                        <div style={{ width: '18px', height: '36px', borderRadius: '9px', background: '#2dd4bf', boxShadow: '0 0 8px #2dd4bf' }} />
                        <div style={{ width: '18px', height: '18px', borderRadius: '4px', background: '#c084fc' }} />
                        <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#fbbf24', boxShadow: '0 0 6px #fbbf24' }} />
                        <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#f87171' }} />
                        <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#38bdf8' }} />
                        <div style={{ flex: 1 }} />
                        <span style={{ fontSize: '8px', fontFamily: 'var(--mono)', color: '#94a3b8', writingMode: 'vertical-rl', letterSpacing: '0.1em' }}>
                          01·17·6.5
                        </span>
                      </div>

                      {/* Center CRT Monitor Screen */}
                      <div style={{ padding: '20px 22px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                        {/* CRT Screen Bezel */}
                        <div
                          style={{
                            background: '#020108',
                            borderRadius: '34px',
                            border: '4px solid #22d3ee',
                            boxShadow: '0 0 0 3px #050212, 0 0 0 7px #0891b2, 0 0 28px rgba(6, 182, 212, 0.85), 0 0 60px rgba(168, 85, 247, 0.4), inset 0 0 26px rgba(6, 182, 212, 0.25)',
                            padding: '14px 18px',
                            position: 'relative',
                            overflow: 'hidden',
                            display: 'flex',
                            flexDirection: 'column',
                            justifyContent: 'space-between',
                            minHeight: '380px',
                          }}
                        >
                          {/* CRT Scanline Horizontal Texture */}
                          <div
                            style={{
                              position: 'absolute',
                              inset: 0,
                              pointerEvents: 'none',
                              zIndex: 18,
                              backgroundImage: 'repeating-linear-gradient(0deg, rgba(0, 0, 0, 0.2) 0px, rgba(0, 0, 0, 0.2) 1px, transparent 1px, transparent 3px)',
                            }}
                          />

                          {/* Monitor Top Status Line */}
                          <div
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'space-between',
                              fontSize: '11px',
                              fontFamily: 'var(--mono)',
                              fontWeight: 700,
                              zIndex: 12,
                              padding: '2px 4px 6px',
                              borderBottom: '1px solid rgba(34, 211, 238, 0.2)',
                            }}
                          >
                            <span style={{ color: '#a5b4fc', letterSpacing: '0.04em' }}>
                              4T 5432-9 122,333 PW
                            </span>
                            <span style={{ color: '#38bdf8', letterSpacing: '0.06em' }}>
                              . LUNAR IMAGING ARCHIVE (ISRO FEED)
                            </span>
                          </div>

                          {/* Center 3D Coverflow Image Carousel */}
                          <div
                            style={{
                              position: 'relative',
                              height: '270px',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              margin: '8px 0',
                              overflow: 'hidden',
                            }}
                          >
                            {/* Left Navigation Arrow Button */}
                            <button
                              onClick={() => setActiveScreenId(prevScreen.id)}
                              title="Previous Lunar Frame"
                              style={{
                                position: 'absolute',
                                left: '8px',
                                zIndex: 25,
                                width: '32px',
                                height: '40px',
                                background: 'rgba(3, 2, 14, 0.92)',
                                border: '2px solid #38bdf8',
                                color: '#38bdf8',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                fontSize: '18px',
                                fontWeight: 900,
                                cursor: 'pointer',
                                borderRadius: '4px',
                                boxShadow: '0 0 12px rgba(56, 189, 248, 0.45)',
                                transition: 'all 0.2s ease',
                              }}
                              onMouseEnter={(e) => {
                                e.currentTarget.style.background = '#38bdf8';
                                e.currentTarget.style.color = '#000000';
                              }}
                              onMouseLeave={(e) => {
                                e.currentTarget.style.background = 'rgba(3, 2, 14, 0.92)';
                                e.currentTarget.style.color = '#38bdf8';
                              }}
                            >
                              &#x276E;
                            </button>

                            {/* Left Card (Previous) */}
                            <div
                              onClick={() => setActiveScreenId(prevScreen.id)}
                              title={`Switch to ${prevScreen.title}`}
                              style={{
                                position: 'absolute',
                                left: '16px',
                                width: '160px',
                                height: '215px',
                                borderRadius: '8px',
                                overflow: 'hidden',
                                border: '1.5px solid rgba(56, 189, 248, 0.4)',
                                opacity: 0.52,
                                transform: 'perspective(700px) rotateY(16deg) scale(0.86)',
                                cursor: 'pointer',
                                zIndex: 6,
                                transition: 'all 0.3s ease',
                                background: '#000000',
                              }}
                            >
                              <img
                                src={prevScreen.sourceImg}
                                alt={prevScreen.title}
                                style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                              />
                            </div>

                            {/* Center Active Focused Card (Matches Reference HUD Pixel-Perfect) */}
                            <div
                              style={{
                                position: 'relative',
                                width: '320px',
                                height: '255px',
                                borderRadius: '10px',
                                border: '2.5px solid #38bdf8',
                                boxShadow: '0 0 26px rgba(56, 189, 248, 0.55), inset 0 0 16px rgba(56, 189, 248, 0.25)',
                                zIndex: 12,
                                overflow: 'hidden',
                                background: '#000000',
                                transition: 'all 0.3s ease',
                              }}
                            >
                              <img
                                src={selectedScreen.sourceImg}
                                alt={selectedScreen.title}
                                style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
                              />

                              {/* Top-Left Active HUD Box */}
                              <div
                                style={{
                                  position: 'absolute',
                                  top: '8px',
                                  left: '8px',
                                  background: 'rgba(3, 4, 15, 0.88)',
                                  border: '1.5px solid rgba(56, 189, 248, 0.75)',
                                  padding: '4px 8px',
                                  borderRadius: '4px',
                                  display: 'flex',
                                  flexDirection: 'column',
                                  gap: '2px',
                                  zIndex: 15,
                                  boxShadow: '0 2px 8px rgba(0,0,0,0.7)',
                                }}
                              >
                                <span style={{ fontSize: '10px', fontFamily: 'var(--mono)', color: '#93c5fd', fontWeight: 700, letterSpacing: '0.04em' }}>
                                  IMAGE {currentScreenIndex + 1} / {totalScreens}
                                </span>
                                <span style={{ fontSize: '11px', fontFamily: 'var(--mono)', color: '#ffffff', fontWeight: 800 }}>
                                  {selectedScreen.missionHeadline}
                                </span>
                              </div>

                              {/* Top-Right Mission Tag */}
                              <div
                                style={{
                                  position: 'absolute',
                                  top: '8px',
                                  right: '8px',
                                  background: 'rgba(3, 4, 15, 0.88)',
                                  border: '1.5px solid rgba(56, 189, 248, 0.75)',
                                  padding: '3px 8px',
                                  borderRadius: '4px',
                                  color: '#38bdf8',
                                  fontFamily: 'var(--mono)',
                                  fontWeight: 800,
                                  fontSize: '10.5px',
                                  zIndex: 15,
                                  boxShadow: '0 2px 8px rgba(0,0,0,0.7)',
                                }}
                              >
                                [{selectedScreen.missionTag}]
                              </div>

                              {/* Bottom-Right Feature & Coordinates Box */}
                              <div
                                style={{
                                  position: 'absolute',
                                  bottom: '8px',
                                  right: '8px',
                                  background: 'rgba(3, 4, 15, 0.88)',
                                  border: '1.5px solid rgba(56, 189, 248, 0.75)',
                                  padding: '4px 8px',
                                  borderRadius: '4px',
                                  textAlign: 'right',
                                  display: 'flex',
                                  flexDirection: 'column',
                                  gap: '2px',
                                  zIndex: 15,
                                  boxShadow: '0 2px 8px rgba(0,0,0,0.7)',
                                }}
                              >
                                <span style={{ fontSize: '11px', fontFamily: 'var(--mono)', color: '#ffffff', fontWeight: 800 }}>
                                  {selectedScreen.featureShort}
                                </span>
                                <span style={{ fontSize: '10px', fontFamily: 'var(--mono)', color: '#38bdf8', fontWeight: 700 }}>
                                  {selectedScreen.coords}
                                </span>
                              </div>
                            </div>

                            {/* Right Card (Next) */}
                            <div
                              onClick={() => setActiveScreenId(nextScreen.id)}
                              title={`Switch to ${nextScreen.title}`}
                              style={{
                                position: 'absolute',
                                right: '16px',
                                width: '160px',
                                height: '215px',
                                borderRadius: '8px',
                                overflow: 'hidden',
                                border: '1.5px solid rgba(56, 189, 248, 0.4)',
                                opacity: 0.52,
                                transform: 'perspective(700px) rotateY(-16deg) scale(0.86)',
                                cursor: 'pointer',
                                zIndex: 6,
                                transition: 'all 0.3s ease',
                                background: '#000000',
                              }}
                            >
                              <img
                                src={nextScreen.sourceImg}
                                alt={nextScreen.title}
                                style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                              />
                            </div>

                            {/* Right Navigation Arrow Button */}
                            <button
                              onClick={() => setActiveScreenId(nextScreen.id)}
                              title="Next Lunar Frame"
                              style={{
                                position: 'absolute',
                                right: '8px',
                                zIndex: 25,
                                width: '32px',
                                height: '40px',
                                background: 'rgba(3, 2, 14, 0.92)',
                                border: '2px solid #38bdf8',
                                color: '#38bdf8',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                fontSize: '18px',
                                fontWeight: 900,
                                cursor: 'pointer',
                                borderRadius: '4px',
                                boxShadow: '0 0 12px rgba(56, 189, 248, 0.45)',
                                transition: 'all 0.2s ease',
                              }}
                              onMouseEnter={(e) => {
                                e.currentTarget.style.background = '#38bdf8';
                                e.currentTarget.style.color = '#000000';
                              }}
                              onMouseLeave={(e) => {
                                e.currentTarget.style.background = 'rgba(3, 2, 14, 0.92)';
                                e.currentTarget.style.color = '#38bdf8';
                              }}
                            >
                              &#x276F;
                            </button>
                          </div>

                          {/* Monitor Bottom Status & Pagination */}
                          <div style={{ zIndex: 12 }}>
                            {/* Pagination Dots and Terminal Coordinates */}
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '4px 4px 6px' }}>
                              <div style={{ width: '100px' }} />
                              <div style={{ display: 'flex', alignItems: 'center', gap: '7px' }}>
                                {viewScreensList.map((screen, idx) => {
                                  const isCur = idx === currentScreenIndex;
                                  return (
                                    <span
                                      key={screen.id}
                                      onClick={() => setActiveScreenId(screen.id)}
                                      style={{
                                        width: isCur ? '8px' : '5px',
                                        height: isCur ? '8px' : '5px',
                                        borderRadius: '50%',
                                        background: isCur ? '#38bdf8' : 'rgba(255, 255, 255, 0.3)',
                                        boxShadow: isCur ? '0 0 8px #38bdf8' : 'none',
                                        cursor: 'pointer',
                                        transition: 'all 0.2s ease',
                                        display: 'inline-block',
                                      }}
                                    />
                                  );
                                })}
                              </div>
                              <span style={{ fontSize: '9.5px', fontFamily: 'var(--mono)', color: '#94a3b8', letterSpacing: '0.04em' }}>
                                SEATTLE, NV. 03.63.43
                              </span>
                            </div>

                            {/* Active Image Selected Banner */}
                            <div
                              style={{
                                textAlign: 'center',
                                padding: '3px 0',
                                borderTop: '1px solid rgba(56, 189, 248, 0.2)',
                                color: '#38bdf8',
                                fontFamily: 'var(--mono)',
                                fontSize: '10.5px',
                                fontWeight: 800,
                                letterSpacing: '0.08em',
                              }}
                            >
                              {selectedScreen.feedStatus || `${selectedScreen.missionHeadline} FEED ACTIVE | IMAGE SELECTED`}
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* Right View Screens Retro Sidebar */}
                      <div
                        style={{
                          borderLeft: '1px solid rgba(56, 189, 248, 0.25)',
                          background: 'rgba(18, 12, 34, 0.92)',
                          padding: '20px 18px',
                          display: 'flex',
                          flexDirection: 'column',
                          justifyContent: 'space-between',
                        }}
                      >
                        <div>
                          {/* Heading: VIEW SCREENS [LUNAR] */}
                          <div
                            style={{
                              fontSize: '24px',
                              fontWeight: 900,
                              lineHeight: 1.15,
                              color: '#cbd5e1',
                              letterSpacing: '0.04em',
                              marginBottom: '12px',
                              textTransform: 'uppercase',
                              fontFamily: 'var(--display)',
                            }}
                          >
                            VIEW<br />
                            SCREENS<br />
                            <span style={{ color: '#64748b' }}>[LUNAR]</span>
                          </div>

                          {/* Subtitle */}
                          <p
                            style={{
                              margin: '0 0 16px',
                              fontSize: '10.5px',
                              color: '#64748b',
                              lineHeight: 1.45,
                              fontFamily: 'var(--mono)',
                              textTransform: 'uppercase',
                              letterSpacing: '0.04em',
                            }}
                          >
                            ARCHIVE VIEW<br />
                            OF ISRO<br />
                            CHANDRAYAAN &<br />
                            PARTNER AGENCIES
                          </p>

                          {/* Swipe Instructions */}
                          <div
                            style={{
                              fontSize: '10.5px',
                              color: '#94a3b8',
                              lineHeight: 1.45,
                              fontFamily: 'var(--mono)',
                              textTransform: 'uppercase',
                              marginBottom: '18px',
                            }}
                          >
                            SWIPE L/R TO<br />
                            CYCLE IMAGES.
                          </div>

                          {/* Local Time Metric */}
                          <div style={{ marginTop: '10px' }}>
                            <span style={{ fontSize: '10px', fontFamily: 'var(--mono)', color: '#64748b', display: 'block' }}>
                              ▪ LOCAL TIME:
                            </span>
                            <strong style={{ fontSize: '13px', fontFamily: 'var(--mono)', color: '#38bdf8', fontWeight: 800, letterSpacing: '0.06em' }}>
                              VDEC 15
                            </strong>
                          </div>
                        </div>

                        {/* Bottom ISRO Emblem & Feed Stable Tag */}
                        <div
                          style={{
                            borderTop: '1px solid rgba(255, 255, 255, 0.08)',
                            paddingTop: '14px',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '6px',
                          }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <img
                              src="/assets/isro_logo.svg"
                              alt="ISRO Logo"
                              style={{ height: '34px', objectFit: 'contain', filter: 'brightness(1.15)' }}
                            />
                          </div>
                          <span style={{ fontSize: '9px', fontFamily: 'var(--mono)', color: '#64748b', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
                            FEED STABLE<br />
                            [LOWER RANGER 1]
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Deep Telemetry & Scientific Context Cards (Kept Intact Directly Below Screen) */}
                  <div
                    style={{
                      marginTop: '20px',
                      display: 'grid',
                      gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
                      gap: '16px',
                    }}
                  >
                    {/* Mission Context & Scientific Significance */}
                    <div
                      style={{
                        background: 'rgba(8, 5, 22, 0.75)',
                        border: '1px solid rgba(138, 107, 255, 0.35)',
                        borderRadius: '14px',
                        padding: '18px 20px',
                        display: 'flex',
                        flexDirection: 'column',
                        justifyContent: 'space-between',
                      }}
                    >
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                          <span style={{ fontSize: '10px', fontFamily: 'var(--mono)', fontWeight: 800, color: 'var(--amber)', letterSpacing: '0.08em' }}>
                            SELECTED MISSION TELEMETRY
                          </span>
                          <span style={{ fontSize: '10px', fontFamily: 'var(--mono)', color: '#34d399', background: 'rgba(52,211,153,0.15)', padding: '2px 6px', borderRadius: '4px' }}>
                            {selectedScreen.agency}
                          </span>
                        </div>
                        <h4 style={{ margin: '0 0 6px 0', fontSize: '16px', color: '#ffffff', fontWeight: 800 }}>
                          {selectedScreen.title}
                        </h4>
                        <p style={{ margin: 0, fontSize: '13px', color: '#c4b5fd', lineHeight: 1.6 }}>
                          {selectedScreen.desc}
                        </p>
                      </div>

                      <div style={{ marginTop: '12px', fontSize: '11px', fontFamily: 'var(--mono)', color: 'var(--ink-dim)' }}>
                        RESOLUTION: <strong style={{ color: '#ffffff' }}>{selectedScreen.resolution}</strong>
                      </div>
                    </div>

                    {/* 4-Metric Radiometric Sensor Telemetry Grid */}
                    <div
                      style={{
                        background: 'rgba(8, 5, 22, 0.75)',
                        border: '1px solid rgba(255, 255, 255, 0.1)',
                        borderRadius: '14px',
                        padding: '18px 20px',
                        display: 'flex',
                        flexDirection: 'column',
                        justifyContent: 'space-between',
                        gap: '12px',
                      }}
                    >
                      <div
                        style={{
                          display: 'grid',
                          gridTemplateColumns: '1fr 1fr',
                          gap: '10px',
                          background: 'rgba(0, 0, 0, 0.45)',
                          padding: '12px',
                          borderRadius: '8px',
                          border: '1px solid rgba(255, 255, 255, 0.06)',
                          fontFamily: 'var(--mono)',
                          fontSize: '11.5px',
                        }}
                      >
                        <div>
                          <span style={{ color: 'var(--ink-dim)', fontSize: '9.5px', display: 'block' }}>SOLAR ANGLE</span>
                          <strong style={{ color: '#fbbf24' }}>{selectedScreen.telemetry.sunAngle}</strong>
                        </div>
                        <div>
                          <span style={{ color: 'var(--ink-dim)', fontSize: '9.5px', display: 'block' }}>ORBIT / ELEVATION</span>
                          <strong style={{ color: '#c084fc' }}>{selectedScreen.telemetry.elevation}</strong>
                        </div>
                        <div>
                          <span style={{ color: 'var(--ink-dim)', fontSize: '9.5px', display: 'block' }}>FIELD OF VIEW</span>
                          <strong style={{ color: '#34d399' }}>{selectedScreen.telemetry.fov}</strong>
                        </div>
                        <div>
                          <span style={{ color: 'var(--ink-dim)', fontSize: '9.5px', display: 'block' }}>SURFACE TEMP</span>
                          <strong style={{ color: '#38bdf8' }}>{selectedScreen.telemetry.temp}</strong>
                        </div>
                      </div>

                      {/* Comparative Truth Reference Card */}
                      <div
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '12px',
                          padding: '8px 12px',
                          background: 'rgba(138, 107, 255, 0.08)',
                          borderRadius: '8px',
                          border: '1px solid rgba(138, 107, 255, 0.25)',
                        }}
                      >
                        <img
                          src={selectedScreen.refImg}
                          alt="Reference comparison"
                          style={{
                            width: '44px',
                            height: '44px',
                            borderRadius: '6px',
                            objectFit: 'cover',
                            border: '1px solid rgba(255,255,255,0.2)',
                          }}
                        />
                        <div style={{ display: 'flex', flexDirection: 'column' }}>
                          <span style={{ fontSize: '9.5px', fontFamily: 'var(--mono)', color: '#a855f7', fontWeight: 800 }}>
                            COMPARATIVE TRUTH: {selectedScreen.refTag}
                          </span>
                          <span style={{ fontSize: '11px', color: '#e2e8f0', fontWeight: 600 }}>
                            Cross-instrument radiometric verification reference
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })()}
          </div>
        )}

        {/* TAB 2: REGISTRATION CONSOLE */}
        {activeTab === 'console' && (
          <>
            <div className="hero">
              <h1>Chandrayaan-2 optical images, aligned to LRO NAC ground truth.</h1>
              <p>
                Sun-angle and scale invariant correspondence between TMC-2 and reference imagery matched, validated, and scored in one view.
              </p>
            </div>

            <div className="grid">
              <div className="panel viewer">
                <div className="viewer-head">
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span className="label">
                      TMC-2 ORBITER STRIP [CH-2] <span style={{ color: 'var(--ink-dim)' }}>vs</span> LRO NAC GROUND TRUTH [NASA]
                    </span>
                    <span style={{ fontSize: '10px', fontFamily: 'var(--mono)', color: '#34d399', background: 'rgba(52, 211, 153, 0.12)', padding: '2px 6px', borderRadius: '4px', border: '1px solid rgba(52, 211, 153, 0.3)' }}>
                      HOMOGRAPHY SYNC ACTIVE
                    </span>
                  </div>

                  <div className="viewer-actions">
                    <button
                      className={`play-video-btn ${isPlaying ? 'active' : ''}`}
                      onClick={() => setIsPlaying(!isPlaying)}
                      title="Toggle automated scan loop"
                      style={{ padding: '3px 10px', fontSize: '10.5px' }}
                    >
                      <span>{isPlaying ? '⏸ Laser Loop' : '▶ Scan'}</span>
                    </button>
                    <span style={{ fontSize: '11px', fontFamily: 'var(--mono)', color: 'var(--ink-dim)' }}>
                      DATUM: <strong style={{ color: '#c4b5fd' }}>MOON_2000</strong>
                    </span>
                  </div>
                </div>

                <div className="viewer-split" id="viewerSplit">
                  <div className="pane" id="paneSource">
                    <div className="viewfinder-bracket tl"></div>
                    <div className="viewfinder-bracket tr"></div>
                    <div className="viewfinder-bracket bl"></div>
                    <div className="viewfinder-bracket br"></div>

                    <div style={{ position: 'absolute', top: '12px', left: '16px', zIndex: 16, display: 'flex', flexDirection: 'column', gap: '3px' }}>
                      <span className="header-tag" style={{ position: 'static', margin: 0, padding: 0 }}>
                        CHANDRAYAAN-2 · TMC-2
                      </span>
                      <span style={{ fontSize: '10px', fontFamily: 'var(--mono)', color: '#fbbf24', background: 'rgba(0,0,0,0.75)', padding: '2px 6px', borderRadius: '4px', width: 'fit-content' }}>
                        RES: 5.0 m/px · NADIR STRIP
                      </span>
                    </div>

                    <img
                      src="/assets/tmc2.jpg"
                      alt="Chandrayaan-2 TMC-2 Orbiter Strip"
                      className="source-img"
                      style={{
                        filter: claheOn
                          ? 'contrast(1.35) brightness(1.05)'
                          : 'contrast(0.95) brightness(0.95)',
                      }}
                    />
                    <div
                      className="tile-grid-overlay"
                      style={{ backgroundSize: `${Math.round(tileSize / 4)}px ${Math.round(tileSize / 4)}px` }}
                    />

                    {/* Sci-Fi HUD Crosshair Center Marker */}
                    <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', width: '28px', height: '28px', border: '1px dashed rgba(251,191,36,0.6)', borderRadius: '50%', pointerEvents: 'none', zIndex: 14 }}>
                      <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', width: '4px', height: '4px', background: '#fbbf24', borderRadius: '50%' }}></div>
                    </div>

                    {/* Dense Green Feature Keypoints Overlay (Image 1 Style) */}
                    <svg style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', zIndex: 16, pointerEvents: 'none' }} viewBox="0 0 500 340">
                      {greenFeaturePoints.map((pt) => {
                        const isVisible = sequencePhase !== 'green-scan' || (pt.x / 500) * 100 <= scanPosGreen;
                        if (!isVisible) return null;
                        return (
                          <g key={pt.id}>
                            <circle cx={pt.x} cy={pt.y} r={pt.r + 3.5} className="green-feature-pulse" />
                            <circle cx={pt.x} cy={pt.y} r={pt.r} className="green-feature-dot" />
                          </g>
                        );
                      })}
                    </svg>

                    {/* Green Laser Scan Beam on Image 1 */}
                    {sequencePhase === 'green-scan' && (
                      <div
                        className="parallel-scan-beam green-beam"
                        style={{
                          left: `${scanPosGreen}%`,
                          transition: 'left 50ms linear'
                        }}
                      />
                    )}

                    {/* Yellow Synchronized Scan Beam on Image 1 */}
                    {sequencePhase === 'yellow-scan' && (
                      <div
                        className="parallel-scan-beam yellow-beam"
                        style={{
                          left: `${scanPosYellow}%`,
                          transition: 'left 50ms linear'
                        }}
                      />
                    )}
                  </div>

                  <div className="pane" id="paneRef">
                    <div className="viewfinder-bracket tl"></div>
                    <div className="viewfinder-bracket tr"></div>
                    <div className="viewfinder-bracket bl"></div>
                    <div className="viewfinder-bracket br"></div>

                    <div style={{ position: 'absolute', top: '12px', left: '16px', zIndex: 19, display: 'flex', flexDirection: 'column', gap: '3px' }}>
                      <span className="header-tag" style={{ position: 'static', margin: 0, padding: 0 }}>
                        NASA LRO NAC GROUND TRUTH
                      </span>
                      <span style={{ fontSize: '10px', fontFamily: 'var(--mono)', color: '#34d399', background: 'rgba(0,0,0,0.75)', padding: '2px 6px', borderRadius: '4px', width: 'fit-content' }}>
                        RES: 0.5 m/px · MONO NARROW ANGLE
                      </span>
                      {sequencePhase === 'blue-scan' && (
                        <span style={{ fontSize: '9px', fontFamily: 'var(--mono)', color: '#38bdf8', background: 'rgba(0,0,0,0.85)', padding: '2px 8px', borderRadius: '4px', border: '1px solid #38bdf8', boxShadow: '0 0 8px rgba(56,189,248,0.4)', fontWeight: 800, width: 'fit-content' }}>
                          🔵 HOLOGRAPHIC GRID TARGETING · {Math.round(scanPosBlue)}%
                        </span>
                      )}
                      {sequencePhase === 'yellow-scan' && (
                        <span style={{ fontSize: '9px', fontFamily: 'var(--mono)', color: '#fbbf24', background: 'rgba(0,0,0,0.85)', padding: '2px 8px', borderRadius: '4px', border: '1px solid #fbbf24', boxShadow: '0 0 8px rgba(251,191,36,0.4)', fontWeight: 800, width: 'fit-content' }}>
                          🟡 DUAL SPECTRUM SYNC · {Math.round(scanPosYellow)}%
                        </span>
                      )}
                    </div>

                    <img
                      src="/assets/lronac.jpg"
                      alt="NASA LRO NAC Reference Target"
                      className="source-img"
                      style={{
                        filter: claheOn
                          ? 'contrast(1.3) brightness(1.05)'
                          : 'contrast(0.95) brightness(0.95)',
                      }}
                    />
                    <div
                      className="tile-grid-overlay"
                      style={{ backgroundSize: `${Math.round(tileSize / 4)}px ${Math.round(tileSize / 4)}px` }}
                    />

                    {/* Holographic Tactical Grid & Brackets (Image 2 Style) */}
                    {(sequencePhase === 'blue-scan' || sequencePhase === 'yellow-scan' || sequencePhase === 'mapping' || sequencePhase === 'locked') && (
                      <div
                        className="blue-tactical-grid-overlay"
                        style={{
                          opacity: sequencePhase === 'blue-scan' ? Math.min(1, Math.max(0.25, scanPosBlue / 75)) : 0.9,
                          clipPath: sequencePhase === 'blue-scan' ? `inset(0 ${Math.max(0, 100 - scanPosBlue)}% 0 0)` : 'none'
                        }}
                      >
                        <div className="blue-grid-mesh" />
                        <div className="blue-corner-bracket tl" />
                        <div className="blue-corner-bracket tr" />
                        <div className="blue-corner-bracket bl" />
                        <div className="blue-corner-bracket br" />
                        <div className="blue-subtarget-frame">
                          <div className="blue-subtarget-frame-inner" />
                        </div>
                        <div style={{ position: 'absolute', bottom: '16px', right: '16px', fontSize: '9px', fontFamily: 'var(--mono)', color: '#38bdf8', textShadow: '0 0 8px #38bdf8', fontWeight: 800, background: 'rgba(0,0,0,0.85)', padding: '2px 8px', borderRadius: '4px', border: '1px solid rgba(56,189,248,0.5)' }}>
                          HOLOGRAPHIC TARGET MESH // 0.5m GSD
                        </div>
                      </div>
                    )}

                    {/* Sci-Fi HUD Crosshair Center Marker */}
                    <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', width: '28px', height: '28px', border: '1px dashed rgba(52,211,153,0.6)', borderRadius: '50%', pointerEvents: 'none', zIndex: 14 }}>
                      <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', width: '4px', height: '4px', background: '#34d399', borderRadius: '50%' }}></div>
                    </div>

                    {/* Blue Laser Scan Beam on Image 2 */}
                    {sequencePhase === 'blue-scan' && (
                      <div
                        className="parallel-scan-beam blue-beam"
                        style={{
                          left: `${scanPosBlue}%`,
                          transition: 'left 50ms linear'
                        }}
                      />
                    )}

                    {/* Yellow Synchronized Scan Beam on Image 2 */}
                    {sequencePhase === 'yellow-scan' && (
                      <div
                        className="parallel-scan-beam yellow-beam"
                        style={{
                          left: `${scanPosYellow}%`,
                          transition: 'left 50ms linear'
                        }}
                      />
                    )}
                  </div>

                  {(sequencePhase === 'mapping' || sequencePhase === 'locked') && (
                    <svg className="cross-overlay" viewBox="0 0 1000 340">
                      {constellationLines.map((line, idx) => {
                        const n1 = getNode(line.from);
                        const n2 = getNode(line.to);
                        if (!n1 || !n2) return null;

                        const dx = n2.x - n1.x;
                        const dy = n2.y - n1.y;

                        const lineStart = line.order * 0.12;
                        const lineEnd = lineStart + 0.55;
                        const localProgress = Math.min(1, Math.max(0, (shootProgress - lineStart) / (lineEnd - lineStart)));

                        if (localProgress <= 0) return null;

                        const currentX2 = n1.x + dx * localProgress;
                        const currentY2 = n1.y + dy * localProgress;

                        return (
                          <g key={`cl-${idx}`}>
                            <line
                              x1={n1.x}
                              y1={n1.y}
                              x2={currentX2}
                              y2={currentY2}
                              stroke="#000000"
                              strokeWidth="5.5"
                              strokeLinecap="round"
                            />

                            <line
                              className="constellation-line-glow"
                              x1={n1.x}
                              y1={n1.y}
                              x2={currentX2}
                              y2={currentY2}
                            />

                            {localProgress < 1 && (
                              <circle
                                cx={currentX2}
                                cy={currentY2}
                                r="5"
                                className="laser-head-spark"
                              />
                            )}
                          </g>
                        );
                      })}

                      {constellationNodes
                        .filter((n) => n.isSource)
                        .map((n) => (
                          <g key={n.id}>
                            <circle
                              cx={n.x}
                              cy={n.y}
                              className="node-outer-halo"
                              fill="none"
                              stroke="#c084fc"
                              filter="drop-shadow(0 0 8px #a855f7)"
                            />
                            <circle
                              cx={n.x}
                              cy={n.y}
                              r="7"
                              fill="none"
                              stroke="#ffffff"
                              strokeWidth="1.8"
                              filter="drop-shadow(0 0 4px #c084fc)"
                            />
                            <circle
                              cx={n.x}
                              cy={n.y}
                              r="4"
                              fill="#ffffff"
                              filter="drop-shadow(0 0 6px #ffffff)"
                            />
                            {subpixelOn && (
                              <g>
                                <line x1={n.x - 7} y1={n.y} x2={n.x + 7} y2={n.y} stroke="#34d399" strokeWidth="1.4" filter="drop-shadow(0 0 3px #34d399)" />
                                <line x1={n.x} y1={n.y - 7} x2={n.x} y2={n.y + 7} stroke="#34d399" strokeWidth="1.4" filter="drop-shadow(0 0 3px #34d399)" />
                              </g>
                            )}
                          </g>
                        ))}

                      {constellationNodes
                        .filter((n) => !n.isSource)
                        .map((n) => {
                          const arrived = shootProgress > 0.45;
                          if (!arrived) return null;

                          return (
                            <g key={n.id}>
                              <circle
                                cx={n.x}
                                cy={n.y}
                                className="node-outer-halo"
                                fill="none"
                                stroke="#c084fc"
                                filter="drop-shadow(0 0 8px #a855f7)"
                              />
                              <circle
                                cx={n.x}
                                cy={n.y}
                                r="7"
                                fill="none"
                                stroke="#ffffff"
                                strokeWidth="1.8"
                                filter="drop-shadow(0 0 4px #c084fc)"
                              />
                              <circle
                                cx={n.x}
                                cy={n.y}
                                r="4"
                                fill="#ffffff"
                                filter="drop-shadow(0 0 6px #ffffff)"
                              />
                              {subpixelOn && (
                                <g>
                                  <line x1={n.x - 7} y1={n.y} x2={n.x + 7} y2={n.y} stroke="#34d399" strokeWidth="1.4" filter="drop-shadow(0 0 3px #34d399)" />
                                  <line x1={n.x} y1={n.y - 7} x2={n.x} y2={n.y + 7} stroke="#34d399" strokeWidth="1.4" filter="drop-shadow(0 0 3px #34d399)" />
                                </g>
                              )}
                            </g>
                          );
                        })}
                    </svg>
                  )}
                </div>

                <div className="viewer-foot">
                  <button
                    className="transport-btn"
                    title="Cycle to next tile"
                    onClick={() => setCurrentTile((prev) => (prev % totalTiles) + 1)}
                  >
                    ⟲
                  </button>

                  <div className="scrub-track">
                    <input
                      type="range"
                      min="1"
                      max={totalTiles}
                      value={currentTile}
                      onChange={(e) => {
                        const val = Number(e.target.value);
                        setCurrentTile(val);
                        // When user manually scrubs, sync the pipeline phase and stage
                        setIsPlaying(false);
                        const progress = (val - 1) / (totalTiles - 1 || 1);
                        if (progress < 0.20) {
                          setSequencePhase('green-scan');
                          const subP = progress / 0.20;
                          setScanPosGreen(subP * 100);
                          setScanPosBlue(0);
                          setScanPosYellow(0);
                          setShootProgress(0);
                          setScanPosA(subP * 100);
                          setScanPosB(0);
                          setActiveStep(1);
                        } else if (progress < 0.40) {
                          setSequencePhase('blue-scan');
                          const subP = (progress - 0.20) / 0.20;
                          setScanPosGreen(100);
                          setScanPosBlue(subP * 100);
                          setScanPosYellow(0);
                          setShootProgress(0);
                          setScanPosA(100);
                          setScanPosB(subP * 100);
                          setActiveStep(2);
                        } else if (progress < 0.60) {
                          setSequencePhase('yellow-scan');
                          const subP = (progress - 0.40) / 0.20;
                          setScanPosGreen(100);
                          setScanPosBlue(100);
                          setScanPosYellow(subP * 100);
                          setShootProgress(0);
                          setScanPosA(subP * 100);
                          setScanPosB(subP * 100);
                          setActiveStep(3);
                        } else if (progress < 0.85) {
                          setSequencePhase('mapping');
                          const subP = (progress - 0.60) / 0.25;
                          setScanPosGreen(100);
                          setScanPosBlue(100);
                          setScanPosYellow(100);
                          setShootProgress(subP);
                          setScanPosA(100);
                          setScanPosB(100);
                          setActiveStep(4);
                        } else {
                          setSequencePhase('locked');
                          setScanPosGreen(100);
                          setScanPosBlue(100);
                          setScanPosYellow(100);
                          setShootProgress(1);
                          setScanPosA(100);
                          setScanPosB(100);
                          setActiveStep(5);
                        }
                      }}
                    />
                  </div>

                  <div className="scrub-val">
                    tile {currentTile}/{totalTiles}
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '10px', fontSize: '11px', fontFamily: 'var(--mono)', flexWrap: 'wrap', gap: '8px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                    <span style={{ color: sequencePhase === 'green-scan' ? '#22c55e' : 'var(--ink-dim)', fontWeight: sequencePhase === 'green-scan' ? 800 : 400, textShadow: sequencePhase === 'green-scan' ? '0 0 8px rgba(34,197,94,0.6)' : 'none' }}>
                      [1] Green Scan ({Math.round(scanPosGreen)}%)
                    </span>
                    <span style={{ color: 'var(--ink-faint)' }}>→</span>
                    <span style={{ color: sequencePhase === 'blue-scan' ? '#38bdf8' : 'var(--ink-dim)', fontWeight: sequencePhase === 'blue-scan' ? 800 : 400, textShadow: sequencePhase === 'blue-scan' ? '0 0 8px rgba(56,189,248,0.6)' : 'none' }}>
                      [2] Blue Scan ({Math.round(scanPosBlue)}%)
                    </span>
                    <span style={{ color: 'var(--ink-faint)' }}>→</span>
                    <span style={{ color: sequencePhase === 'yellow-scan' ? '#fbbf24' : 'var(--ink-dim)', fontWeight: sequencePhase === 'yellow-scan' ? 800 : 400, textShadow: sequencePhase === 'yellow-scan' ? '0 0 8px rgba(251,191,36,0.6)' : 'none' }}>
                      [3] Yellow Sync ({Math.round(scanPosYellow)}%)
                    </span>
                    <span style={{ color: 'var(--ink-faint)' }}>→</span>
                    <span style={{ color: sequencePhase === 'mapping' ? '#c084fc' : 'var(--ink-dim)', fontWeight: sequencePhase === 'mapping' ? 800 : 400, textShadow: sequencePhase === 'mapping' ? '0 0 8px rgba(192,132,252,0.6)' : 'none' }}>
                      [4] Final Mapping ({Math.round(shootProgress * 100)}%)
                    </span>
                    <span style={{ color: 'var(--ink-faint)' }}>→</span>
                    <span style={{ color: sequencePhase === 'locked' ? '#34d399' : 'var(--ink-dim)', fontWeight: sequencePhase === 'locked' ? 800 : 400, textShadow: sequencePhase === 'locked' ? '0 0 8px rgba(52,211,153,0.6)' : 'none' }}>
                      [5] Locked
                    </span>
                  </div>

                  <div style={{
                    color: sequencePhase === 'green-scan'
                      ? '#22c55e'
                      : sequencePhase === 'blue-scan'
                        ? '#38bdf8'
                        : sequencePhase === 'yellow-scan'
                          ? '#fbbf24'
                          : sequencePhase === 'mapping'
                            ? '#c084fc'
                            : '#34d399',
                    fontWeight: 700,
                    fontFamily: 'var(--mono)',
                    fontSize: '11px'
                  }}>
                    {sequencePhase === 'green-scan'
                      ? `🟢 GREEN FEATURE SCAN · ${Math.round(scanPosGreen)}%`
                      : sequencePhase === 'blue-scan'
                        ? `🔵 BLUE GRID TARGETING · ${Math.round(scanPosBlue)}%`
                        : sequencePhase === 'yellow-scan'
                          ? `🟡 YELLOW DUAL CORRELATION · ${Math.round(scanPosYellow)}%`
                          : sequencePhase === 'mapping'
                            ? `⚡ FINAL MAPPING VECTORS · ${Math.round(shootProgress * 100)}%`
                            : '🔒 REGISTRATION LOCKED · 100%'}
                  </div>
                </div>

                {/* Registration Mission Telemetry Strip */}
                <div
                  style={{
                    marginTop: '12px',
                    padding: '8px 12px',
                    background: 'rgba(5, 3, 14, 0.85)',
                    borderRadius: '8px',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
                    gap: '10px',
                    fontSize: '11px',
                    fontFamily: 'var(--mono)',
                  }}
                >
                  <div style={{ display: 'flex', flexDirection: 'column' }}>
                    <span style={{ color: 'var(--ink-dim)', fontSize: '9.5px' }}>SENSOR PAIR</span>
                    <span style={{ color: '#ffffff', fontWeight: 700 }}>TMC-2 ↔ LRO NAC</span>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column' }}>
                    <span style={{ color: 'var(--ink-dim)', fontSize: '9.5px' }}>SCALE DISPARITY</span>
                    <span style={{ color: '#fbbf24', fontWeight: 700 }}>10:1 (5.0m vs 0.5m)</span>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column' }}>
                    <span style={{ color: 'var(--ink-dim)', fontSize: '9.5px' }}>ILLUMINATION</span>
                    <span style={{ color: '#c084fc', fontWeight: 700 }}>Δ 41.2° Solar Angle</span>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column' }}>
                    <span style={{ color: 'var(--ink-dim)', fontSize: '9.5px' }}>HOMOGRAPHY STATUS</span>
                    <span style={{ color: '#34d399', fontWeight: 700 }}>Projective 3x3 Locked</span>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column' }}>
                    <span style={{ color: 'var(--ink-dim)', fontSize: '9.5px' }}>GEO-REFERENCING</span>
                    <span style={{ color: '#38bdf8', fontWeight: 700 }}>MOON_2000 IAU Geoid</span>
                  </div>
                </div>
              </div>

              <div className="panel controls">
                <h3>preprocessing</h3>

                <div className="ctrl">
                  <div className="ctrl-row">
                    <span className="ctrl-name">CLAHE preprocessing</span>
                    <div
                      className={`switch ${claheOn ? 'on' : ''}`}
                      onClick={() => setClaheOn(!claheOn)}
                    >
                      <div className="knob"></div>
                    </div>
                  </div>
                </div>

                <div className="ctrl">
                  <div className="ctrl-row">
                    <span className="ctrl-name">MAGSAC++ threshold</span>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span style={{ fontSize: '9px', fontFamily: 'var(--mono)', padding: '1px 5px', borderRadius: '4px', background: magsacThreshold < 1.8 ? 'rgba(52,211,153,0.15)' : magsacThreshold < 3.4 ? 'rgba(251,191,36,0.15)' : 'rgba(239,68,68,0.15)', color: magsacThreshold < 1.8 ? '#34d399' : magsacThreshold < 3.4 ? '#fbbf24' : '#f87171', border: '1px solid currentColor' }}>
                        {magsacThreshold < 1.8 ? 'ULTRA-TIGHT' : magsacThreshold < 3.4 ? 'BALANCED' : 'HIGH-RECALL'}
                      </span>
                      <span className="ctrl-name" style={{ color: 'var(--amber)', fontWeight: 700, fontFamily: 'var(--mono)' }}>
                        {magsacThreshold.toFixed(1)} px
                      </span>
                    </div>
                  </div>
                  <div className="range-wrap">
                    <input
                      type="range"
                      min="0.5"
                      max="5.0"
                      step="0.1"
                      value={magsacThreshold}
                      onChange={(e) => setMagsacThreshold(Number(e.target.value))}
                      style={{
                        '--val-pct': `${((magsacThreshold - 0.5) / (5.0 - 0.5)) * 100}%`,
                      }}
                    />
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '9.5px', fontFamily: 'var(--mono)', color: 'var(--ink-faint)', marginTop: '3px' }}>
                      <span>0.5 px (Tight)</span>
                      <span>5.0 px (Loose)</span>
                    </div>
                  </div>
                </div>

                <div className="ctrl">
                  <div className="ctrl-row">
                    <span className="ctrl-name">Tile size</span>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span style={{ fontSize: '9px', fontFamily: 'var(--mono)', padding: '1px 5px', borderRadius: '4px', background: 'rgba(192, 132, 252, 0.15)', color: '#c084fc', border: '1px solid rgba(192, 132, 252, 0.35)' }}>
                        {Math.pow(Math.round(512 / tileSize), 2)} TILES
                      </span>
                      <span className="ctrl-name" style={{ color: 'var(--amber)', fontWeight: 700, fontFamily: 'var(--mono)' }}>
                        {tileSize} px
                      </span>
                    </div>
                  </div>
                  <div className="range-wrap">
                    <input
                      type="range"
                      min="64"
                      max="512"
                      step="32"
                      value={tileSize}
                      onChange={(e) => setTileSize(Number(e.target.value))}
                      style={{
                        '--val-pct': `${((tileSize - 64) / (512 - 64)) * 100}%`,
                      }}
                    />
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '9.5px', fontFamily: 'var(--mono)', color: 'var(--ink-faint)', marginTop: '3px' }}>
                      <span>64 px (64 tiles)</span>
                      <span>512 px (1 tile)</span>
                    </div>
                  </div>
                </div>

                <div className="ctrl">
                  <div className="ctrl-row">
                    <span className="ctrl-name">Sub-pixel refinement</span>
                    <div
                      className={`switch ${subpixelOn ? 'on' : ''}`}
                      onClick={() => setSubpixelOn(!subpixelOn)}
                    >
                      <div className="knob"></div>
                    </div>
                  </div>
                </div>

                <div className="ctrl">
                  <div className="ctrl-row">
                    <span className="ctrl-name">Spatial uniformity filter</span>
                    <div
                      className={`switch ${uniformityOn ? 'on' : ''}`}
                      onClick={() => setUniformityOn(!uniformityOn)}
                    >
                      <div className="knob"></div>
                    </div>
                  </div>
                </div>

                {/* Real-Time Homography & Solver Diagnostics */}
                <div
                  style={{
                    marginTop: '14px',
                    padding: '10px 12px',
                    background: 'rgba(5, 3, 15, 0.65)',
                    borderRadius: '8px',
                    border: '1px solid rgba(255, 255, 255, 0.08)',
                    fontFamily: 'var(--mono)',
                    fontSize: '11px',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px', borderBottom: '1px solid rgba(255,255,255,0.06)', paddingBottom: '5px' }}>
                    <span style={{ color: 'var(--amber)', fontWeight: 700, letterSpacing: '0.04em', fontSize: '10px' }}>
                      MATHEMATICAL SOLVER STATE
                    </span>
                    <span style={{ color: '#34d399', fontSize: '9px', fontWeight: 600 }}>
                      CONVERGED (3×3)
                    </span>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px', fontSize: '9.5px' }}>
                    <div>
                      <span style={{ color: 'var(--ink-dim)', display: 'block' }}>Epipolar Tolerance:</span>
                      <strong style={{ color: '#fbbf24' }}>±{(magsacThreshold * 0.14).toFixed(2)} px</strong>
                    </div>
                    <div>
                      <span style={{ color: 'var(--ink-dim)', display: 'block' }}>Quad Grid Division:</span>
                      <strong style={{ color: '#c084fc' }}>{Math.round(512 / tileSize)}×{Math.round(512 / tileSize)} quads</strong>
                    </div>
                    <div>
                      <span style={{ color: 'var(--ink-dim)', display: 'block' }}>Sub-Pixel Est:</span>
                      <strong style={{ color: subpixelOn ? '#34d399' : '#94a3b8' }}>{subpixelOn ? 'Taylor 2D (0.2px)' : 'Quantized (1px)'}</strong>
                    </div>
                    <div>
                      <span style={{ color: 'var(--ink-dim)', display: 'block' }}>ANMS Spatial Dist:</span>
                      <strong style={{ color: uniformityOn ? '#38bdf8' : '#94a3b8' }}>{uniformityOn ? 'Uniform Spread' : 'Clustered Rims'}</strong>
                    </div>
                  </div>
                </div>

                {/* Quick Presets for Instant Factor Alignment */}
                <div style={{ marginTop: '12px' }}>
                  <div style={{ fontSize: '10px', fontFamily: 'var(--mono)', color: 'var(--ink-dim)', marginBottom: '6px' }}>
                    REGISTRATION PRESETS:
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '6px' }}>
                    <button
                      onClick={() => {
                        setMagsacThreshold(3.6);
                        setTileSize(512);
                        setSubpixelOn(false);
                        setUniformityOn(false);
                      }}
                      title="Fast draft scan: 512px single tile, integer pixels"
                      style={{
                        background: 'rgba(255, 255, 255, 0.04)',
                        border: '1px solid rgba(255, 255, 255, 0.1)',
                        borderRadius: '6px',
                        padding: '6px 4px',
                        color: '#cbd5e1',
                        fontSize: '9.5px',
                        fontFamily: 'var(--mono)',
                        cursor: 'pointer',
                        textAlign: 'center',
                        transition: 'all 0.2s ease',
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.borderColor = 'var(--amber)')}
                      onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.1)')}
                    >
                      ⚡ Fast
                    </button>
                    <button
                      onClick={() => {
                        setMagsacThreshold(2.4);
                        setTileSize(256);
                        setSubpixelOn(true);
                        setUniformityOn(true);
                        setClaheOn(true);
                      }}
                      title="Chandrayaan-2 Recommended: 256px quads, sub-pixel on, uniformity on"
                      style={{
                        background: 'rgba(251, 191, 36, 0.12)',
                        border: '1px solid #fbbf24',
                        borderRadius: '6px',
                        padding: '6px 4px',
                        color: '#fbbf24',
                        fontSize: '9.5px',
                        fontFamily: 'var(--mono)',
                        fontWeight: 700,
                        cursor: 'pointer',
                        textAlign: 'center',
                        boxShadow: '0 0 8px rgba(251,191,36,0.25)',
                        transition: 'all 0.2s ease',
                      }}
                    >
                      🎯 Balanced
                    </button>
                    <button
                      onClick={() => {
                        setMagsacThreshold(1.2);
                        setTileSize(128);
                        setSubpixelOn(true);
                        setUniformityOn(true);
                        setClaheOn(true);
                      }}
                      title="Ultra-precision: 128px dense quads, 1.2px threshold, sub-0.2px RMSE"
                      style={{
                        background: 'rgba(192, 132, 252, 0.1)',
                        border: '1px solid #c084fc',
                        borderRadius: '6px',
                        padding: '6px 4px',
                        color: '#c084fc',
                        fontSize: '9.5px',
                        fontFamily: 'var(--mono)',
                        cursor: 'pointer',
                        textAlign: 'center',
                        transition: 'all 0.2s ease',
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.borderColor = '#ffffff')}
                      onMouseLeave={(e) => (e.currentTarget.style.borderColor = '#c084fc')}
                    >
                      🔬 Ultra
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <div className="metrics">
              <div className="metric">
                <div
                  className="ring"
                  style={{
                    '--pct': currentMetrics.rmsePct,
                    '--ring-color': 'var(--violet)',
                  }}
                >
                  <span>{currentMetrics.rmsePct}%</span>
                </div>
                <div className="metric-info">
                  <div className="m-label">RMSE</div>
                  <div className="m-value">
                    {currentMetrics.rmseVal}
                    <sup>px</sup>
                  </div>
                </div>
              </div>

              <div className="metric">
                <div
                  className="ring"
                  style={{
                    '--pct': currentMetrics.inlierPct,
                    '--ring-color': 'var(--amber)',
                  }}
                >
                  <span>{currentMetrics.inlierPct}%</span>
                </div>
                <div className="metric-info">
                  <div className="m-label">Inlier count</div>
                  <div className="m-value">
                    {currentMetrics.inlierCount}
                    <sup>pts</sup>
                  </div>
                </div>
              </div>

              <div className="metric">
                <div
                  className="ring"
                  style={{
                    '--pct': currentMetrics.coveragePct,
                    '--ring-color': 'var(--magenta)',
                  }}
                >
                  <span>{currentMetrics.coveragePct}%</span>
                </div>
                <div className="metric-info">
                  <div className="m-label">Spatial coverage</div>
                  <div className="m-value">
                    {currentMetrics.coveragePct}
                    <sup>%</sup>
                  </div>
                </div>
              </div>

              <div className="metric">
                <div
                  className="ring"
                  style={{
                    '--pct': currentMetrics.gridPct,
                    '--ring-color': 'var(--emerald)',
                  }}
                >
                  <span>{currentMetrics.gridPct}%</span>
                </div>
                <div className="metric-info">
                  <div className="m-label">Grid occupancy</div>
                  <div className="m-value">
                    {currentMetrics.gridPct}
                    <sup>%</sup>
                  </div>
                </div>
              </div>
            </div>

            <div className="panel roadmap">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
                <h3
                  style={{
                    fontFamily: 'var(--mono)',
                    fontSize: '12px',
                    color: 'var(--ink-dim)',
                    margin: 0,
                    fontWeight: 600,
                  }}
                >
                  pipeline execution roadmap
                </h3>
                <span style={{ fontSize: '11px', fontFamily: 'var(--mono)', color: 'var(--amber)' }}>
                  Stage {activeStep}/6 Active · Click any step to inspect
                </span>
              </div>

              <div className="roadmap-track">
                {[
                  { id: 1, label: 'Feature matching', detail: 'SuperPoint dense detector extracts interest keypoints across high-contrast crater rims and terrace crests.' },
                  { id: 2, label: 'MAGSAC++ rejection', detail: `Eliminates outlier correspondencies with marginalizing sample consensus at ${magsacThreshold}px threshold.` },
                  { id: 3, label: 'Tiled re-matching', detail: `Quad-tree division (${tileSize}px tiles) forces keypoint extraction in low-texture, shadowed lunar mares.` },
                  { id: 4, label: 'Spatial uniformity', detail: uniformityOn ? 'Uniformity filter active: culling spatial clusters to prevent registration bias.' : 'Uniformity filter off: keypoint density governed solely by gradient intensity.' },
                  { id: 5, label: 'Sub-pixel refine', detail: subpixelOn ? 'Sub-pixel Taylor expansion active: residual error minimized down to 0.22px.' : 'Integer pixel accuracy only (RMSE ~ 1.45px).' },
                  { id: 6, label: 'Final registration', detail: 'Invertible 3x3 projective homography H matrix computed and locked with sub-pixel verification.' },
                ].map((step, idx, arr) => {
                  const isDone = step.id < activeStep;
                  const isActive = step.id === activeStep;
                  return (
                    <div
                      key={step.id}
                      className={`rm-step ${isDone ? 'done' : ''} ${isActive ? 'active' : ''}`}
                      onClick={() => setActiveStep(step.id)}
                      title={`Inspect Stage ${step.id}: ${step.label}`}
                    >
                      {idx < arr.length - 1 && <div className="rm-line"></div>}
                      <div className="dot"></div>
                      <div className="rm-label">{step.label}</div>
                    </div>
                  );
                })}
              </div>

              {/* Active Pipeline Stage Description Callout */}
              <div
                style={{
                  marginTop: '14px',
                  background: 'rgba(138, 107, 255, 0.08)',
                  border: '1px solid rgba(138, 107, 255, 0.3)',
                  borderRadius: '10px',
                  padding: '10px 14px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  fontFamily: 'var(--mono)',
                  fontSize: '11.5px',
                  color: '#f0ecfc',
                }}
              >
                <div>
                  <strong style={{ color: 'var(--amber)' }}>Stage {activeStep} Action: </strong>
                  {[
                    'SuperPoint dense detector extracts interest keypoints across high-contrast crater rims and terrace crests.',
                    `Eliminates outlier correspondencies with marginalizing sample consensus at ${magsacThreshold}px threshold.`,
                    `Quad-tree division (${tileSize}px tiles) forces keypoint extraction in low-texture, shadowed lunar mares.`,
                    uniformityOn ? 'Uniformity filter active: culling spatial clusters to prevent registration bias.' : 'Uniformity filter off: keypoint density governed solely by gradient intensity.',
                    subpixelOn ? 'Sub-pixel Taylor expansion active: residual error minimized down to 0.22px.' : 'Integer pixel accuracy only (RMSE ~ 1.45px).',
                    'Invertible 3x3 projective homography H matrix computed and locked with sub-pixel verification.',
                  ][activeStep - 1]}
                </div>
                <div style={{ color: 'var(--violet)', fontWeight: 700 }}>
                  Active Tile {currentTile}/24
                </div>
              </div>
            </div>
          </>
        )}

        {/* TAB 3: MULTI-MODAL FLOW */}
        {activeTab === 'multimodal' && (
          <div style={{ marginTop: '22px' }}>
            <div
              className="panel"
              style={{
                position: 'relative',
                padding: '30px 28px 28px 96px',
                border: '1px solid rgba(255, 255, 255, 0.28)',
                borderRadius: '16px',
                background: 'rgba(10, 7, 24, 0.88)',
                backdropFilter: 'blur(16px)',
                boxShadow: '0 12px 40px rgba(0, 0, 0, 0.75)',
              }}
            >
              <div style={{ position: 'absolute', top: '12px', left: '12px', width: '18px', height: '18px', borderTop: '2.5px solid #a855f7', borderLeft: '2.5px solid #a855f7' }}></div>
              <div style={{ position: 'absolute', top: '12px', right: '12px', width: '18px', height: '18px', borderTop: '2.5px solid #a855f7', borderRight: '2.5px solid #a855f7' }}></div>
              <div style={{ position: 'absolute', bottom: '12px', left: '12px', width: '18px', height: '18px', borderBottom: '2.5px solid #a855f7', borderLeft: '2.5px solid #a855f7' }}></div>
              <div style={{ position: 'absolute', bottom: '12px', right: '12px', width: '18px', height: '18px', borderBottom: '2.5px solid #a855f7', borderRight: '2.5px solid #a855f7' }}></div>

              {/* Functional Sidebar Toolbar with Generous Spacing */}
              <div
                style={{
                  position: 'absolute',
                  top: '32px',
                  left: '20px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '12px',
                  background: 'rgba(5, 3, 14, 0.94)',
                  padding: '10px 8px',
                  borderRadius: '14px',
                  border: '1.5px solid rgba(255, 255, 255, 0.22)',
                  boxShadow: '0 8px 24px rgba(0, 0, 0, 0.75)',
                  zIndex: 20,
                }}
              >
                {[
                  { icon: '🛰️', title: 'Sensors (OHRC / TMC-2 / IIRS)', id: 'sensors', desc: 'Active multi-spectral sensor pipeline' },
                  { icon: '📐', title: 'Solar Geometry (Incident Rays)', id: 'solar', desc: 'Incident illumination angles & solar azimuth calculator' },
                  { icon: '🔭', title: 'Optics Specs (GSD Resolution)', id: 'optics', desc: 'Spatial Ground Sampling Distance & MTF focal analysis' },
                  { icon: '🎯', title: 'Homography Warping (H 3x3)', id: 'warp', desc: 'Planar perspective projection & sub-pixel transformation' },
                  { icon: '📊', title: 'Multi-Modal Telemetry (CoH-S)', id: 'telemetry', desc: 'Cross-gradient correlation metrics & feature inlier graph' },
                ].map((item) => (
                  <button
                    key={item.id}
                    title={`${item.title}- ${item.desc}`}
                    onClick={() => setMmActiveTool(item.id)}
                    style={{
                      width: '38px',
                      height: '38px',
                      borderRadius: '10px',
                      background: mmActiveTool === item.id ? 'var(--violet)' : 'rgba(255, 255, 255, 0.05)',
                      border: mmActiveTool === item.id ? '1.5px solid #ffffff' : '1px solid var(--panel-edge)',
                      color: '#ffffff',
                      cursor: 'pointer',
                      fontSize: '18px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
                      boxShadow: mmActiveTool === item.id ? '0 0 16px var(--violet-glow)' : 'none',
                      transform: mmActiveTool === item.id ? 'scale(1.08)' : 'scale(1)',
                    }}
                  >
                    {item.icon}
                  </button>
                ))}
              </div>

              <div style={{ marginBottom: '16px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px' }}>
                  <h2
                    style={{
                      fontSize: '24px',
                      fontWeight: 700,
                      margin: '0 0 6px',
                      color: '#ffffff',
                      letterSpacing: '-0.01em',
                      background: 'linear-gradient(90deg, #ffffff, #c084fc)',
                      WebkitBackgroundClip: 'text',
                      WebkitTextFillColor: 'transparent',
                    }}
                  >
                    Multi-Modal Registration & Solar Invariance
                  </h2>

                  {/* Active Tool Badge Drawer */}
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      background: 'rgba(138, 107, 255, 0.16)',
                      border: '1px solid var(--violet)',
                      padding: '4px 12px',
                      borderRadius: '8px',
                      fontSize: '11.5px',
                      fontFamily: 'var(--mono)',
                      color: '#d4c9fd',
                      boxShadow: '0 0 12px rgba(138, 107, 255, 0.3)',
                    }}
                  >
                    <span style={{ fontSize: '13px' }}>
                      {mmActiveTool === 'sensors' && '🛰️ Sensor Payloads'}
                      {mmActiveTool === 'solar' && '📐 Incident Solar Geometry'}
                      {mmActiveTool === 'optics' && '🔭 Optics & Spatial GSD'}
                      {mmActiveTool === 'warp' && '🎯 Projective Homography'}
                      {mmActiveTool === 'telemetry' && '📊 CoH-S Cross Spectral Telemetry'}
                    </span>
                  </div>
                </div>

                <p style={{ color: '#f0ecfc', fontSize: '13.5px', margin: 0, lineHeight: 1.6, maxWidth: '820px', fontWeight: 500 }}>
                  {mmActiveTool === 'sensors' && 'The integration of optical and spectral lunar images across varying solar illumination angles, sensor resolutions, and viewing geometries from Chandrayaan-2 payloads (OHRC, TMC-2, IIRS) into a unified ground-truth reference frame.'}
                  {mmActiveTool === 'solar' && 'Solar Geometry Mode: Simulating varying incident light rays (42° to 80°) across crater shadows to prevent false edge boundaries from fooling keypoint detectors.'}
                  {mmActiveTool === 'optics' && 'Optics Mode: Resolving scale disparity between high-magnification OHRC (0.25m/px), mapping camera TMC-2 (5.0m/px), and hyperspectral IIRS (80m/px) via scale-space pyramid.'}
                  {mmActiveTool === 'warp' && 'Homography Warping: Computing the planar 3x3 projection matrix that geometrically rectifies orbital tilt, spacecraft pitch, and topography perspective distortion.'}
                  {mmActiveTool === 'telemetry' && 'Multi-Modal Telemetry: Live verification of cross-gradient normalized mutual information (CoH-S) and high-confidence matched inliers.'}
                </p>
              </div>

              {/* 3 Multi-Modal Sensors with Real Solar Illumination Reactivity */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr auto 1fr auto 1fr',
                  alignItems: 'center',
                  gap: '14px',
                  margin: '22px 0',
                }}
              >
                {/* 1. OHRC (High Res 0.25m GSD) */}
                <div
                  onClick={() => setMmActiveSensor('ohrc')}
                  style={{
                    position: 'relative',
                    border: mmActiveSensor === 'ohrc' ? '2px solid var(--amber)' : '1px solid var(--panel-edge)',
                    borderRadius: '12px',
                    padding: '12px',
                    background: mmActiveSensor === 'ohrc' ? 'rgba(251, 191, 36, 0.12)' : 'rgba(0, 0, 0, 0.65)',
                    cursor: 'pointer',
                    transition: 'all 0.25s',
                    boxShadow: mmActiveSensor === 'ohrc' ? '0 0 20px rgba(251, 191, 36, 0.45)' : 'none',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <span style={{ fontWeight: 700, fontSize: '14px', color: '#ffffff' }}>OHRC</span>
                    <span style={{ fontSize: '11px', fontFamily: 'var(--mono)', color: 'var(--amber)' }}>0.25m GSD</span>
                  </div>

                  <div style={{ position: 'relative', height: '180px', borderRadius: '8px', overflow: 'hidden' }}>
                    <img
                      src={sunAngleDeg < 45 ? '/assets/sun_angle_low.jpg' : '/assets/sun_angle_high.jpg'}
                      alt="OHRC"
                      style={{
                        width: '100%',
                        height: '100%',
                        objectFit: 'cover',
                        filter: `contrast(${1.0 + (90 - sunAngleDeg) * 0.006}) brightness(${0.7 + (sunAngleDeg / 90) * 0.45})`,
                        transition: 'filter 0.2s ease, src 0.3s ease',
                      }}
                    />

                    {/* Dynamic Solar Angle Indicator Ray */}
                    <div
                      style={{
                        position: 'absolute',
                        top: `${Math.max(6, Math.round(55 - sunAngleDeg * 0.55))}%`,
                        left: '10px',
                        width: '32px',
                        height: '32px',
                        borderRadius: '50%',
                        background: 'radial-gradient(circle, #fff 15%, #fbbf24 65%, #f59e0b 100%)',
                        boxShadow: '0 0 16px #fbbf24, 0 0 30px rgba(251, 191, 36, 0.8)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: '16px',
                        transition: 'top 0.2s ease',
                      }}
                    >
                      ☀️
                    </div>
                    <svg style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', pointerEvents: 'none' }}>
                      <line
                        x1="26"
                        y1={`${Math.max(16, Math.round(65 - sunAngleDeg * 0.55))}%`}
                        x2="140"
                        y2="135"
                        stroke="#fbbf24"
                        strokeWidth="2.5"
                        strokeDasharray="4 3"
                        filter="drop-shadow(0 0 6px #fbbf24)"
                      />
                      <circle cx="140" cy="135" r="4.5" fill="#fbbf24" />
                    </svg>

                    {/* Simulated Shadow Cast Overlay */}
                    <div
                      style={{
                        position: 'absolute',
                        inset: 0,
                        background: `linear-gradient(${180 - sunAngleDeg}deg, rgba(0,0,0,0) 40%, rgba(0,0,0,${(90 - sunAngleDeg) * 0.007}) 100%)`,
                        pointerEvents: 'none',
                      }}
                    />
                  </div>

                  <div style={{ textAlign: 'center', marginTop: '8px', fontFamily: 'var(--mono)', fontSize: '11.5px', color: 'var(--amber)', fontWeight: 600 }}>
                    Illumination · Sun {sunAngleDeg}°
                  </div>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px' }}>
                  <div style={{ fontSize: '20px', filter: 'drop-shadow(0 0 8px #fbbf24)' }}>☀️</div>
                  <div style={{ fontFamily: 'var(--mono)', fontSize: '10px', color: 'var(--amber)', fontWeight: 600 }}>
                    d: CoH-S
                  </div>
                  <div style={{ fontSize: '18px', color: '#ffffff', fontWeight: 700 }}>➔</div>
                </div>

                {/* 2. TMC-2 (Mapping Optical 5m GSD) */}
                <div
                  onClick={() => setMmActiveSensor('tmc')}
                  style={{
                    position: 'relative',
                    border: mmActiveSensor === 'tmc' ? '2px solid var(--violet)' : '1px solid var(--panel-edge)',
                    borderRadius: '12px',
                    padding: '12px',
                    background: mmActiveSensor === 'tmc' ? 'rgba(138, 107, 255, 0.14)' : 'rgba(0, 0, 0, 0.65)',
                    cursor: 'pointer',
                    transition: 'all 0.25s',
                    boxShadow: mmActiveSensor === 'tmc' ? '0 0 22px rgba(168, 85, 247, 0.55)' : 'none',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <span style={{ fontWeight: 700, fontSize: '14px', color: 'var(--violet)' }}>TMC-2</span>
                    <span style={{ fontSize: '11px', fontFamily: 'var(--mono)', color: 'var(--violet)' }}>5.0m GSD</span>
                  </div>

                  <div style={{ position: 'relative', height: '180px', borderRadius: '8px', overflow: 'hidden' }}>
                    <img
                      src={sunAngleDeg < 45 ? '/assets/sun_angle_low.jpg' : '/assets/ch2_crater_source.jpg'}
                      alt="TMC"
                      style={{
                        width: '100%',
                        height: '100%',
                        objectFit: 'cover',
                        filter: `contrast(${1.05 + (90 - sunAngleDeg) * 0.005}) brightness(${0.72 + (sunAngleDeg / 90) * 0.42})`,
                        transition: 'filter 0.2s ease',
                      }}
                    />
                    <div
                      style={{
                        position: 'absolute',
                        top: `${Math.max(6, Math.round(55 - sunAngleDeg * 0.55))}%`,
                        left: '10px',
                        width: '32px',
                        height: '32px',
                        borderRadius: '50%',
                        background: 'radial-gradient(circle, #fff 15%, #fbbf24 65%, #f59e0b 100%)',
                        boxShadow: '0 0 16px #fbbf24, 0 0 30px rgba(251, 191, 36, 0.8)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: '16px',
                        transition: 'top 0.2s ease',
                      }}
                    >
                      ☀️
                    </div>
                    <svg style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', pointerEvents: 'none' }}>
                      <line
                        x1="26"
                        y1={`${Math.max(16, Math.round(65 - sunAngleDeg * 0.55))}%`}
                        x2="155"
                        y2="135"
                        stroke="#fbbf24"
                        strokeWidth="2.5"
                        strokeDasharray="4 3"
                        filter="drop-shadow(0 0 6px #fbbf24)"
                      />
                      <circle cx="155" cy="135" r="4.5" fill="#fbbf24" />
                    </svg>

                    {/* Dynamic Shadow Cast */}
                    <div
                      style={{
                        position: 'absolute',
                        inset: 0,
                        background: `linear-gradient(${180 - sunAngleDeg}deg, rgba(0,0,0,0) 40%, rgba(0,0,0,${(90 - sunAngleDeg) * 0.007}) 100%)`,
                        pointerEvents: 'none',
                      }}
                    />
                  </div>

                  <div style={{ textAlign: 'center', marginTop: '8px', fontFamily: 'var(--mono)', fontSize: '11.5px', color: '#ffffff', fontWeight: 700 }}>
                    Normal angle · Sun {sunAngleDeg}°
                  </div>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px' }}>
                  <div style={{ fontSize: '20px', filter: 'drop-shadow(0 0 8px #fbbf24)' }}>☀️</div>
                  <div style={{ fontFamily: 'var(--mono)', fontSize: '10px', color: 'var(--amber)', fontWeight: 600 }}>
                    b: CoH-S
                  </div>
                  <div style={{ fontSize: '18px', color: '#ffffff', fontWeight: 700 }}>➔</div>
                </div>

                {/* 3. IIRS (Hyperspectral 80m GSD) */}
                <div
                  onClick={() => setMmActiveSensor('iirs')}
                  style={{
                    position: 'relative',
                    border: mmActiveSensor === 'iirs' ? '2px solid var(--emerald)' : '1px solid var(--panel-edge)',
                    borderRadius: '12px',
                    padding: '12px',
                    background: mmActiveSensor === 'iirs' ? 'rgba(52, 211, 153, 0.12)' : 'rgba(0, 0, 0, 0.65)',
                    cursor: 'pointer',
                    transition: 'all 0.25s',
                    boxShadow: mmActiveSensor === 'iirs' ? '0 0 20px rgba(52, 211, 153, 0.45)' : 'none',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <span style={{ fontWeight: 700, fontSize: '14px', color: '#ffffff' }}>IIRS</span>
                    <span style={{ fontSize: '11px', fontFamily: 'var(--mono)', color: 'var(--emerald)' }}>80.0m GSD</span>
                  </div>

                  <div style={{ position: 'relative', height: '180px', borderRadius: '8px', overflow: 'hidden' }}>
                    <img
                      src="/assets/lro_crater_reference.jpg"
                      alt="IIRS"
                      style={{
                        width: '100%',
                        height: '100%',
                        objectFit: 'cover',
                        filter: `sepia(0.4) hue-rotate(90deg) contrast(${1.1 + (90 - sunAngleDeg) * 0.005}) brightness(${0.75 + (sunAngleDeg / 90) * 0.4})`,
                        transition: 'filter 0.2s ease',
                      }}
                    />
                    <svg style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', pointerEvents: 'none' }}>
                      <line x1="20" y1="20" x2="145" y2="110" stroke="#34d399" strokeWidth="2.5" strokeDasharray="4 3" filter="drop-shadow(0 0 6px #34d399)" />
                      <circle cx="145" cy="110" r="5" fill="#ffffff" stroke="#34d399" strokeWidth="2" />
                    </svg>

                    <div
                      style={{
                        position: 'absolute',
                        inset: 0,
                        background: `linear-gradient(${180 - sunAngleDeg}deg, rgba(0,0,0,0) 40%, rgba(0,0,0,${(90 - sunAngleDeg) * 0.006}) 100%)`,
                        pointerEvents: 'none',
                      }}
                    />
                  </div>

                  <div style={{ textAlign: 'center', marginTop: '8px', fontFamily: 'var(--mono)', fontSize: '11.5px', color: 'var(--emerald)', fontWeight: 600 }}>
                    Cross-Spectral · Sun {sunAngleDeg}°
                  </div>
                </div>
              </div>

              <div
                style={{
                  maxWidth: '460px',
                  margin: '16px auto 16px',
                  background: 'rgba(251, 191, 36, 0.08)',
                  border: '1.5px solid rgba(251, 191, 36, 0.65)',
                  borderRadius: '12px',
                  padding: '12px 18px',
                  boxShadow: '0 0 20px rgba(251, 191, 36, 0.15)',
                  textAlign: 'center',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', color: 'var(--amber)', fontWeight: 700, fontSize: '13px' }}>
                  <span>⚠️</span>
                  <span>Sub-pixel Accuracy</span>
                </div>
                <div style={{ color: 'var(--ink-dim)', fontSize: '12px', marginTop: '4px', fontFamily: 'var(--mono)' }}>
                  Invertible affine & homography model invariant to solar elevation angle and scale.
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '14px', marginTop: '16px' }}>
                <div style={{ border: '1px solid var(--panel-edge)', borderRadius: '12px', padding: '14px', background: 'rgba(0,0,0,0.45)' }}>
                  <div style={{ color: 'var(--amber)', fontWeight: 600, fontSize: '13px', marginBottom: '4px' }}>Solar Elevation Invariance</div>
                  <div style={{ color: 'var(--ink-dim)', fontSize: '12px', lineHeight: 1.5 }}>
                    Normalized cross-gradient matching eliminates shadows caused by varying sun angles (42° vs 65° vs 80°), mapping invariant topological crater boundaries.
                  </div>
                </div>

                <div style={{ border: '1px solid var(--panel-edge)', borderRadius: '12px', padding: '14px', background: 'rgba(0,0,0,0.45)' }}>
                  <div style={{ color: 'var(--violet)', fontWeight: 600, fontSize: '13px', marginBottom: '4px' }}>Multi-Scale Pyramidal Matching</div>
                  <div style={{ color: 'var(--ink-dim)', fontSize: '12px', lineHeight: 1.5 }}>
                    Bridges 10x-300x GSD scale differences (0.25m OHRC to 80m IIRS) using scale-space Gaussian pyramids and LoFTR coarse-to-fine dense keypoints.
                  </div>
                </div>

                <div style={{ border: '1px solid var(--panel-edge)', borderRadius: '12px', padding: '14px', background: 'rgba(0,0,0,0.45)' }}>
                  <div style={{ color: 'var(--emerald)', fontWeight: 600, fontSize: '13px', marginBottom: '4px' }}>Cross-Spectral Alignment</div>
                  <div style={{ color: 'var(--ink-dim)', fontSize: '12px', lineHeight: 1.5 }}>
                    Correlates panchromatic visible reflectance (TMC-2) with hyperspectral absorption bands (IIRS 0.8–5.0 µm) for unified mineralogical site mapping.
                  </div>
                </div>
              </div>

              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  marginTop: '18px',
                  paddingTop: '14px',
                  borderTop: '1px solid var(--panel-edge)',
                  fontFamily: 'var(--mono)',
                  fontSize: '11.5px',
                  color: 'var(--ink-dim)',
                  flexWrap: 'wrap',
                  gap: '12px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span style={{ color: '#ffffff', fontWeight: 600 }}>Simulate Sun Angle:</span>
                  <input
                    type="range"
                    min="15"
                    max="85"
                    value={sunAngleDeg}
                    onChange={(e) => setSunAngleDeg(Number(e.target.value))}
                    style={{ width: '130px', accentColor: 'var(--amber)' }}
                  />
                  <span style={{ color: 'var(--amber)', fontWeight: 700 }}>{sunAngleDeg}°</span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                  <span style={{ background: 'rgba(255, 255, 255, 0.08)', padding: '3px 8px', borderRadius: '6px', color: '#ffffff' }}>
                    110% Scale Invariance
                  </span>
                  <span style={{ background: 'rgba(255, 255, 255, 0.08)', padding: '3px 8px', borderRadius: '6px', color: '#ffffff' }}>
                    20% Solar Offset
                  </span>
                  <span style={{ color: 'var(--amber)', fontWeight: 700 }}>
                    11095 / 206 Points Correlated
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 4: ALIGNMENT & FOOTPRINT */}
        {activeTab === 'alignment' && (
          <div style={{ marginTop: '22px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div className="panel" style={{ padding: '20px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px', flexWrap: 'wrap', gap: '8px' }}>
                <div>
                  <div style={{ fontWeight: 700, fontSize: '17px', color: '#ffffff' }}>Sub-Pixel Registration Verification (Split Wipe)</div>
                  <div style={{ fontSize: '12.5px', color: 'var(--ink-dim)', fontFamily: 'var(--mono)' }}>
                    Wipe curtain to compare crater alignment • Residual &lt; 0.32 px
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '6px', background: 'rgba(0,0,0,0.5)', padding: '3px', borderRadius: '8px', border: '1px solid var(--panel-edge)' }}>
                  {['wipe', 'difference', 'checkerboard'].map((m) => (
                    <button
                      key={m}
                      onClick={() => setSplitMode(m)}
                      style={{
                        background: splitMode === m ? 'var(--violet)' : 'transparent',
                        color: splitMode === m ? '#ffffff' : 'var(--ink-dim)',
                        border: 'none',
                        padding: '4px 10px',
                        borderRadius: '6px',
                        fontSize: '11px',
                        fontFamily: 'var(--mono)',
                        cursor: 'pointer',
                        textTransform: 'capitalize',
                        transition: 'all 0.2s',
                      }}
                    >
                      {m}
                    </button>
                  ))}
                </div>
              </div>

              <div
                style={{
                  position: 'relative',
                  width: '100%',
                  height: '340px',
                  borderRadius: '10px',
                  overflow: 'hidden',
                  border: '1px solid var(--panel-edge)',
                  background: '#0a0716',
                  userSelect: 'none',
                }}
              >
                {/* Background Layer: LRO NAC Reference */}
                <img
                  src="/assets/lro_crater_reference.jpg"
                  alt="LRO NAC"
                  style={{
                    position: 'absolute',
                    inset: 0,
                    width: '100%',
                    height: '100%',
                    objectFit: 'cover',
                  }}
                />

                {/* Mode 1: Split Wipe */}
                {splitMode === 'wipe' && (
                  <>
                    <div
                      style={{
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        bottom: 0,
                        width: `${splitPos}%`,
                        overflow: 'hidden',
                        borderRight: '2.5px solid var(--amber)',
                        boxShadow: '0 0 16px var(--amber)',
                        zIndex: 4,
                      }}
                    >
                      <img
                        src="/assets/ch2_crater_source.jpg"
                        alt="TMC-2"
                        style={{
                          position: 'absolute',
                          top: 0,
                          left: 0,
                          height: '100%',
                          width: '100%',
                          objectFit: 'cover',
                        }}
                      />
                      <span className="tag" style={{ position: 'absolute', top: '10px', left: '10px', zIndex: 6 }}>
                        TMC-2 SOURCE
                      </span>
                      <div className="split-handle">↔</div>
                    </div>
                    <span className="tag" style={{ position: 'absolute', top: '10px', right: '10px', zIndex: 6 }}>
                      LRO NAC REFERENCE
                    </span>
                    <input
                      type="range"
                      min="0"
                      max="100"
                      value={splitPos}
                      onChange={(e) => setSplitPos(Number(e.target.value))}
                      className="split-range-input"
                      style={{ zIndex: 10 }}
                    />
                  </>
                )}

                {/* Mode 2: Difference Heatmap */}
                {splitMode === 'difference' && (
                  <>
                    <img
                      src="/assets/ch2_crater_source.jpg"
                      alt="TMC-2 Difference"
                      style={{
                        position: 'absolute',
                        inset: 0,
                        width: '100%',
                        height: '100%',
                        objectFit: 'cover',
                        mixBlendMode: 'difference',
                        filter: 'contrast(1.6) invert(0.1)',
                        zIndex: 4,
                      }}
                    />
                    <span className="tag" style={{ position: 'absolute', top: '10px', right: '10px', zIndex: 6, background: 'rgba(236,72,153,0.85)', color: '#ffffff' }}>
                      DIFFERENCE HEATMAP (ALIGNMENT RESIDUAL)
                    </span>
                  </>
                )}

                {/* Mode 3: Checkerboard Alternating Mask */}
                {splitMode === 'checkerboard' && (
                  <>
                    <div
                      style={{
                        position: 'absolute',
                        inset: 0,
                        zIndex: 4,
                        backgroundImage: `url('/assets/ch2_crater_source.jpg')`,
                        backgroundSize: 'cover',
                        backgroundPosition: 'center',
                        WebkitMaskImage: `
                          linear-gradient(45deg, #000 25%, transparent 25%),
                          linear-gradient(-45deg, #000 25%, transparent 25%),
                          linear-gradient(45deg, transparent 75%, #000 75%),
                          linear-gradient(-45deg, transparent 75%, #000 75%)
                        `,
                        WebkitMaskSize: '80px 80px',
                        WebkitMaskPosition: '0 0, 0 40px, 40px -40px, -40px 0px',
                        maskImage: `
                          linear-gradient(45deg, #000 25%, transparent 25%),
                          linear-gradient(-45deg, #000 25%, transparent 25%),
                          linear-gradient(45deg, transparent 75%, #000 75%),
                          linear-gradient(-45deg, transparent 75%, #000 75%)
                        `,
                        maskSize: '80px 80px',
                        maskPosition: '0 0, 0 40px, 40px -40px, -40px 0px',
                      }}
                    />
                    <div
                      style={{
                        position: 'absolute',
                        inset: 0,
                        zIndex: 5,
                        pointerEvents: 'none',
                        backgroundSize: '80px 80px',
                        backgroundImage: `
                          linear-gradient(to right, rgba(255, 255, 255, 0.15) 1px, transparent 1px),
                          linear-gradient(to bottom, rgba(255, 255, 255, 0.15) 1px, transparent 1px)
                        `,
                      }}
                    />
                    <span className="tag" style={{ position: 'absolute', top: '10px', left: '10px', zIndex: 6, background: 'rgba(138, 107, 255, 0.9)' }}>
                      CHECKERBOARD: TMC-2 ⛶ LRO NAC
                    </span>
                    <span className="tag" style={{ position: 'absolute', top: '10px', right: '10px', zIndex: 6 }}>
                      ALTERNATING 80px BLOCKS
                    </span>
                  </>
                )}
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '12px', fontFamily: 'var(--mono)', fontSize: '11px', color: 'var(--ink-dim)' }}>
                <span>Drag curtain horizontally across ridges and crater peaks</span>
                <span style={{ color: 'var(--amber)' }}>Curtain position: {splitPos}%</span>
              </div>
            </div>

            <div className="panel" style={{ padding: '20px' }}>
              <div style={{ marginBottom: '14px' }}>
                <div style={{ fontWeight: 700, fontSize: '17px', color: '#ffffff' }}>Lunar Geographic Footprint (19.2°N, 43.1°E)</div>
                <div style={{ fontSize: '12.5px', color: 'var(--ink-dim)', fontFamily: 'var(--mono)' }}>
                  Spatial intersection and 3x3 homography transformation coordinates
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '20px' }}>
                <div style={{ border: '1px solid var(--panel-edge)', borderRadius: '12px', padding: '16px', background: 'rgba(0,0,0,0.5)' }}>
                  <div style={{ fontSize: '12px', fontFamily: 'var(--mono)', color: 'var(--ink-dim)', marginBottom: '12px' }}>
                    Projective Homography Matrix (H_3x3)
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px', fontFamily: 'var(--mono)', fontSize: '12px', textAlign: 'center' }}>
                    {['0.9984', '-0.0124', '14.281', '0.0118', '0.9991', '-8.405', '0.0000', '0.0000', '1.0000'].map((val, idx) => (
                      <div key={idx} style={{ padding: '10px', background: 'rgba(255,255,255,0.06)', borderRadius: '6px', color: 'var(--amber)', fontWeight: 600 }}>
                        {val}
                      </div>
                    ))}
                  </div>
                </div>

                <div style={{ border: '1px solid var(--panel-edge)', borderRadius: '12px', padding: '16px', background: 'rgba(0,0,0,0.5)', fontFamily: 'var(--mono)', fontSize: '12px', color: 'var(--ink-dim)', display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: '8px' }}>
                  <div style={{ color: '#ffffff', fontWeight: 600, fontSize: '13px' }}>Coordinate Intersection:</div>
                  <div>• Chandrayaan-2 TMC-2: 19.45°N / 42.80°E</div>
                  <div>• LRO NAC Reference: 18.90°N / 43.40°E</div>
                  <div>• Overlap Area: 42.8 km² (100% Cropped)</div>
                  <div style={{ color: 'var(--violet)', fontWeight: 600, marginTop: '4px' }}>• Status: Memory mapped ~1.2 GB .img verified</div>
                </div>
              </div>
            </div>
          </div>
        )}

        <footer>
          <div className="tagline">registering the moon, one match at a time</div>
        </footer>
      </div>
    </div>
  );
}
