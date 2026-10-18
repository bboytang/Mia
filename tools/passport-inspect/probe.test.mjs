import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {inspect, restrictCommands} from './probe.mjs';

function device() {
  const calls = [];
  const table = new Uint8Array(4096).fill(255);
  table.set([0xaa, 0x50]);
  return {
    calls, security: {chipId: 5, flags: 0, flashCryptCnt: 0},
    chip: {CHIP_NAME: 'ESP32-C3', getMajorChipVersion: async () => 0,
      getMinorChipVersion: async () => 4},
    command: async op => {calls.push(['command', op]);},
    async detectChip() {calls.push(['detect']);},
    async getSecurityInfo() {calls.push(['security']); return this.security;},
    async runStub() {calls.push(['ram-stub']);},
    async readFlashId() {return 0x1740c8;},
    async readFlash(address, bytes) {calls.push(['read', address, bytes]); return table;},
  };
}
const hash = async bytes => createHash('sha256').update(bytes).digest('hex');

test('only the 4KiB table is read; report never grants approval', async () => {
  const loader = device();
  const report = await inspect(loader, hash);
  assert.deepEqual(loader.calls, [['detect'], ['security'], ['ram-stub'], ['read', 0x8000, 4096]]);
  assert.equal(report.chip_revision, 4);
  assert.equal(report.partition_table_hex.length, 8192);
  assert.equal(report.flash_authorized, false);
  assert.equal(report.identity_regions_reviewed, false);
  assert.equal(report.recovery_boot_change_noted, false);
  assert.equal(report.full_flash_backup_read, false);
  assert.equal('keyPurposes' in report, false);
});
for (const security of [
  {chipId: 5, flags: 1, flashCryptCnt: 0},
  {chipId: 5, flags: 4, flashCryptCnt: 0},
  {chipId: 5, flags: 0, flashCryptCnt: 1},
  {chipId: 5, flags: 0, flashCryptCnt: 7},
  {chipId: 5, flags: 0},
  {chipId: 5, flags: undefined, flashCryptCnt: 0},
  {chipId: null, flags: 0, flashCryptCnt: 0},
]) {
  test(`unsafe or unknown security stops before RAM stub: ${JSON.stringify(security)}`, async () => {
    const loader = device(); loader.security = security;
    await assert.rejects(inspect(loader, hash));
    assert.deepEqual(loader.calls, [['detect'], ['security']]);
  });
}
test('even crypt-count popcount means disabled, not simply a nonzero counter', async () => {
  const loader = device(); loader.security.flashCryptCnt = 3;
  assert.equal((await inspect(loader, hash)).flash_encryption, false);
});
test('wrong chip, flash size, partial and malformed table are refused', async () => {
  for (const mutate of [
    loader => {loader.chip.CHIP_NAME = 'ESP32-S3';},
    loader => {loader.readFlashId = async () => 0x1640c8;},
    loader => {loader.readFlashId = async () => undefined;},
    loader => {loader.readFlash = async () => new Uint8Array(4095);},
    loader => {loader.readFlash = async () => new Uint8Array(4096);},
  ]) {
    const loader = device(); mutate(loader);
    await assert.rejects(inspect(loader, hash));
  }
});
test('flash write, compressed write and erase commands are blocked', async () => {
  const loader = device(); restrictCommands(loader);
  for (const op of [2, 3, 4, 15, 16, 17, 18, 0xd0, 0xd1, 0xff]) {
    assert.throws(() => loader.command(op), /disabled/);
  }
  await loader.command(0xd2);
  assert.deepEqual(loader.calls, [['command', 0xd2]]);
});
