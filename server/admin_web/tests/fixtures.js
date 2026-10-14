// Synthetic records only. No tests send traffic or credentials to production.
export const longText = '长文本配置与设备信息'.repeat(35);
export const agent = {
  id: 'test-agent', agentName: longText, systemPrompt: longText, agentId: 'test-agent',
  llmModelName: longText, ttsModelName: longText, ttsVoiceName: longText,
  deviceCount: 1, memModelId: 'Memory_local_short', functions: [], contextProvider: [], tags: [],
};
export const device = {
  id: 'test-device', alias: longText, board: longText, macAddress: 'AA:BB:CC:DD:EE:FF',
  appVersion: '0.9.7', autoUpdate: 0, createDateTimestamp: 1791936000000,
};
const model = { id: 'test-model', modelName: longText, modelCode: 'test', configJson: { type: 'test' }, isEnabled: 1, isDefault: 0, sort: 1 };
const param = { id: 'test-param', paramCode: 'server.long_parameter', paramValue: longText, valueType: 'string', remark: longText };
const features = Object.fromEntries(['voiceprintRecognition','voiceClone','knowledgeBase','mcpAccessPoint','vad','asr','addressBook'].map(key => [key, { enabled: true, name: key, description: longText }]));
export const pubConfig = { version: 'test', allowUserRegister: true, systemWebMenu: { features } };

export async function mockBackend(page, superAdmin = true) {
  await page.addInitScript(({ config, admin }) => {
    localStorage.setItem('token', 'synthetic-test-token');
    localStorage.setItem('userLanguage', 'zh_CN');
    localStorage.setItem('userInfo', JSON.stringify({ username: '响应式测试', superAdmin: admin }));
    localStorage.setItem('pubConfig', JSON.stringify(config));
  }, { config: pubConfig, admin: superAdmin });
  await page.route('**/xiaozhi/**', async route => {
    const path = new URL(route.request().url()).pathname.replace(/^\/xiaozhi/, '');
    let data = { list: [], total: 0 };
    if (path.endsWith('/pub-config')) data = pubConfig;
    else if (path === '/user/info') data = { username: '响应式测试', superAdmin };
    else if (path === '/agent/list' || path.includes('/agent/search')) data = [agent];
    else if (path === '/agent/template') data = [];
    else if (path === '/agent/test-agent') data = agent;
    else if (path.includes('/tags') || path.includes('/voiceprint') || path.includes('/voice-print')) data = [];
    else if (path.includes('/snapshots/current')) data = { currentVersionNo: 1 };
    else if (path.includes('/device/bind/')) data = [device];
    else if (path.includes('/device/address-book/')) data = { alias: longText, permissions: [] };
    else if (path.includes('status')) data = '{}';
    else if (path === '/models/names' || path.includes('/llm/names') || path.endsWith('/plugin/names')) data = [];
    else if (path === '/models/provider') data = { list: [{ id: 'test-provider', name: longText, providerCode: 'test', modelType: 'LLM', fields: '[{"key":"test","label":"测试字段","type":"string"}]', sort: 1 }], total: 1 };
    else if (path.startsWith('/models/') && path.endsWith('/voices')) data = { list: [], total: 0 };
    else if (path === '/models') data = { list: [model], total: 1 };
    else if (path === '/admin/params/page') data = { list: [param], total: 1 };
    else if (path === '/admin/server/server-list') data = ['http://example.invalid/' + 'long-path/'.repeat(20)];
    else if (path === '/admin/users') data = { list: [{ id: 'test-user', username: longText, mobile: '13800000000', status: 1, selected: false }], total: 1 };
    else if (path === '/datasets/rag-models') data = [];
    else if (path === '/datasets') data = { list: [{ datasetId: 'test-kb', name: longText, description: longText, status: 1 }], total: 1 };
    else if (path.endsWith('/documents')) data = { list: [{ id: 'test-document', name: longText + '.txt', parseStatusCode: 0, size: 1024 }], total: 1 };
    else if (path.includes('/agent/') && (path.includes('template') || path.includes('voice'))) data = [];
    await route.fulfill({ contentType: 'application/json', body: JSON.stringify({ code: 0, data }) });
  });
}
