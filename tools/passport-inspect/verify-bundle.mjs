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

async function checkPicker(navigator, expected) {
  let picker;
  const elements = new Map();
  const document = {querySelector(selector) {
    if (!elements.has(selector)) elements.set(selector, {
      hidden: true, addEventListener(type, callback) {picker = callback;},
    });
    return elements.get(selector);
  }};
  vm.runInNewContext(script, {document, navigator, window: {isSecureContext: true},
    Error, TextEncoder, TextDecoder, Uint8Array, Blob, URL, ReadableStream, WritableStream,
    setTimeout, clearTimeout, atob, btoa}, {timeout: 1000});
  await picker();
  assert.match(elements.get('#status').textContent, new RegExp(expected));
  assert.equal(elements.get('#download').hidden, true);
  assert.equal(elements.get('#inspect').disabled, false);
}
for (const platform of [
  {userAgent: 'Mozilla/5.0 (Linux; Android 14; Tablet)'},
  {userAgent: 'desktop mode', userAgentData: {platform: 'Android'}},
]) {
  let usbCalls = 0;
  await checkPicker({...platform,
    serial: {requestPort() {throw new Error('WRONG_NATIVE_SERIAL');}},
    usb: {async requestDevice(options) {
      usbCalls++;
      assert.equal(options.filters[0].vendorId, 0x303a);
      assert.equal(options.filters[0].productId, 0x1001);
      assert.equal(options.filters[0].classCode, 2);
      throw new Error('EXPECTED_ANDROID_USB_PICKER');
    }},
  }, 'EXPECTED_ANDROID_USB_PICKER');
  assert.equal(usbCalls, 1);
}
let serialCalls = 0;
await checkPicker({userAgent: 'desktop',
  serial: {async requestPort(options) {
    serialCalls++;
    assert.equal(options.filters[0].usbVendorId, 0x303a);
    assert.equal(options.filters[0].usbProductId, 0x1001);
    throw new Error('EXPECTED_DESKTOP_SERIAL_PICKER');
  }},
  usb: {requestDevice() {throw new Error('WRONG_DESKTOP_USB');}},
}, 'EXPECTED_DESKTOP_SERIAL_PICKER');
assert.equal(serialCalls, 1);
await checkPicker({userAgent: 'unsupported'}, '当前浏览器不支持 USB');
console.log('Actual bundle: Android user-agent/platform prefer USB; desktop retains native serial; unsupported API rejected.');
