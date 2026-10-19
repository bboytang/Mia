"""Necessary authorization hooks for the existing manager chat services."""

from .install_youmi import replace_once

BASE = 'main/manager-api/src/main/java/xiaozhi/modules/agent/'
HISTORY = BASE + 'controller/AgentChatHistoryController.java'
REPORT = BASE + 'dto/AgentChatHistoryReportDTO.java'
BIZ = BASE + 'service/biz/impl/AgentChatHistoryBizServiceImpl.java'
CONTROLLER = BASE + 'controller/AgentController.java'
INTERFACE = BASE + 'service/AgentChatSummaryService.java'
SUMMARY = BASE + 'service/impl/AgentChatSummaryServiceImpl.java'
PREIMAGES = {
    HISTORY: '8ff57406926f69e9ca827cb8150f3fefbc7e920e483d7cbdd5e7f8682fc00d8d',
    REPORT: 'b3040b643a26f6f5232c874fd282501fa8df47d52f0d47c832c7dfb089089a6d',
    BIZ: '1bd87661db055b5a4b82e8aa988a9ea22b7f2acbfe25fa0831c6e7b2fb0d2981',
    CONTROLLER: '597b38912f513c35a6d7fb44d337480cd3350712d2867a9c22369524d822872b',
    INTERFACE: '20dd65f4b6efb8771d3853d49870ab92ddc11de4cc6ee40555a5540285171d8f',
    SUMMARY: '1d690790d2c8153cc385ded3d6f814389cc4d43560ce8d768a48c748e361f179',
}
CHAT_AUTH = 'xiaozhi.modules.device.service.impl.YoumiChatAuthorizationService'


def field(text, anchor):
    return replace_once(text, anchor, anchor + '\n'
                        '    @jakarta.annotation.Resource\n'
                        f'    private {CHAT_AUTH} youmiChatAuthorization;\n')


def history(text):
    text = field(text, '    private final RedisUtils redisUtils;')
    return replace_once(text, '        Boolean result = agentChatHistoryBizService.report(request);',
                        '        Map<String, Object> snapshot = request.getMiaScope();\n'
                        '        Map<String, Object> scope = youmiChatAuthorization.require(snapshot, request.getSessionId(), true);\n'
                        '        if (!scope.get("device_id").equals(request.getMacAddress())) {\n'
                        '            throw new RenException(ErrorCode.NO_PERMISSION);\n        }\n'
                        '        Boolean result = youmiChatAuthorization.write(snapshot, request.getSessionId(), true,\n'
                        '                () -> agentChatHistoryBizService.report(request));')


def report(text):
    return replace_once(text, '    private String macAddress;',
                        '    private String macAddress;\n\n'
                        '    @NotNull\n    private java.util.Map<String, Object> miaScope;')


def biz(text):
    text = field(text, '    private final DeviceService deviceService;')
    return replace_once(text, '        Integer chatHistoryConf = agentEntity.getChatHistoryConf();',
                        '        var scope = youmiChatAuthorization.require(report.getMiaScope(), report.getSessionId(), true);\n'
                        '        if (!scope.get("agent_id").equals(agentEntity.getId())\n'
                        '                || !scope.get("user_id").equals(agentEntity.getUserId())) {\n'
                        '            throw new youmi.common.exception.RenException(\n'
                        '                    youmi.common.exception.ErrorCode.NO_PERMISSION);\n        }\n'
                        '        Integer chatHistoryConf = agentEntity.getChatHistoryConf();')


def controller(text):
    text = replace_once(text, 'import lombok.AllArgsConstructor;', 'import lombok.RequiredArgsConstructor;')
    text = replace_once(text, '@AllArgsConstructor', '@RequiredArgsConstructor')
    text = field(text, '    private final AgentTagService agentTagService;')
    text = replace_once(text, '    private String requireSessionAgent(String sessionId) {\n'
                        '        String agentId = agentChatHistoryService.getAgentIdBySessionId(sessionId);\n'
                        '        if (StringUtils.isBlank(agentId)) {\n'
                        '            throw new RenException(ErrorCode.AGENT_NOT_FOUND);\n        }\n'
                        '        agentService.getAgentById(agentId);\n        return agentId;\n    }\n\n', '')
    for action in ('Summary', 'Title'):
        text = replace_once(text,
                            f'    public Result<Void> generateAndSaveChat{action}(@PathVariable String sessionId) {{\n'
                            '        requireSessionAgent(sessionId);',
                            f'    public Result<Void> generateAndSaveChat{action}(@PathVariable String sessionId,\n'
                            '            @RequestBody Map<String, Object> body) {\n'
                            '        Map<String, Object> snapshot = Map.copyOf(body);\n'
                            '        youmiChatAuthorization.require(snapshot, sessionId, false);')
        text = replace_once(text, f'agentChatSummaryService.generateAndSaveChat{action}(sessionId);',
                            f'agentChatSummaryService.generateAndSaveChat{action}(sessionId, snapshot);')
    return text


