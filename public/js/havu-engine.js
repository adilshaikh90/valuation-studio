/**
 * Valuation Studio — HAVU 144Hz Interactive Physics Engine
 * Featuring:
 * 1. Interactive Dot-Matrix / LED Canvas with spring physics and cursor ripples.
 * 2. 144Hz Hardware-accelerated smooth custom magnetic cursor.
 * 3. Retro-futuristic pixel glyph micro-interactions.
 * 4. Real-time DCF valuation sandbox with smooth numerical interpolation.
 */

document.addEventListener('DOMContentLoaded', () => {
  initHavuCursor();
  initDotMatrixCanvas();
  initPixelGlyphs();
  initHavuSandbox();
  initTrendingChips();
});

// ── 1. 144Hz Custom Smooth Magnetic Cursor ──────────────────────────────────
function initHavuCursor() {
  const dot = document.createElement('div');
  dot.className = 'hv-cursor-dot';
  const follower = document.createElement('div');
  follower.className = 'hv-cursor-follower';
  document.body.appendChild(dot);
  document.body.appendChild(follower);

  let mouseX = window.innerWidth / 2;
  let mouseY = window.innerHeight / 2;
  let followerX = mouseX;
  let followerY = mouseY;

  window.addEventListener('mousemove', (e) => {
    mouseX = e.clientX;
    mouseY = e.clientY;
    dot.style.transform = `translate3d(${mouseX}px, ${mouseY}px, 0)`;
  });

  // Smooth lerp loop running at native display refresh rate (144Hz/120Hz/60Hz)
  function renderCursor() {
    followerX += (mouseX - followerX) * 0.18;
    followerY += (mouseY - followerY) * 0.18;
    follower.style.transform = `translate3d(${followerX}px, ${followerY}px, 0)`;
    requestAnimationFrame(renderCursor);
  }
  requestAnimationFrame(renderCursor);

  // Expand follower on interactive elements
  const interactives = 'a, button, input, select, textarea, .hv-pixel-glyph, .hv-trend-pill, .hv-module-card, .stat-card, .quick-link-item, .sidebar-item, .tab-btn, .badge';
  document.addEventListener('mouseover', (e) => {
    if (e.target.closest(interactives)) {
      document.body.classList.add('hv-cursor-active');
    }
  });
  document.addEventListener('mouseout', (e) => {
    if (e.target.closest(interactives)) {
      document.body.classList.remove('hv-cursor-active');
    }
  });
}

// ── 2. Interactive Dot-Matrix / LED Grid Canvas ─────────────────────────────
function initDotMatrixCanvas() {
  const canvas = document.getElementById('hvDotMatrixCanvas');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  let width = (canvas.width = canvas.parentElement.clientWidth);
  let height = (canvas.height = canvas.parentElement.clientHeight);

  window.addEventListener('resize', () => {
    if (!canvas.parentElement) return;
    width = canvas.width = canvas.parentElement.clientWidth;
    height = canvas.height = canvas.parentElement.clientHeight;
    setupMatrix();
  });

  const spacing = 12; // distance between dot centers
  let dots = [];

  // Mouse interaction coordinates
  let mouse = { x: -1000, y: -1000, radius: 85 };

  canvas.addEventListener('mousemove', (e) => {
    const rect = canvas.getBoundingClientRect();
    mouse.x = e.clientX - rect.left;
    mouse.y = e.clientY - rect.top;
  });

  canvas.addEventListener('mouseleave', () => {
    mouse.x = -1000;
    mouse.y = -1000;
  });

  // Bitmap representation of "VALUATION STUDIO" in 5x7 dot font
  function setupMatrix() {
    dots = [];
    const cols = Math.floor(width / spacing);
    const rows = Math.floor(height / spacing);
    const startX = (width - cols * spacing) / 2;
    const startY = (height - rows * spacing) / 2;

    // Rasterize target text into an offscreen canvas to sample pixels
    const offCanvas = document.createElement('canvas');
    offCanvas.width = cols;
    offCanvas.height = rows;
    const offCtx = offCanvas.getContext('2d');

    offCtx.fillStyle = '#000000';
    offCtx.fillRect(0, 0, cols, rows);
    offCtx.fillStyle = '#ffffff';
    offCtx.font = 'bold 9px monospace';
    offCtx.textAlign = 'center';
    offCtx.textBaseline = 'middle';

    // Text to render in LED phosphor
    const displayText = width > 700 ? 'VALUATION STUDIO' : 'V-STUDIO';
    offCtx.fillText(displayText, cols / 2, rows / 2);

    const imgData = offCtx.getImageData(0, 0, cols, rows).data;

    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const idx = (r * cols + c) * 4;
        const isLetter = imgData[idx] > 128; // Bright pixel in offscreen text

        const originX = startX + c * spacing + spacing / 2;
        const originY = startY + r * spacing + spacing / 2;

        dots.push({
          originX,
          originY,
          x: originX,
          y: originY,
          vx: 0,
          vy: 0,
          isLetter,
          baseRadius: isLetter ? 2.5 : 1.2,
          radius: isLetter ? 2.5 : 1.2,
          color: isLetter ? 'rgba(255, 255, 255, 0.95)' : 'rgba(255, 255, 255, 0.12)'
        });
      }
    }
  }

  setupMatrix();

  // 144Hz Physics Animation Loop
  function render() {
    ctx.clearRect(0, 0, width, height);

    for (let i = 0; i < dots.length; i++) {
      const d = dots[i];

      // Mouse distance
      const dx = mouse.x - d.x;
      const dy = mouse.y - d.y;
      const dist = Math.sqrt(dx * dx + dy * dy);

      // Repulsion force
      if (dist < mouse.radius) {
        const force = (1 - dist / mouse.radius) * 12;
        const angle = Math.atan2(dy, dx);
        d.vx -= Math.cos(angle) * force;
        d.vy -= Math.sin(angle) * force;
      }

      // Spring force returning to origin
      const returnForceX = (d.originX - d.x) * 0.14;
      const returnForceY = (d.originY - d.y) * 0.14;

      d.vx = (d.vx + returnForceX) * 0.82; // 82% damping
      d.vy = (d.vy + returnForceY) * 0.82;

      d.x += d.vx;
      d.y += d.vy;

      // Glow intensity when near cursor or active
      let glow = 0;
      if (dist < mouse.radius * 1.5) {
        glow = (1 - dist / (mouse.radius * 1.5));
      }

      ctx.beginPath();
      ctx.arc(d.x, d.y, d.radius + glow * 1.5, 0, Math.PI * 2);

      if (d.isLetter) {
        ctx.fillStyle = glow > 0.2 ? '#f59e0b' : '#ffffff';
        if (glow > 0.3) {
          ctx.shadowColor = '#f59e0b';
          ctx.shadowBlur = 8;
        } else {
          ctx.shadowBlur = 0;
        }
      } else {
        const alpha = Math.min(1, 0.12 + glow * 0.7);
        ctx.fillStyle = glow > 0.3 ? `rgba(245, 158, 11, ${alpha})` : `rgba(255, 255, 255, ${alpha})`;
        ctx.shadowBlur = 0;
      }

      ctx.fill();
    }

    requestAnimationFrame(render);
  }

  requestAnimationFrame(render);
}

