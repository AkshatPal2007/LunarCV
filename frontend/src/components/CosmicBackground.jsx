import React, { useEffect, useRef } from 'react';

export default function CosmicBackground() {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let animationFrameId;

    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    const handleResize = () => {
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    };
    window.addEventListener('resize', handleResize);

    // Particle field
    const numStars = 120;
    const stars = Array.from({ length: numStars }, () => ({
      x: Math.random() * width,
      y: Math.random() * height,
      size: Math.random() * 2 + 0.5,
      alpha: Math.random(),
      speed: Math.random() * 0.02 + 0.005,
      direction: Math.random() * Math.PI * 2,
    }));

    // Meteors
    const numMeteors = 2;
    const meteors = Array.from({ length: numMeteors }, () => ({
      x: Math.random() * width,
      y: Math.random() * height * 0.5,
      len: Math.random() * 80 + 40,
      speed: Math.random() * 4 + 2,
      alpha: 0,
      active: false,
    }));

    const render = () => {
      ctx.clearRect(0, 0, width, height);

      // Draw faint twinkling stars
      stars.forEach((star) => {
        star.alpha += (Math.random() - 0.5) * 0.03;
        if (star.alpha < 0.1) star.alpha = 0.1;
        if (star.alpha > 0.9) star.alpha = 0.9;

        ctx.beginPath();
        ctx.arc(star.x, star.y, star.size, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255, 230, 200, ${star.alpha})`;
        ctx.shadowBlur = star.size * 4;
        ctx.shadowColor = '#fbbf24';
        ctx.fill();
        ctx.shadowBlur = 0;
      });

      // Meteors
      meteors.forEach((m) => {
        if (!m.active && Math.random() < 0.005) {
          m.active = true;
          m.x = Math.random() * width * 0.8;
          m.y = Math.random() * height * 0.4;
          m.alpha = 1;
        }

        if (m.active) {
          ctx.beginPath();
          const grad = ctx.createLinearGradient(m.x, m.y, m.x - m.len, m.y + m.len * 0.6);
          grad.addColorStop(0, `rgba(251, 191, 36, ${m.alpha})`);
          grad.addColorStop(1, 'rgba(251, 191, 36, 0)');

          ctx.strokeStyle = grad;
          ctx.lineWidth = 1.5;
          ctx.moveTo(m.x, m.y);
          ctx.lineTo(m.x - m.len, m.y + m.len * 0.6);
          ctx.stroke();

          m.x += m.speed * 2;
          m.y += m.speed * 1.2;
          m.alpha -= 0.015;

          if (m.alpha <= 0) {
            m.active = false;
          }
        }
      });

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  return (
    <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
      {/* Background Cosmic Image */}
      <img
        src="/assets/cosmic_bg.png"
        alt="Cosmic Background"
        className="absolute inset-0 w-full h-full object-cover opacity-60 mix-blend-screen scale-105 filter blur-[0.5px]"
      />
      {/* Radial overlay glow */}
      <div className="absolute inset-0 bg-radial-vignette bg-gradient-to-b from-[#070814]/40 via-transparent to-[#070814]/90" />
      {/* Canvas for animated starfield and meteors */}
      <canvas ref={canvasRef} className="absolute inset-0 w-full h-full" />
    </div>
  );
}
