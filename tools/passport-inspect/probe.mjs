// No arbitrary address, flash write, erase, reset-to-firmware or eFuse operation.
export const TABLE_ADDRESS = 0x8000;
export const TABLE_BYTES = 4096;

export function restrictCommands(loader) {
  const command = loader.command.bind(loader);
  // RAM stub upload, synchronization, SPI register access, security and table
  // read only. Unknown commands fail closed, including flash write and erase.
  const allowed = new Set([null, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0a, 0x0d, 0x14, 0xd2]);
  loader.command = (op, ...args) => {
    if (!allowed.has(op ?? null)) throw new Error('Flash modification is disabled');
    return command(op, ...args);
  };
}

export async function inspect(loader, sha256) {
  restrictCommands(loader);
  await loader.detectChip();
  if (loader.chip?.CHIP_NAME !== 'ESP32-C3') throw new Error('仅支持 ESP32-C3');
  const security = await loader.getSecurityInfo();
  if (security.chipId !== 5 || !Number.isInteger(security.flags) || security.flags < 0 ||
      security.flags > 0xffffffff ||
      !Number.isInteger(security.flashCryptCnt) || security.flashCryptCnt < 0 ||
      security.flashCryptCnt > 255) throw new Error('无法确认芯片安全状态');
  const secureBoot = (security.flags & 1) !== 0;
  const secureDownload = (security.flags & 4) !== 0;
  let bits = security.flashCryptCnt, count = 0;
  while (bits) { count += bits & 1; bits >>>= 1; }
  const encrypted = count % 2 !== 0;
  if (secureBoot || secureDownload || encrypted) {
    throw new Error('已启用芯片安全功能，需要单独审查；未读取 Flash');
  }
  const major = await loader.chip.getMajorChipVersion(loader);
  const minor = await loader.chip.getMinorChipVersion(loader);
  if (!Number.isInteger(major) || !Number.isInteger(minor) ||
      major < 0 || major > 3 || minor < 0 || minor > 15) throw new Error('无法确认硅片版本');
  // The official stub is bundled locally and uploaded to RAM only.
  await loader.runStub();
  const id = await loader.readFlashId();
  if (!Number.isInteger(id) || (id >>> 16 & 255) !== 23 ||
      (id & 255) === 0 || (id & 255) === 255) throw new Error('无法确认 8MB Flash');
  const table = await loader.readFlash(TABLE_ADDRESS, TABLE_BYTES);
  if (!(table instanceof Uint8Array) || table.length !== TABLE_BYTES ||
      table[0] !== 0xaa || table[1] !== 0x50) throw new Error('分区表读取失败');
  return {
    schema: 1, source: 'mia-passport-browser-inspection', chip: 'esp32c3',
    flash_bytes: 0x800000, flash_id: id, chip_revision: major * 100 + minor,
    secure_boot: false, flash_encryption: false, secure_download: false,
    partition_table_sha256: await sha256(table),
    partition_table_hex: Array.from(table, n => n.toString(16).padStart(2, '0')).join(''),
    identity_regions_reviewed: false, recovery_boot_change_noted: false,
    flash_authorized: false, full_flash_backup_read: false,
  };
}
