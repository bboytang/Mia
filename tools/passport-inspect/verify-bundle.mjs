// Check the actual bundled artifact loads, does not access USB on page load,
// and refuses an insecure context before opening a port. No real USB claim.
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';
import assert from 'node:assert/strict';

const html = await readFile('dist/passport-inspect.html', 'utf8');
assert.equal((html.match(/<script>/g) || []).length, 1);
assert.ok(!html.includes('<script src='));
const script = html.split('<script>')[1].split('</script>')[0];
const elements = new Map();
let click;
const document = {querySelector(selector) {
  if (!elements.has(selector)) elements.set(selector, {
    hidden: true, addEventListener(type, callback) {assert.equal(type, 'click'); click = callback;},
  });
  return elements.get(selector);
}};
const navigator = new Proxy({}, {get() {throw new Error('Unexpected USB access');}});
vm.runInNewContext(script, {document, navigator, window: {isSecureContext: false},
  TextEncoder, TextDecoder, Uint8Array, Blob, URL, ReadableStream, WritableStream,
  setTimeout, clearTimeout, atob, btoa}, {timeout: 1000});
assert.equal(typeof click, 'function');
await click();
assert.match(elements.get('#status').textContent, /HTTPS/);
assert.equal(elements.get('#download').hidden, true);
assert.equal(elements.get('#inspect').disabled, false);
console.log('Actual standalone bundle loaded; insecure context denied before USB access.');
