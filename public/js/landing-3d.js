/**
 * Valuation Studio - Interactive 3D & Particle Engine
 * 60fps 3D canvas projection, interactive gyroscope tilt physics,
 * spotlight specular highlights, and real-time valuation simulation.
 */

document.addEventListener('DOMContentLoaded', () => {
  init3DCanvas();
  init3DTerminalTilt();
  init3DCardSpotlight();
  initValuationSandbox();
  initTickerChips();
});

// ── 1. Interactive 3D Canvas Background ──────────────────────────────────────
function init3DCanvas() {
  const canvas = document.getElementById('matrix3dCanvas');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  let width = (canvas.width = window.innerWidth);
  let height = (canvas.height = window.innerHeight);

  window.addEventListener('resize', () => {
    width = canvas.width = window.innerWidth;
    height = canvas.height = window.innerHeight;
  });

  // Mouse tracking
  let mouseX = width / 2;
  let mouseY = height / 2;
  let targetMouseX = width / 2;
  let targetMouseY = height / 2;

  window.addEventListener('mousemove', (e) => {
    targetMouseX = e.clientX;
    targetMouseY = e.clientY;
  });

  // 3D Particles grid
  const particles = [];
  const count = Math.min(100, Math.floor((width * height) / 14000));
  const fov = 350;

  for (let i = 0; i < count; i++) {
    particles.push({
      x: (Math.random() - 0.5) * width * 1.5,
      y: (Math.random() - 0.5) * height * 1.5,
      z: Math.random() * 800 + 50,
      vx: (Math.random() - 0.5) * 0.4,
      vy: (Math.random() - 0.5) * 0.4,
      vz: -(Math.random() * 0.8 + 0.2),
      radius: Math.random() * 2 + 1,
      color: Math.random() > 0.4 ? 'rgba(245, 158, 11, ' : 'rgba(56, 189, 248, '
    });
  }

  function render() {
    // Smooth mouse lerp
    mouseX += (targetMouseX - mouseX) * 0.05;
    mouseY += (targetMouseY - mouseY) * 0.05;

    const angleY = ((mouseX - width / 2) / width) * 0.35;
    const angleX = ((mouseY - height / 2) / height) * 0.35;

    ctx.clearRect(0, 0, width, height);

    const projected = [];

    // Project and update particles
    for (let i = 0; i < particles.length; i++) {
      const p = particles[i];

      // Move particle forward in 3D depth
      p.z += p.vz;
      p.x += p.vx;
      p.y += p.vy;

      // Wrap around
      if (p.z < 20) p.z = 800;
      if (p.x < -width) p.x = width;
      if (p.x > width) p.x = -width;
      if (p.y < -height) p.y = height;
      if (p.y > height) p.y = -height;

      // 3D Rotation
      const cosY = Math.cos(angleY);
      const sinY = Math.sin(angleY);
      const cosX = Math.cos(angleX);
      const sinX = Math.sin(angleX);

      // Rotate around Y
      let x1 = p.x * cosY - p.z * sinY;
      let z1 = p.z * cosY + p.x * sinY;

      // Rotate around X
      let y1 = p.y * cosX - z1 * sinX;
      let z2 = z1 * cosX + p.y * sinX;

      // Perspective projection
      if (z2 <= -fov + 10) continue;
      const scale = fov / (fov + z2);
      const projX = x1 * scale + width / 2;
      const projY = y1 * scale + height / 2;

      // Alpha based on depth
      const alpha = Math.max(0, Math.min(1, 1 - z2 / 900));

      projected.push({
        x: projX,
        y: projY,
        scale,
        alpha,
        color: p.color,
        radius: p.radius * scale
      });

      // Draw particle
      ctx.beginPath();
      ctx.arc(projX, projY, Math.max(0.5, p.radius * scale), 0, Math.PI * 2);
      ctx.fillStyle = `${p.color}${alpha * 0.8})`;
      ctx.shadowColor = p.color.includes('245') ? '#f59e0b' : '#38bdf8';
      ctx.shadowBlur = 6 * scale;
      ctx.fill();
    }

    // Connect nearby projected points with subtle glowing lines
    ctx.shadowBlur = 0;
    const maxDist = 110;
    for (let i = 0; i < projected.length; i++) {
      for (let j = i + 1; j < projected.length; j++) {
        const p1 = projected[i];
        const p2 = projected[j];
        const dx = p1.x - p2.x;
        const dy = p1.y - p2.y;
        const dist = Math.sqrt(dx * dx + dy * dy);

        if (dist < maxDist) {
          const lineAlpha = (1 - dist / maxDist) * p1.alpha * p2.alpha * 0.25;
          ctx.beginPath();
          ctx.moveTo(p1.x, p1.y);
          ctx.lineTo(p2.x, p2.y);
          ctx.strokeStyle = `rgba(245, 158, 11, ${lineAlpha})`;
          ctx.lineWidth = 0.75;
          ctx.stroke();
        }
      }
    }

    requestAnimationFrame(render);
  }

  requestAnimationFrame(render);
}

