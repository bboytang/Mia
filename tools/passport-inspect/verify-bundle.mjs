// Check the actual bundled artifact loads, does not access USB on page load,
// and refuses an insecure context before opening a port. No real USB claim.
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';
import assert from 'node:assert/strict';

const html = await readFile('dist/passport-inspect.html', 'utf8');
assert.equal((html.match(/<script>/g) || []).length, 1);
assert.ok(!html.includes('<script src='));
assert.match(html, /工具 v3/);
assert.match(html, /value="usb" selected/);
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

async function checkPicker(navigator, expected, mode = 'usb') {
  let picker;
  const elements = new Map();
  const document = {querySelector(selector) {
    if (!elements.has(selector)) elements.set(selector, {
      hidden: true, value: selector === '#connection' ? mode : undefined,
      addEventListener(type, callback) {picker = callback;},
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
  {userAgent: 'Mozilla/5.0 (X11; Linux x86_64)', userAgentData: {platform: 'Linux'}},
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
}, 'EXPECTED_DESKTOP_SERIAL_PICKER', 'serial');
assert.equal(serialCalls, 1);
await checkPicker({userAgent: 'unsupported', serial: {requestPort() {throw new Error('UNWANTED_SERIAL_FALLBACK');}}}, '未提供 USB 设备接口');
await checkPicker({userAgent: 'unsupported'}, '未提供电脑串口接口', 'serial');
console.log('Actual bundle: explicit USB default survives Android desktop mode; no serial fallback; desktop serial is opt-in; unsupported API rejected.');
