import {build} from 'esbuild';
import {readFile, mkdir, writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';

const result = await build({entryPoints: ['page.mjs'], bundle: true, write: false,
  format: 'iife', platform: 'browser', target: ['chrome100'], minify: true, legalComments: 'inline'});
const script = result.outputFiles[0].text.replaceAll('</script', '<\\/script');
const html = (await readFile('index.html', 'utf8')).replace('<!-- BUNDLE -->', `<script>${script}</script>`);
await mkdir('dist', {recursive: true});
await writeFile('dist/passport-inspect.html', html);
await writeFile('dist/SHA256SUMS', createHash('sha256').update(html).digest('hex') + '  passport-inspect.html\n');
let notices = '';
for (const name of ['esptool-js', 'web-serial-polyfill', 'pako', 'atob-lite']) {
  const license = await readFile(`node_modules/${name}/${name === 'atob-lite' ? 'LICENSE.md' : 'LICENSE'}`, 'utf8');
  notices += `${name}\n${license}\n\n`;
}
await writeFile('dist/THIRD-PARTY-LICENSES.txt', notices);
console.log('Built a standalone static read-only page. No deployment or device operation performed.');