def interface(text):
    for action in ('Summary', 'Title'):
        text = replace_once(text, f'boolean generateAndSaveChat{action}(String sessionId);',
                            f'boolean generateAndSaveChat{action}(String sessionId, java.util.Map<String, Object> snapshot);')
    return text


def summary(text):
    for unused in ('import xiaozhi.modules.device.entity.DeviceEntity;\n',
                   'import xiaozhi.modules.device.service.DeviceService;\n',
                   '    private final DeviceService deviceService;\n'):
        text = replace_once(text, unused, '')
    marker = '    /**\n     * 根据会话ID获取设备信息\n'
    text = replace_once(text, text[text.index(marker):text.rindex('\n}')], '')
    text = field(text, '    private final ModelConfigService modelConfigService;')
    text = replace_once(text, '    public boolean generateAndSaveChatSummary(String sessionId) {',
                        '    public boolean generateAndSaveChatSummary(String sessionId, Map<String, Object> snapshot) {')
    text = replace_once(text, '            DeviceEntity device = getDeviceBySessionId(sessionId);\n'
                        '            if (device == null) {\n'
                        '                log.info("未找到与会话 {} 关联的设备", sessionId);\n'
                        '                return false;\n            }\n\n'
                        '            String agentId = device.getAgentId();',
                        '            Map<String, Object> scope = youmiChatAuthorization.require(snapshot, sessionId, false);\n'
                        '            String agentId = (String) scope.get("agent_id");')
    text = replace_once(text, '                    agentService.updateAgentById(agentId, new AgentUpdateDTO() {\n'
                        '                        {\n                            setSummaryMemory(summaryDTO.getSummary());\n'
                        '                        }\n                    }, false);',
                        '                    youmiChatAuthorization.write(snapshot, sessionId, false, () -> {\n'
                        '                        agentService.updateAgentById(agentId, new AgentUpdateDTO() {\n'
                        '                            { setSummaryMemory(summaryDTO.getSummary()); }\n'
                        '                        }, false);\n                        return true;\n                    });')
    text = replace_once(text, '    public boolean generateAndSaveChatTitle(String sessionId) {',
                        '    public boolean generateAndSaveChatTitle(String sessionId, Map<String, Object> snapshot) {')
    text = replace_once(text, '            // 自动获取agentId\n'
                        '            String agentId = findAgentIdBySessionId(sessionId);',
                        '            Map<String, Object> scope = youmiChatAuthorization.require(snapshot, sessionId, false);\n'
                        '            String agentId = (String) scope.get("agent_id");')
    text = replace_once(text, '                agentChatTitleService.saveOrUpdateTitle(sessionId, title);',
                        '                youmiChatAuthorization.write(snapshot, sessionId, false, () -> {\n'
                        '                    agentChatTitleService.saveOrUpdateTitle(sessionId, title);\n'
                        '                    return true;\n                });')
    # Recheck immediately before either LLM, not only at dispatch or persistence.
    text = replace_once(text, '                AgentChatSummaryDTO summaryDTO = generateChatSummary(sessionId);',
                        '                youmiChatAuthorization.require(snapshot, sessionId, false);\n'
                        '                AgentChatSummaryDTO summaryDTO = generateChatSummary(sessionId);')
    return replace_once(text, '            String title = llmService.generateTitle(conversation.toString(), slmModelId);',
                        '            youmiChatAuthorization.require(snapshot, sessionId, false);\n'
                        '            String title = llmService.generateTitle(conversation.toString(), slmModelId);')


PATCHERS = {HISTORY: history, REPORT: report, BIZ: biz, CONTROLLER: controller,
            INTERFACE: interface, SUMMARY: summary}
