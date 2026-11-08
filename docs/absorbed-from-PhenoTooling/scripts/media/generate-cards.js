#!/usr/bin/env node
/**
 * Static PNG card generator for projects without real screenshots.
 *
 * Uses Playwright to render the card-composer canvas in a headless browser
 * and save each generated card as a PNG file.
 *
 * Usage:
 *   node scripts/media/generate-cards.js
 *
 * Output:
 *   public/projects/<slug>/card.png  (for projects without existing images)
 *
 * Prerequisites:
 *   npm install (Playwright is already a devDependency)
 *   npx playwright install chromium
 *
 * Card dimensions: 800 x 450 px (matches CARD_WIDTH x CARD_HEIGHT in card-composer.js)
 */

import { chromium } from 'playwright';
import { readFileSync, existsSync, mkdirSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, '..', '..');

/* ─── Projects that already have real images ─── */

const SKIP = new Set([
  'netweave', 'witf', 'gmk-arch', 'dss-cipher',
  'substrate', 'phenotype-omlx', 'omniroute', 'sharecli',
]);

/* ─── Project metadata (subset needed for card generation) ─── */

const PROJECTS = [
  { slug: 'agentapi-plusplus', title: 'AgentAPI++', technologies: ['TypeScript'], category: 'developer-tools' },
  { slug: 'byteport', title: 'BytePort', technologies: ['Go', 'AWS', 'Deployment'], category: 'cloud' },
  { slug: 'cliproxyapi-plusplus', title: 'CLIProxyAPI++', technologies: ['TypeScript'], category: 'developer-tools' },
  { slug: 'forgecode', title: 'ForgeCode', technologies: ['TypeScript'], category: 'developer-tools' },
  { slug: 'frostify', title: 'Frostify', technologies: ['TypeScript', 'Design'], category: 'design' },
  { slug: 'mcpforge', title: 'MCPForge', technologies: ['TypeScript'], category: 'developer-tools' },
  { slug: 'tracera', title: 'Tracera', technologies: ['Rust', 'Traceability', 'Audit'], category: 'developer-tools' },
];

const CARD_WIDTH = 800;
const CARD_HEIGHT = 450;

/* ─── Card rendering function (runs in browser context) ─── */