// ── 2. Interactive 3D Terminal Tilt Physics ──────────────────────────────────
function init3DTerminalTilt() {
  const card = document.querySelector('.terminal-3d-card');
  const glare = document.querySelector('.terminal-glare');
  if (!card) return;

  const maxTilt = 8; // degrees
  let isHovered = false;

  card.addEventListener('mouseenter', () => {
    isHovered = true;
  });

  card.addEventListener('mousemove', (e) => {
    const rect = card.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const centerX = rect.width / 2;
    const centerY = rect.height / 2;

    const rotX = -((y - centerY) / centerY) * maxTilt;
    const rotY = ((x - centerX) / centerX) * maxTilt;

    card.style.transform = `perspective(1200px) rotateX(${rotX.toFixed(2)}deg) rotateY(${rotY.toFixed(2)}deg) scale3d(1.015, 1.015, 1.015)`;

    if (glare) {
      const glareX = (x / rect.width) * 100;
      const glareY = (y / rect.height) * 100;
      glare.style.background = `radial-gradient(circle at ${glareX}% ${glareY}%, rgba(255, 255, 255, 0.12) 0%, transparent 65%)`;
    }
  });

  card.addEventListener('mouseleave', () => {
    isHovered = false;
    card.style.transform = 'perspective(1200px) rotateX(2deg) rotateY(-1deg) scale3d(1, 1, 1)';
    if (glare) {
      glare.style.background = 'radial-gradient(circle at 50% 50%, rgba(255, 255, 255, 0.05) 0%, transparent 60%)';
    }
  });

  // Default subtle natural tilt
  card.style.transform = 'perspective(1200px) rotateX(2deg) rotateY(-1deg)';
}

// ── 3. 3D Card Spotlight & Cursor Parallax ───────────────────────────────────
function init3DCardSpotlight() {
  const cards = document.querySelectorAll('.feature-3d-card');
  if (!cards.length) return;

  cards.forEach((card) => {
    card.addEventListener('mousemove', (e) => {
      const rect = card.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      card.style.setProperty('--mouse-x', `${x}px`);
      card.style.setProperty('--mouse-y', `${y}px`);

      // Gentle 3D tilt
      const centerX = rect.width / 2;
      const centerY = rect.height / 2;
      const rotX = -((y - centerY) / centerY) * 4;
      const rotY = ((x - centerX) / centerX) * 4;

      card.style.transform = `perspective(800px) rotateX(${rotX.toFixed(2)}deg) rotateY(${rotY.toFixed(2)}deg) translateY(-5px)`;
    });

    card.addEventListener('mouseleave', () => {
      card.style.transform = 'perspective(800px) rotateX(0deg) rotateY(0deg) translateY(0)';
    });
  });
}

