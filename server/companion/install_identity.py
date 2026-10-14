"""Review/apply necessary binding guards to the fixed manager source only."""

import argparse
import difflib
import hashlib
from pathlib import Path
import shutil

from .install_xiaozhi import replace_once


TARGET = 'main/manager-api/src/main/java/xiaozhi/modules/device/service/impl/DeviceServiceImpl.java'
PREIMAGE = '26f5d6acbc8680232da1d8f2d8b5ad43eeaee04d4c35323f7c0f31505ce76743'


def binding_guards(original):
    text = replace_once(original, 'import lombok.AllArgsConstructor;', 'import lombok.RequiredArgsConstructor;')
    text = replace_once(text, '@AllArgsConstructor', '@RequiredArgsConstructor')
    text = replace_once(text, 'import org.springframework.stereotype.Service;',
                        'import org.springframework.stereotype.Service;\n'
                        'import org.springframework.context.annotation.Lazy;\n'
                        'import org.springframework.transaction.annotation.Transactional;\n'
                        'import jakarta.annotation.Resource;\n'
                        'import xiaozhi.modules.agent.service.AgentService;')
    text = replace_once(text, '    private final DeviceDao deviceDao;',
                        '    @Lazy\n    @Resource\n    private AgentService miaAgentService;\n\n'
                        '    private final DeviceDao deviceDao;')
    text = replace_once(text, '    @Override\n    public Boolean deviceActivation(String agentId, String activationCode) {',
                        '    private void requireMiaAgentPermission(String agentId, Long userId) {\n'
                        '        if (userId == null) {\n'
                        '            throw new RenException(ErrorCode.USER_NOT_LOGIN);\n'
                        '        }\n'
                        '        if (!miaAgentService.checkAgentPermission(agentId, userId)) {\n'
                        '            throw new RenException(ErrorCode.NO_PERMISSION);\n'
                        '        }\n'
                        '    }\n\n'
                        '    @Override\n    @Transactional(rollbackFor = Exception.class)\n'
                        '    public Boolean deviceActivation(String agentId, String activationCode) {\n'
                        '        requireMiaAgentPermission(agentId, SecurityUser.getUser().getId());')
    text = replace_once(text, '    public void manualAddDevice(Long userId, DeviceManualAddDTO dto) {',
                        '    @Transactional(rollbackFor = Exception.class)\n'
                        '    public void manualAddDevice(Long userId, DeviceManualAddDTO dto) {\n'
                        '        requireMiaAgentPermission(dto.getAgentId(), userId);')
    text = replace_once(text, '    public void unbindDevice(Long userId, String deviceId) {',
                        '    @Transactional(rollbackFor = Exception.class)\n'
                        '    public void unbindDevice(Long userId, String deviceId) {')
    return replace_once(text, '        String macAddress = device.getMacAddress();\n',
                        '        if (userId == null || !userId.equals(device.getUserId())) {\n'
                        '            throw new RenException(ErrorCode.NO_PERMISSION);\n'
                        '        }\n'
                        '        String macAddress = device.getMacAddress();\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('upstream', type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    try:
        path = args.upstream / TARGET
        original = path.read_text(encoding='utf-8')
        if hashlib.sha256(original.encode()).hexdigest() != PREIMAGE:
            raise ValueError('Refusing unreviewed DeviceServiceImpl: requires fixed clean manager baseline')
        changed = binding_guards(original)
        if args.apply:
            backup = path.with_name(path.name + '.mia-identity-original')
            if backup.exists():
                raise ValueError('Identity backup exists; refusing to overwrite')
            shutil.copy2(path, backup)
            try:
                path.write_text(changed, encoding='utf-8')
            except OSError:
                shutil.copy2(backup, path)
                raise
            print('Installed necessary binding guards on isolated source; rebuild required, no database changed.')
        else:
            print(''.join(difflib.unified_diff(original.splitlines(True), changed.splitlines(True),
                                             fromfile='a/' + TARGET, tofile='b/' + TARGET)), end='')
    except (OSError, ValueError) as error:
        parser.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()