function getRendererSource() {
  // Read the card-icons and card-composer source to extract the pure rendering logic
  // We inline the relevant functions since the browser context can't use ES module imports
  return `
    <script>
    // ── Inlined card-icons helpers ──
    function roundRect(ctx, x, y, w, h, r) {
      ctx.beginPath();
      ctx.moveTo(x + r, y);
      ctx.lineTo(x + w - r, y);
      ctx.arcTo(x + w, y, x + w, y + r, r);
      ctx.lineTo(x + w, y + h - r);
      ctx.arcTo(x + w, y + h, x + w - r, y + h, r);
      ctx.lineTo(x + r, y + h);
      ctx.arcTo(x, y + h, x, y + h - r, r);
      ctx.lineTo(x, y + r);
      ctx.arcTo(x, y, x + r, y, r);
      ctx.closePath();
    }

    function hexToRgba(hex, alpha) {
      const h = hex.replace('#', '');
      const r = parseInt(h.substring(0, 2), 16);
      const g = parseInt(h.substring(2, 4), 16);
      const b = parseInt(h.substring(4, 6), 16);
      return 'rgba(' + r + ',' + g + ',' + b + ',' + alpha + ')';
    }

    // ── Category icon drawing (inlined from card-icons.js) ──
    const CATEGORY_ICONS = {
      'ai-infrastructure': 'router', 'ai-ml': 'neural',
      'developer-tools': 'gears', 'cloud': 'cloud',
      'systems': 'terminal', 'simulation': 'graph',
      'design': 'palette', 'physical-product': 'cube',
    };

    function drawCategoryIcon(ctx, category, accent) {
      const iconType = CATEGORY_ICONS[category] || 'gears';
      ctx.strokeStyle = accent; ctx.fillStyle = 'none';
      ctx.lineWidth = 2.2; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
      ctx.globalAlpha = 0.35;
      switch (iconType) {
        case 'router': drawRouterIcon(ctx, accent); break;
        case 'neural': drawNeuralIcon(ctx, accent); break;
        case 'terminal': drawTerminalIcon(ctx, accent); break;
        case 'gears': drawGearsIcon(ctx, accent); break;
        case 'cloud': drawCloudIcon(ctx, accent); break;
        case 'graph': drawGraphIcon(ctx, accent); break;
        case 'palette': drawPaletteIcon(ctx, accent); break;
        case 'cube': drawCubeIcon(ctx, accent); break;
        default: drawGearsIcon(ctx, accent);
      }
    }

    function drawRouterIcon(ctx, accent) {
      roundRect(ctx,-28,-18,56,36,6); ctx.stroke();
      roundRect(ctx,-52,-10,20,20,4); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(-32,0); ctx.lineTo(-28,0); ctx.stroke();
      roundRect(ctx,32,-10,20,20,4); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(28,0); ctx.lineTo(32,0); ctx.stroke();
      roundRect(ctx,-10,-42,20,20,4); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(0,-18); ctx.lineTo(0,-22); ctx.stroke();
      roundRect(ctx,-10,22,20,20,4); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(0,18); ctx.lineTo(0,22); ctx.stroke();
      ctx.fillStyle=accent; ctx.globalAlpha=0.4;
      ctx.beginPath(); ctx.arc(0,0,3,0,Math.PI*2); ctx.fill();
    }

    function drawNeuralIcon(ctx, accent) {
      const nodes=[{x:0,y:-30},{x:-26,y:-10},{x:26,y:-10},{x:-16,y:16},{x:16,y:16},{x:0,y:34}];
      ctx.globalAlpha=0.2;
      for(let i=0;i<nodes.length;i++)for(let j=i+1;j<nodes.length;j++){
        if(Math.abs(i-j)<=2||(i===0&&j===5)){ctx.beginPath();ctx.moveTo(nodes[i].x,nodes[i].y);ctx.lineTo(nodes[j].x,nodes[j].y);ctx.stroke();}
      }
      ctx.globalAlpha=0.45;
      for(const n of nodes){ctx.fillStyle=accent;ctx.beginPath();ctx.arc(n.x,n.y,5,0,Math.PI*2);ctx.fill();ctx.stroke();}
    }

    function drawTerminalIcon(ctx, accent) {
      roundRect(ctx,-34,-26,68,48,6); ctx.stroke();
      ctx.fillStyle=hexToRgba(accent,0.06); roundRect(ctx,-28,-21,56,36,3); ctx.fill(); ctx.stroke();
      ctx.beginPath();ctx.moveTo(-10,22);ctx.lineTo(10,22);ctx.moveTo(0,22);ctx.lineTo(0,30);ctx.moveTo(-16,30);ctx.lineTo(16,30);ctx.stroke();
      ctx.fillStyle=accent;ctx.globalAlpha=0.6;ctx.fillRect(-20,-12,2,14);ctx.font='11px monospace';ctx.fillText('$',-14,-2);
    }

    function drawGearsIcon(ctx, accent) {
      drawGear(ctx,-14,4,22,8,8,accent); drawGear(ctx,14,-4,16,6,6,accent);
    }
    function drawGear(ctx,cx,cy,outerR,innerR,teeth,accent){
      ctx.beginPath();const step=(Math.PI*2)/teeth;
      for(let i=0;i<teeth;i++){const a1=i*step,a2=a1+step*0.35,a3=a1+step*0.5,a4=a1+step*0.85;
        if(i===0)ctx.moveTo(cx+Math.cos(a1)*outerR,cy+Math.sin(a1)*outerR);
        ctx.lineTo(cx+Math.cos(a2)*outerR,cy+Math.sin(a2)*outerR);ctx.lineTo(cx+Math.cos(a3)*innerR,cy+Math.sin(a3)*innerR);ctx.lineTo(cx+Math.cos(a4)*innerR,cy+Math.sin(a4)*innerR);
      }ctx.closePath();ctx.stroke();ctx.beginPath();ctx.arc(cx,cy,innerR*0.4,0,Math.PI*2);ctx.stroke();
    }

    function drawCloudIcon(ctx, accent) {
      ctx.beginPath();ctx.arc(-12,6,14,Math.PI*0.8,Math.PI*1.85);ctx.arc(8,-2,18,Math.PI*1.15,Math.PI*0.15);ctx.arc(24,6,12,Math.PI*1.4,Math.PI*0.4);ctx.lineTo(-24,18);ctx.lineTo(-24,14);ctx.closePath();ctx.stroke();
      ctx.beginPath();ctx.moveTo(0,14);ctx.lineTo(0,-6);ctx.moveTo(-6,0);ctx.lineTo(0,-6);ctx.lineTo(6,0);ctx.stroke();
    }

    function drawGraphIcon(ctx, accent) {
      const pts=[{x:-28,y:14},{x:-10,y:-18},{x:12,y:6},{x:28,y:-14},{x:20,y:20}];
      ctx.globalAlpha=0.25;const edges=[[0,1],[1,2],[2,3],[2,4],[0,2]];
      for(const[a,b]of edges){ctx.beginPath();ctx.moveTo(pts[a].x,pts[a].y);ctx.lineTo(pts[b].x,pts[b].y);ctx.stroke();}
      ctx.globalAlpha=0.45;for(const p of pts){ctx.fillStyle=accent;ctx.beginPath();ctx.arc(p.x,p.y,4,0,Math.PI*2);ctx.fill();}
    }

    function drawPaletteIcon(ctx, accent) {
      const swatches=['#e8734a','#3178c6','#00add8','#4caf50','#e91e63'],angles=[-0.6,-0.15,0.3,0.75,1.2],radius=24;
      ctx.lineWidth=1.5;for(let i=0;i<swatches.length;i++){ctx.fillStyle=hexToRgba(swatches[i],0.5);ctx.globalAlpha=0.4;ctx.beginPath();ctx.arc(Math.cos(angles[i])*radius,Math.sin(angles[i])*radius-4,7,0,Math.PI*2);ctx.fill();ctx.strokeStyle=accent;ctx.stroke();}
      ctx.globalAlpha=0.25;ctx.strokeStyle=accent;ctx.beginPath();ctx.ellipse(0,0,34,26,0,0,Math.PI*2);ctx.stroke();
    }

    function drawCubeIcon(ctx, accent) {
      const s=22;ctx.beginPath();ctx.moveTo(-s,s*0.4);ctx.lineTo(0,s*0.9);ctx.lineTo(s,s*0.4);ctx.lineTo(s,-s*0.4);ctx.lineTo(0,-s*0.1);ctx.lineTo(-s,-s*0.4);ctx.closePath();ctx.stroke();
      ctx.beginPath();ctx.moveTo(-s,-s*0.4);ctx.lineTo(0,-s*0.9);ctx.lineTo(s,-s*0.4);ctx.stroke();
      ctx.beginPath();ctx.moveTo(0,-s*0.1);ctx.lineTo(0,s*0.9);ctx.stroke();
    }

    // ── Tech-to-color mapping ──
    const TECH_COLORS = {
      Rust:'#e8734a',Go:'#00add8',TypeScript:'#3178c6',JavaScript:'#f7df1e',
      Python:'#3776ab',Swift:'#f05138',Kotlin:'#7f52ff',MLX:'#5c6bc0',
      'Apple Silicon':'#a2aaad',Routing:'#7EBAB5',Observability:'#9c7cdb',
      FUSE:'#e6a817',Linux:'#3d8c40','OpenAPI':'#6ba539',MCP:'#e07c4f',
      'Provider integration':'#00add8',Reliability:'#d94f4f',Algorithms:'#00bcd4',
      WebSockets:'#ff9800','Cellular automata':'#7c4dff',AWS:'#ff9900',
      Deployment:'#4caf50',Traceability:'#e8734a',Audit:'#d94f4f',
      'Product design':'#9c7cdb',Manufacturing:'#78909c',GTM:'#4caf50',
      Fulfillment:'#78909c',Design:'#e91e63',
    };
    const ACCENT_FALLBACK = ['#7EBAB5','#737c4c','#3f8795'];

    function resolveAccentColors(techs) {
      if (!techs || !techs.length) return ACCENT_FALLBACK;
      const mapped = techs.map(t => TECH_COLORS[t]).filter(Boolean);
      return mapped.length >= 2 ? mapped : [...mapped, ...ACCENT_FALLBACK].slice(0, 3);
    }

    // ── PRNG ──
    function mulberry32(seed) {
      let s = seed | 0;
      return function() { s=(s+0x6d2b79f5)|0; let t=Math.imul(s^(s>>>15),1|s); t=(t+Math.imul(t^(t>>>7),61|t))^t; return((t^(t>>>14))>>>0)/4294967296; };
    }
    function hashString(str) { let h=0x811c9dc5; for(let i=0;i<str.length;i++){h^=str.charCodeAt(i);h=Math.imul(h,0x01000193);} return h>>>0; }
    function pick(rng,arr){return arr[Math.floor(rng()*arr.length)];}

    // ── Render pipeline ──
    const W=800,H=450;
    const COLORS={graphite950:'#171a18',graphite900:'#20231f',white:'#ffffff'};

    function renderCard(project) {
      const canvas = document.createElement('canvas');
      canvas.width = W; canvas.height = H;
      const ctx = canvas.getContext('2d');
      const seed = hashString(project.slug);
      const rng = mulberry32(seed);
      const techs = project.technologies || [];
      const accent = resolveAccentColors(techs);
      const primary = accent[0];

      // Background
      const grad=ctx.createLinearGradient(0,0,0,H);grad.addColorStop(0,COLORS.graphite950);grad.addColorStop(1,COLORS.graphite900);ctx.fillStyle=grad;ctx.fillRect(0,0,W,H);
      const rad=ctx.createRadialGradient(W*0.72,H*0.28,0,W*0.72,H*0.28,W*0.55);rad.addColorStop(0,hexToRgba(primary,0.07));rad.addColorStop(1,'rgba(0,0,0,0)');ctx.fillStyle=rad;ctx.fillRect(0,0,W,H);

      // Shapes
      const centers=[];const sc=3+Math.floor(rng()*3);
      for(let i=0;i<sc;i++){const color=pick(rng,accent);const cx=60+rng()*(W-120);const cy=50+rng()*(H-100);centers.push({x:cx,y:cy});ctx.save();ctx.globalAlpha=0.06+rng()*0.10;ctx.fillStyle=color;ctx.strokeStyle=color;ctx.lineWidth=1.2;const s=rng();
        if(s<0.3){const r=30+rng()*70;ctx.beginPath();ctx.arc(cx,cy,r,0,Math.PI*2);ctx.fill();ctx.globalAlpha+=0.04;ctx.stroke();}
        else if(s<0.6){const w=40+rng()*100,h=30+rng()*60,rot=(rng()-0.5)*0.35;ctx.translate(cx,cy);ctx.rotate(rot);ctx.fillRect(-w/2,-h/2,w,h);ctx.strokeRect(-w/2,-h/2,w,h);}
        else if(s<0.82){const len=50+rng()*140,angle=rng()*Math.PI*2;ctx.lineWidth=1.5+rng()*2;ctx.beginPath();ctx.moveTo(cx-Math.cos(angle)*len/2,cy-Math.sin(angle)*len/2);ctx.lineTo(cx+Math.cos(angle)*len/2,cy+Math.sin(angle)*len/2);ctx.stroke();}
        else{const r=18+rng()*35;ctx.lineWidth=1.5+rng()*2;ctx.beginPath();ctx.arc(cx,cy,r,0,Math.PI*2);ctx.stroke();}ctx.restore();
      }

      // Connections
      ctx.save();
      for(let i=0;i<centers.length;i++){for(let j=i+1;j<centers.length;j++){if(i===0||rng()<0.55){const a=centers[i],b=centers[j];ctx.globalAlpha=0.05+rng()*0.06;ctx.strokeStyle=pick(rng,accent);ctx.lineWidth=0.8;ctx.setLineDash([4+rng()*6,6+rng()*8]);ctx.beginPath();ctx.moveTo(a.x,a.y);const mx=(a.x+b.x)/2+(rng()-0.5)*70,my=(a.y+b.y)/2+(rng()-0.5)*50;ctx.quadraticCurveTo(mx,my,b.x,b.y);ctx.stroke();ctx.globalAlpha=0.12;ctx.setLineDash([]);ctx.fillStyle=pick(rng,accent);ctx.beginPath();ctx.arc(mx,my,1.5,0,Math.PI*2);ctx.fill();}}}
      ctx.setLineDash([]);ctx.restore();

      // Title watermark
      ctx.save();ctx.globalAlpha=0.055;ctx.fillStyle=COLORS.white;ctx.font='700 150px "Space Grotesk",sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';let t=project.title;const mw=W*0.85;while(ctx.measureText(t).width>mw&&t.length>3)t=t.slice(0,-1);if(t!==project.title)t+='...';ctx.fillText(t,W/2,H/2+10);ctx.restore();

      // Category icon
      ctx.save();ctx.translate(W*0.78,H*0.30);drawCategoryIcon(ctx,project.category,primary);ctx.restore();

      // Tech badges
      ctx.save();const badges=techs.slice(0,4);let bx=32;const by=H-58;ctx.font='600 11px "Space Grotesk",sans-serif';
      for(const tech of badges){const tw=ctx.measureText(tech).width,bw=tw+20;ctx.globalAlpha=0.12;ctx.fillStyle=primary;roundRect(ctx,bx,by-15,bw,20,4);ctx.fill();ctx.globalAlpha=0.28;ctx.strokeStyle=primary;ctx.lineWidth=0.8;ctx.stroke();ctx.globalAlpha=0.85;ctx.fillStyle=COLORS.white;ctx.textAlign='left';ctx.textBaseline='middle';ctx.fillText(tech,bx+10,by-5);bx+=bw+6;}
      ctx.restore();

      // Title label
      ctx.save();ctx.globalAlpha=0.82;ctx.fillStyle=COLORS.white;ctx.font='600 22px "Space Grotesk",sans-serif';ctx.textAlign='left';ctx.textBaseline='bottom';ctx.fillText(project.title,32,H-34);const tlw=ctx.measureText(project.title).width;ctx.globalAlpha=0.45;ctx.strokeStyle=primary;ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(32,H-28);ctx.lineTo(32+tlw,H-28);ctx.stroke();ctx.restore();

      return canvas.toDataURL('image/png');
    }

    // Expose for Playwright
    window.__renderCard = renderCard;
    </script>
  `;
}