// ── 4. Live Valuation Simulator Sandbox ──────────────────────────────────────
function initValuationSandbox() {
  const waccSlider = document.getElementById('sandboxWacc');
  const growthSlider = document.getElementById('sandboxGrowth');
  const waccValLabel = document.getElementById('waccValLabel');
  const growthValLabel = document.getElementById('growthValLabel');
  const outputPrice = document.getElementById('sandboxOutputPrice');
  const outputUpside = document.getElementById('sandboxOutputUpside');
  const outEv = document.getElementById('sandboxOutEv');
  const outEq = document.getElementById('sandboxOutEq');

  if (!waccSlider || !growthSlider) return;

  // Baseline financials for Apple Inc. (example sandbox model)
  const baseFcf = 108500; // $108.5B FCF
  const marketPrice = 224.5;
  const sharesOutstanding = 15200; // 15.2B shares
  const netDebt = 48000; // $48.0B Net Debt

  function recalculate() {
    const wacc = parseFloat(waccSlider.value) / 100;
    const g = parseFloat(growthSlider.value) / 100;

    waccValLabel.textContent = (wacc * 100).toFixed(1) + '%';
    growthValLabel.textContent = (g * 100).toFixed(1) + '%';

    // Guard against singularity
    if (wacc <= g) {
      outputPrice.textContent = 'N/A';
      outputUpside.textContent = 'WACC must exceed Terminal Growth';
      return;
    }

    // 5-year forecast with decay toward terminal g
    let pvSum = 0;
    let cf = baseFcf;
    for (let i = 1; i <= 5; i++) {
      cf *= 1 + 0.08 * (1 - i * 0.1);
      const discountFactor = 1 / Math.pow(1 + wacc, i - 0.5);
      pvSum += cf * discountFactor;
    }

    // Terminal Value
    const tv = (cf * (1 + g)) / (wacc - g);
    const pvTv = tv / Math.pow(1 + wacc, 5);
    const enterpriseValue = pvSum + pvTv;
    const equityValue = enterpriseValue - netDebt;
    const impliedSharePrice = equityValue / sharesOutstanding;

    const upsidePct = ((impliedSharePrice - marketPrice) / marketPrice) * 100;

    // Update UI
    outputPrice.textContent = '$' + impliedSharePrice.toFixed(2);
    outEv.textContent = '$' + (enterpriseValue / 1000).toFixed(1) + 'B';
    outEq.textContent = '$' + (equityValue / 1000).toFixed(1) + 'B';

    if (upsidePct >= 0) {
      outputUpside.className = 'output-upside-badge green';
      outputUpside.textContent = `+${upsidePct.toFixed(1)}% Implied Upside vs $${marketPrice.toFixed(2)}`;
    } else {
      outputUpside.className = 'output-upside-badge red';
      outputUpside.textContent = `${upsidePct.toFixed(1)}% Implied Downside vs $${marketPrice.toFixed(2)}`;
    }
  }

  waccSlider.addEventListener('input', recalculate);
  growthSlider.addEventListener('input', recalculate);
  recalculate();
}

// ── 5. Quick Ticker Chips & Marquee Selection ────────────────────────────────
function initTickerChips() {
  const input = document.querySelector('#global-search input');
  const chips = document.querySelectorAll('.ticker-chip, .marquee-item');
  if (!input) return;

  chips.forEach((chip) => {
    chip.addEventListener('click', () => {
      const ticker = chip.getAttribute('data-ticker');
      if (ticker) {
        input.value = ticker;
        input.focus();
        // Subtle highlight pulse
        input.parentElement.style.borderColor = '#f59e0b';
        input.parentElement.style.boxShadow = '0 0 25px rgba(245, 158, 11, 0.4)';
        setTimeout(() => {
          input.parentElement.style.borderColor = '';
          input.parentElement.style.boxShadow = '';
        }, 800);
      }
    });
  });
}
