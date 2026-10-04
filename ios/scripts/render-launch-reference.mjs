// Offline scene composition; the app's existing textures remain unchanged.
// npm install --prefix /tmp/mia-launch-render --ignore-scripts @napi-rs/canvas@1.0.10
import { createRequire } from 'node:module';
import { writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

const require = createRequire('/tmp/mia-launch-render/package.json');
const { createCanvas, loadImage } = require('@napi-rs/canvas');
const root = fileURLToPath(new URL('../../', import.meta.url));
const width = 933;
const height = 1686;
const canvas = createCanvas(width, height);
const context = canvas.getContext('2d');
const [city, portrait] = await Promise.all([
  loadImage(`${root}/ios/MiaApp/Assets.xcassets/CityBackground.imageset/city-background.jpg`),
  loadImage(`${root}/ios/MiaApp/Assets.xcassets/MiaPortrait.imageset/mia-portrait.png`),
]);

const cityScale = Math.max(width / city.width, height / city.height);
context.drawImage(city, (width - city.width * cityScale) / 2,
  (height - city.height * cityScale) / 2, city.width * cityScale, city.height * cityScale);
const shade = context.createLinearGradient(0, 0, 0, height);
shade.addColorStop(0, 'rgba(0,0,0,0.32)');
shade.addColorStop(0.5, 'rgba(0,0,0,0)');
shade.addColorStop(1, 'rgba(0,0,0,0.58)');
context.fillStyle = shade;
context.fillRect(0, 0, width, height);

// Mirrors ContentView's portrait bounds for a reference phone, not a device snapshot.
const pointScale = width / 393;
const safeTop = 59 * pointScale;
const safeBottom = 34 * pointScale;
const contentHeight = height - safeTop - safeBottom;
const portraitScale = Math.min(width * 1.12 / portrait.width,
  contentHeight * 0.75 / portrait.height);
context.drawImage(portrait, (width - portrait.width * portraitScale) / 2,
  safeTop + contentHeight * 0.49 - portrait.height * portraitScale / 2,
  portrait.width * portraitScale, portrait.height * portraitScale);

// An unlabelled ring guides the light arc. Native text/controls are never baked in.
const micY = height - safeBottom - 80 * pointScale;
const ring = context.createLinearGradient(width / 2 - 42 * pointScale,
  micY - 42 * pointScale, width / 2 + 42 * pointScale, micY + 42 * pointScale);
ring.addColorStop(0, '#5855d9');
ring.addColorStop(0.5, '#a441dd');
ring.addColorStop(1, '#46cbe4');
context.beginPath();
context.arc(width / 2, micY, 42 * pointScale, 0, Math.PI * 2);
context.fillStyle = ring;
context.shadowColor = '#9a46e6';
context.shadowBlur = 22 * pointScale;
context.fill();
context.shadowBlur = 0;
context.strokeStyle = 'rgba(255,255,255,0.8)';
context.lineWidth = 1.5 * pointScale;
context.stroke();
await writeFile(`${root}/docs/design/launch/mia-home-end-reference.png`, canvas.toBuffer('image/png'));
