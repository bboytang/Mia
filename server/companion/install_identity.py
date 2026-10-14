"""Review/apply necessary binding guards to the fixed manager source only."""

import argparse
import difflib
import hashlib
from pathlib import Path
import shutil

from .install_xiaozhi import replace_once


TARGET = 'main/manager-api/src/main/java/xiaozhi/modules/device/service/impl/DeviceServiceImpl.java'
SHIRO = 'main/manager-api/src/main/java/xiaozhi/modules/security/config/ShiroConfig.java'
DAO = 'main/manager-api/src/main/java/xiaozhi/modules/device/dao/DeviceDao.java'
MASTER = 'main/manager-api/src/main/resources/db/changelog/db.changelog-master.yaml'
PREIMAGES = {
    TARGET: '26f5d6acbc8680232da1d8f2d8b5ad43eeaee04d4c35323f7c0f31505ce76743',
    SHIRO: '7ee4c8d5c1e53ededc107ddb92e4593aa61d88a398fc05fac5c4bf6b9809eae5',
    DAO: '0b348fdc6079c68119d547e8a95dc9f996d25a3490815888bfec2566bfcc9e1d',
    MASTER: 'b2c8039189f12b414811b85527e612ea970231799476ef8661f5dfd2c09005d0',
}
PAYLOADS = {
    'MiaDeviceAuthorizationService.java': 'main/manager-api/src/main/java/xiaozhi/modules/device/service/impl/MiaDeviceAuthorizationService.java',
    'MiaDeviceAuthorizationController.java': 'main/manager-api/src/main/java/xiaozhi/modules/device/controller/MiaDeviceAuthorizationController.java',
    '202610141825.sql': 'main/manager-api/src/main/resources/db/changelog/202610141825.sql',
}


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
    text = replace_once(text, '        String macAddress = device.getMacAddress();\n',
                        '        if (userId == null || !userId.equals(device.getUserId())) {\n'
                        '            throw new RenException(ErrorCode.NO_PERMISSION);\n'
                        '        }\n'
                        '        String macAddress = device.getMacAddress();\n')
    text = replace_once(text, '    private AgentService miaAgentService;\n',
                        '    private AgentService miaAgentService;\n\n'
                        '    @Lazy\n    @Resource\n    private MiaDeviceAuthorizationService miaPrivateGrants;\n')
    text = replace_once(text, '        deviceDao.insert(deviceEntity);\n',
                        '        deviceDao.insert(deviceEntity);\n        miaPrivateGrants.bindingChanged(deviceId);\n')
    text = replace_once(text, '        baseDao.insert(entity);\n',
                        '        baseDao.insert(entity);\n        miaPrivateGrants.bindingChanged(entity.getId());\n')
    text = replace_once(text, '        // 先查询设备信息，获取agentId和macAddress\n'
                        '        DeviceEntity device = baseDao.selectById(deviceId);\n',
                        '        // 先查询设备信息，获取agentId和macAddress\n'
                        '        DeviceEntity device = deviceDao.selectBindingForUpdate(deviceId);\n')
    text = replace_once(text, '        baseDao.delete(wrapper);\n\n        // 删除设备相关的通讯录权限记录',
                        '        baseDao.delete(wrapper);\n        miaPrivateGrants.bindingChanged(deviceId);\n\n'
                        '        // 删除设备相关的通讯录权限记录')
    text = replace_once(text,
                        '    public void deleteByUserId(Long userId) {\n'
                        '        UpdateWrapper<DeviceEntity> wrapper = new UpdateWrapper<>();\n'
                        '        wrapper.eq("user_id", userId);\n        baseDao.delete(wrapper);\n    }',
                        '    @Transactional(rollbackFor = Exception.class)\n'
                        '    public void deleteByUserId(Long userId) {\n'
                        '        UpdateWrapper<DeviceEntity> wrapper = new UpdateWrapper<>();\n'
                        '        wrapper.eq("user_id", userId);\n        baseDao.delete(wrapper);\n'
                        '        miaPrivateGrants.userDeleted(userId);\n    }')
    text = replace_once(text, '    public void deleteByAgentId(String agentId) {',
                        '    @Transactional(rollbackFor = Exception.class)\n'
                        '    public void deleteByAgentId(String agentId) {')
    return replace_once(text, '        baseDao.delete(wrapper);\n\n        // 批量删除这些设备相关的所有通讯录权限记录',
                        '        baseDao.delete(wrapper);\n        miaPrivateGrants.agentDeleted(agentId);\n\n'
                        '        // 批量删除这些设备相关的所有通讯录权限记录')