// ── 3. Retro-Futuristic Pixel Glyphs ─────────────────────────────────────────
function initPixelGlyphs() {
  const glyphs = document.querySelectorAll('.hv-pixel-glyph');
  glyphs.forEach((g) => {
    g.addEventListener('click', () => {
      g.style.transition = 'transform 0.4s cubic-bezier(0.34, 1.56, 0.64, 1)';
      g.style.transform = 'translateY(-14px) scale(1.4) rotate(15deg)';
      setTimeout(() => {
        g.style.transform = 'translateY(0) scale(1) rotate(0deg)';
      }, 400);
    });
  });
}

// ── 4. Interactive Live DCF Sandbox ─────────────────────────────────────────
function initHavuSandbox() {
  const waccSlider = document.getElementById('hvWaccSlider');
  const growthSlider = document.getElementById('hvGrowthSlider');
  const waccDisplay = document.getElementById('hvWaccDisplay');
  const growthDisplay = document.getElementById('hvGrowthDisplay');
  const priceDisplay = document.getElementById('hvPriceDisplay');
  const upsideBadge = document.getElementById('hvUpsideBadge');
  const evDisplay = document.getElementById('hvEvDisplay');
  const eqDisplay = document.getElementById('hvEqDisplay');

  if (!waccSlider || !growthSlider) return;

  // Base financial assumptions (Admiral Group / Mega-Cap Insurer Benchmark)
  const baseFcf = 850; // £850M FCF
  const marketPrice = 38.18; // £38.18 (3,818p)
  const shares = 301.5; // 301.5M shares
  const netDebt = 180; // £180M net debt

  function compute() {
    const wacc = parseFloat(waccSlider.value) / 100;
    const g = parseFloat(growthSlider.value) / 100;

    waccDisplay.textContent = (wacc * 100).toFixed(1) + '%';
    growthDisplay.textContent = (g * 100).toFixed(1) + '%';

    if (wacc <= g) {
      priceDisplay.textContent = 'ERR';
      upsideBadge.textContent = 'WACC must exceed growth';
      return;
    }

    // 5-year projections
    let sumPv = 0;
    let cf = baseFcf;
    for (let i = 1; i <= 5; i++) {
      cf *= 1 + 0.05 * (1 - i * 0.08);
      const df = 1 / Math.pow(1 + wacc, i - 0.5);
      sumPv += cf * df;
    }

    const tv = (cf * (1 + g)) / (wacc - g);
    const pvTv = tv / Math.pow(1 + wacc, 5);
    const ev = sumPv + pvTv;
    const eq = ev - netDebt;
    const impliedPrice = eq / shares;

    const upside = ((impliedPrice - marketPrice) / marketPrice) * 100;

    priceDisplay.textContent = '£' + impliedPrice.toFixed(2);
    evDisplay.textContent = '£' + (ev / 1000).toFixed(2) + 'B';
    eqDisplay.textContent = '£' + (eq / 1000).toFixed(2) + 'B';

    if (upside >= 0) {
      upsideBadge.className = 'hv-upside-badge green';
      upsideBadge.textContent = `+${upside.toFixed(1)}% Implied Upside vs £${marketPrice.toFixed(2)}`;
    } else {
      upsideBadge.className = 'hv-upside-badge red';
      upsideBadge.textContent = `${upside.toFixed(1)}% Implied Downside vs £${marketPrice.toFixed(2)}`;
    }
  }

  waccSlider.addEventListener('input', compute);
  growthSlider.addEventListener('input', compute);
  compute();
}

// ── 5. Trending Ticker Chips ────────────────────────────────────────────────
function initTrendingChips() {
  const input = document.querySelector('.hv-cmd-input');
  const pills = document.querySelectorAll('.hv-trend-pill');
  if (!input) return;

  pills.forEach((p) => {
    p.addEventListener('click', () => {
      const ticker = p.getAttribute('data-ticker');
      if (ticker) {
        input.value = ticker;
        input.focus();
      }
    });
  });
}
