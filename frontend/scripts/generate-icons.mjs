import sharp from 'sharp';
import { readFileSync, mkdirSync, existsSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const publicDir = join(__dirname, '..', 'public');

// Ensure public directory exists
if (!existsSync(publicDir)) {
  mkdirSync(publicDir, { recursive: true });
}

// SVG content for the icon
const svgContent = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <defs>
    <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#fc4c02;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#e03d00;stop-opacity:1" />
    </linearGradient>
  </defs>
  <rect width="512" height="512" rx="96" fill="url(#grad)"/>
  <g transform="translate(256, 256)">
    <circle cx="-80" cy="40" r="50" fill="none" stroke="white" stroke-width="16"/>
    <circle cx="80" cy="40" r="50" fill="none" stroke="white" stroke-width="16"/>
    <path d="M-80 40 L-20 -60 L40 -60 L80 40" fill="none" stroke="white" stroke-width="16" stroke-linecap="round" stroke-linejoin="round"/>
    <path d="M-20 -60 L0 40 L80 40" fill="none" stroke="white" stroke-width="16" stroke-linecap="round" stroke-linejoin="round"/>
    <circle cx="0" cy="40" r="12" fill="white"/>
    <path d="M40 -60 L60 -80 L80 -70" fill="none" stroke="white" stroke-width="12" stroke-linecap="round" stroke-linejoin="round"/>
  </g>
</svg>`;

// Maskable icon (with safe zone padding)
const maskableSvg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <defs>
    <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#fc4c02;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#e03d00;stop-opacity:1" />
    </linearGradient>
  </defs>
  <rect width="512" height="512" fill="url(#grad)"/>
  <g transform="translate(256, 256) scale(0.7)">
    <circle cx="-80" cy="40" r="50" fill="none" stroke="white" stroke-width="16"/>
    <circle cx="80" cy="40" r="50" fill="none" stroke="white" stroke-width="16"/>
    <path d="M-80 40 L-20 -60 L40 -60 L80 40" fill="none" stroke="white" stroke-width="16" stroke-linecap="round" stroke-linejoin="round"/>
    <path d="M-20 -60 L0 40 L80 40" fill="none" stroke="white" stroke-width="16" stroke-linecap="round" stroke-linejoin="round"/>
    <circle cx="0" cy="40" r="12" fill="white"/>
    <path d="M40 -60 L60 -80 L80 -70" fill="none" stroke="white" stroke-width="12" stroke-linecap="round" stroke-linejoin="round"/>
  </g>
</svg>`;

const sizes = [
  { name: 'favicon-16x16.png', size: 16 },
  { name: 'favicon-32x32.png', size: 32 },
  { name: 'pwa-64x64.png', size: 64 },
  { name: 'pwa-192x192.png', size: 192 },
  { name: 'pwa-512x512.png', size: 512 },
  { name: 'apple-touch-icon.png', size: 180 },
];

async function generateIcons() {
  console.log('Generating PWA icons...');

  // Generate regular icons
  for (const { name, size } of sizes) {
    await sharp(Buffer.from(svgContent))
      .resize(size, size)
      .png()
      .toFile(join(publicDir, name));
    console.log(`  ✓ ${name}`);
  }

  // Generate maskable icon
  await sharp(Buffer.from(maskableSvg))
    .resize(512, 512)
    .png()
    .toFile(join(publicDir, 'maskable-icon-512x512.png'));
  console.log('  ✓ maskable-icon-512x512.png');

  // Generate OG image (1200x630)
  const ogSvg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 630">
    <defs>
      <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" style="stop-color:#0f0f0f;stop-opacity:1" />
        <stop offset="100%" style="stop-color:#1a1a1a;stop-opacity:1" />
      </linearGradient>
      <linearGradient id="iconGrad" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" style="stop-color:#fc4c02;stop-opacity:1" />
        <stop offset="100%" style="stop-color:#e03d00;stop-opacity:1" />
      </linearGradient>
    </defs>
    <rect width="1200" height="630" fill="url(#bgGrad)"/>
    <g transform="translate(200, 315)">
      <rect x="-80" y="-80" width="160" height="160" rx="32" fill="url(#iconGrad)"/>
      <g transform="scale(0.25)">
        <circle cx="-80" cy="40" r="50" fill="none" stroke="white" stroke-width="16"/>
        <circle cx="80" cy="40" r="50" fill="none" stroke="white" stroke-width="16"/>
        <path d="M-80 40 L-20 -60 L40 -60 L80 40" fill="none" stroke="white" stroke-width="16" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M-20 -60 L0 40 L80 40" fill="none" stroke="white" stroke-width="16" stroke-linecap="round" stroke-linejoin="round"/>
        <circle cx="0" cy="40" r="12" fill="white"/>
        <path d="M40 -60 L60 -80 L80 -70" fill="none" stroke="white" stroke-width="12" stroke-linecap="round" stroke-linejoin="round"/>
      </g>
    </g>
    <text x="350" y="290" font-family="system-ui, -apple-system, sans-serif" font-size="72" font-weight="bold" fill="white">ApexPath</text>
    <text x="350" y="370" font-family="system-ui, -apple-system, sans-serif" font-size="32" fill="#9ca3af">AI-Powered Cycling Training</text>
  </svg>`;

  await sharp(Buffer.from(ogSvg))
    .resize(1200, 630)
    .png()
    .toFile(join(publicDir, 'og-image.png'));
  console.log('  ✓ og-image.png');

  // Generate screenshot placeholders
  const screenshotWide = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720">
    <rect width="1280" height="720" fill="#0f0f0f"/>
    <text x="640" y="360" font-family="system-ui" font-size="48" fill="#fc4c02" text-anchor="middle">ApexPath Dashboard</text>
  </svg>`;

  const screenshotNarrow = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 1136">
    <rect width="640" height="1136" fill="#0f0f0f"/>
    <text x="320" y="568" font-family="system-ui" font-size="36" fill="#fc4c02" text-anchor="middle">ApexPath Mobile</text>
  </svg>`;

  await sharp(Buffer.from(screenshotWide))
    .resize(1280, 720)
    .png()
    .toFile(join(publicDir, 'screenshot-wide.png'));
  console.log('  ✓ screenshot-wide.png');

  await sharp(Buffer.from(screenshotNarrow))
    .resize(640, 1136)
    .png()
    .toFile(join(publicDir, 'screenshot-narrow.png'));
  console.log('  ✓ screenshot-narrow.png');

  console.log('\nAll icons generated successfully!');
}

generateIcons().catch(console.error);
