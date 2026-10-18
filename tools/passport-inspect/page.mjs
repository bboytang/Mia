import { ESPLoader, Transport } from 'esptool-js';
import { serial as usbSerial } from 'web-serial-polyfill';
import { inspect } from './probe.mjs';

const button = document.querySelector('#inspect');
const download = document.querySelector('#download');
const status = document.querySelector('#status');
let reportUrl;
button.addEventListener('click', async () => {
  button.disabled = true;
  download.hidden = true;
  status.textContent = '请选择 AI Passport USB 设备。读取期间保持供电。';
  let transport;
  try {
    if (!window.isSecureContext) throw new Error('需要 HTTPS 安全页面；本地文件是否支持需由浏览器确认');
    const android = /Android/i.test(navigator.userAgent || '') || navigator.userAgentData?.platform === 'Android';
    const hasUsb = typeof navigator.usb?.requestDevice === 'function';
    // Android may expose a serial API without enumerating the USB CDC device.
    // Match the official Passport tool: prefer WebUSB on Android.
    const serial = android && hasUsb ? usbSerial
      : typeof navigator.serial?.requestPort === 'function' ? navigator.serial
      : hasUsb ? usbSerial : null;
    if (!serial) throw new Error('当前浏览器不支持 USB 连接，请使用安卓 Chrome');
    const port = await serial.requestPort({filters: [{usbVendorId: 0x303a, usbProductId: 0x1001}]});
    const info = port.getInfo();
    if (info.usbVendorId !== 0x303a || info.usbProductId !== 0x1001) throw new Error('请选择 C3 USB JTAG/serial debug unit');
    transport = new Transport(port);
    const loader = new ESPLoader({transport, baudrate: 115200,
      terminal: {clean() {}, write() {}, writeLine() {}}});
    status.textContent = '正在连接并只读检查。设备会暂时进入下载模式。';
    const report = await inspect(loader, async bytes => {
      const hash = await crypto.subtle.digest('SHA-256', bytes);
      return Array.from(new Uint8Array(hash), n => n.toString(16).padStart(2, '0')).join('');
    });
    if (reportUrl) URL.revokeObjectURL(reportUrl);
    reportUrl = URL.createObjectURL(new Blob([JSON.stringify(report, null, 2) + '\n'], {type: 'application/json'}));
    download.href = reportUrl;
    download.hidden = false;
    status.textContent = `读取完成：ESP32-C3，8MB，revision ${report.chip_revision}。请保存检查报告，供工程审核；没有授权或执行刷机。完成后拔线重新上电。`;
  } catch (error) {
    status.textContent = `检查未完成：${error instanceof Error ? error.message : 'USB 通信失败'}。没有请求 Flash 写入或擦除；可拔线重新上电。`;
  } finally {
    if (transport) await transport.disconnect().catch(() => {});
    button.disabled = false;
  }
});
