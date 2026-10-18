import { ESPLoader, Transport } from 'esptool-js';
import { serial as usbSerial } from 'web-serial-polyfill';
import { inspect } from './probe.mjs';

const button = document.querySelector('#inspect');
const download = document.querySelector('#download');
const status = document.querySelector('#status');
const connection = document.querySelector('#connection');
let reportUrl;
button.addEventListener('click', async () => {
  button.disabled = true;
  download.hidden = true;
  status.textContent = '请选择 AI Passport USB 设备。读取期间保持供电。';
  let transport;
  try {
    if (!window.isSecureContext) throw new Error('需要 HTTPS 安全页面；本地文件是否支持需由浏览器确认');
    // An Android browser's desktop mode can hide both Android platform signals.
    // Select the API explicitly; the Android default never falls back to serial.
    const usb = connection.value === 'usb';
    const serial = usb ? (typeof navigator.usb?.requestDevice === 'function' ? usbSerial : null)
      : connection.value === 'serial' && typeof navigator.serial?.requestPort === 'function' ? navigator.serial : null;
    if (!serial) throw new Error(usb ? '当前浏览器未提供 USB 设备接口，请在安卓 Chrome 打开本页'
      : '当前浏览器未提供电脑串口接口');
    status.textContent = `工具 v3 / ${usb ? 'USB（安卓平板）' : '串口（电脑）'}：请选择 AI Passport 设备。`;
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
