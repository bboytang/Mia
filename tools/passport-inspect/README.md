# AI Passport Android read-only inspection

Static support tool for the Mia firmware migration. It does not add a backend,
upload reports, publish a site, erase/program flash or burn eFuses. It temporarily
resets the device into ROM download mode and runs Espressif's bundled RAM stub.
Afterward disconnect USB and power-cycle the device.

```sh
npm ci --ignore-scripts
npm test
npm run build
```

`dist/passport-inspect.html` is a standalone file: scripts, USB compatibility
layer and official RAM stub are bundled; no CDN/runtime network request is needed.
`dist/SHA256SUMS` identifies the exact file. The page blocks network access via
CSP and only offers a local JSON download. Dependencies are locked and sourced
from [Espressif esptool-js v0.7.0](https://github.com/espressif/esptool-js/tree/v0.7.0)
and [Google web-serial-polyfill](https://github.com/google/web-serial-polyfill).
Both are Apache-2.0; esbuild is a build-only MIT dependency. The generated page
retains library license comments.

Open it in an Android Chrome context that exposes WebUSB. A local file may or
may not expose USB on a particular tablet: the page checks `isSecureContext` and
API availability first. If it is blocked, it needs static HTTPS hosting reviewed
separately; no deployment is performed by these scripts. Do not use the project's
production server without approval. Android USB/CDC, ROM reset, disconnect and
report download require a physical tablet/device test; mocked tests do not prove
USB compatibility.

Click “连接并只读检查”, select `USB JTAG/serial debug unit`, wait, then save
`passport-inspection.json`. It contains no key, MAC, NVS or Wi-Fi readout. Safety
preflight rejects wrong chips, enabled/unknown security, non-8MB flash, malformed
or truncated table. Only address `0x8000`, length `0x1000`, can be read. Raw flash
write/compressed write/erase commands are also explicitly blocked. No user-supplied
command or address exists. Full MD5 partition-table parsing happens on import:

```sh
python -m scripts.passport.inspect_device \
  --browser-report /private/path/passport-inspection.json \
  --output /private/path/passport-inspection
```

Review the resulting table and security report using the existing installation
packager; imported reports never grant approval. Inspecting a device is separate
from approving and carrying out the first flash.