def build_changes(root):
    originals = {}
    for name, digest in PREIMAGES.items():
        original = (root / name).read_text(encoding='utf-8')
        if hashlib.sha256(original.encode()).hexdigest() != digest:
            raise ValueError(f'Refusing unreviewed source: {name}; requires fixed manager baseline')
        originals[name] = original
    changed = {
        TARGET: binding_guards(originals[TARGET]),
        SHIRO: replace_once(originals[SHIRO], '        filterMap.put("/**", "oauth2");',
                            '        filterMap.put("/device/mia-auth/exchange", "anon");\n'
                            '        filterMap.put("/device/mia-auth/renew", "anon");\n'
                            '        filterMap.put("/**", "oauth2");'),
        DAO: replace_once(originals[DAO], '    Date getAllLastConnectedAtByAgentId(String agentId);',
                          '    Date getAllLastConnectedAtByAgentId(String agentId);\n\n'
                          '    @org.apache.ibatis.annotations.Select("SELECT id,user_id AS userId,agent_id AS agentId,mac_address AS macAddress FROM ai_device WHERE id=#{id} FOR UPDATE")\n'
                          '    DeviceEntity selectBindingForUpdate(@org.apache.ibatis.annotations.Param("id") String id);'),
        MASTER: originals[MASTER].rstrip('\n') + '\n  - changeSet:\n'
                '      id: 202610141825\n      author: Mia\n      changes:\n'
                '        - sqlFile:\n            encoding: utf8\n'
                '            path: classpath:db/changelog/202610141825.sql\n',
    }
    return {name: (originals[name], content) for name, content in changed.items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('upstream', type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    try:
        changes = build_changes(args.upstream)
        payload_root = Path(__file__).parent / 'manager_identity'
        if args.apply:
            if any((args.upstream / (name + '.mia-identity-original')).exists() for name in changes):
                raise ValueError('Identity backup exists; refusing to overwrite')
            if any((args.upstream / name).exists() for name in PAYLOADS.values()):
                raise ValueError('Private grant payload already exists; refusing to overwrite')
            for name in changes:
                shutil.copy2(args.upstream / name, args.upstream / (name + '.mia-identity-original'))
            copied = []
            try:
                for name, (_, changed) in changes.items():
                    (args.upstream / name).write_text(changed, encoding='utf-8')
                for source, destination in PAYLOADS.items():
                    shutil.copy2(payload_root / source, args.upstream / destination)
                    copied.append(args.upstream / destination)
            except OSError:
                for name in changes:
                    shutil.copy2(args.upstream / (name + '.mia-identity-original'), args.upstream / name)
                for path in copied:
                    path.unlink()
                raise
            print('Installed necessary identity source patch; rebuild/migration required, no running database changed.')
        else:
            for name, (original, changed) in changes.items():
                print(''.join(difflib.unified_diff(original.splitlines(True), changed.splitlines(True),
                                                 fromfile='a/' + name, tofile='b/' + name)), end='')
            for source, destination in PAYLOADS.items():
                content = (payload_root / source).read_text(encoding='utf-8')
                print(''.join(difflib.unified_diff([], content.splitlines(True),
                                                 fromfile='/dev/null', tofile='b/' + destination)), end='')
    except (OSError, ValueError) as error:
        parser.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()