/* ─── Main ─── */

async function main() {
  console.log('Static PNG card generator');
  console.log('Card dimensions: %d x %d px', CARD_WIDTH, CARD_HEIGHT);
  console.log('');

  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: CARD_WIDTH, height: CARD_HEIGHT } });

  // Load a minimal page with the renderer
  await page.setContent(`
    <!DOCTYPE html>
    <html><head><style>
      @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@600;700&display=swap');
    </style></head><body>
    ${getRendererSource()}
    </body></html>
  `);

  // Wait for font to load
  await page.waitForTimeout(1500);

  let generated = 0;
  let skipped = 0;

  for (const project of PROJECTS) {
    if (SKIP.has(project.slug)) {
      skipped++;
      continue;
    }

    const outDir = join(ROOT, 'public', 'projects', project.slug);
    const outPath = join(outDir, 'card.png');

    if (!existsSync(outDir)) {
      mkdirSync(outDir, { recursive: true });
    }

    // Render the card in the browser
    const dataUrl = await page.evaluate((p) => window.__renderCard(p), project);

    // Convert data URL to buffer and write
    const base64 = dataUrl.replace(/^data:image\/png;base64,/, '');
    const buffer = Buffer.from(base64, 'base64');

    const { writeFileSync } = await import('node:fs');
    writeFileSync(outPath, buffer);

    console.log('  [OK]  %s  ->  %s  (%d bytes)', project.slug, outPath.replace(ROOT + '/', ''), buffer.length);
    generated++;
  }

  await browser.close();

  console.log('');
  console.log('Generated %d card PNGs, skipped %d (have real images)', generated, skipped);
  console.log('Card dimensions: %d x %d px', CARD_WIDTH, CARD_HEIGHT);
}

main().catch((err) => {
  console.error('Card generation failed:', err);
  process.exit(1);
});
