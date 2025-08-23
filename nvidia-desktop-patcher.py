import os
import glob
import argparse
import sys
import shutil
import subprocess
import shlex
from typing import Callable, List, Tuple


def safe_edit_file(path: str,
                   mutator: Callable[[List[str]], Tuple[List[str], bool]],
                   backup: bool = False,
                   action: str = 'Updated') -> bool:
    """通用文件编辑器：读取 -> 变更 -> 写回。

    参数:
    - path: 目标文件路径
    - mutator: 接收原始行列表，返回 (新行列表, 是否变更)
    - backup: 是否在写入前生成 .bak 备份（若不存在）
    - action: 变更时打印的动作名称

    返回:
    - bool: 是否发生变更并写回成功
    """
    try:
        with open(path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except (FileNotFoundError, PermissionError) as e:
        print(f'Skip {path}: {e}')
        return False
    except Exception as e:
        print(f'Failed to read {path}: {e}')
        return False

    try:
        new_lines, changed = mutator(lines)
    except Exception as e:
        print(f'Mutation error on {path}: {e}')
        return False

    if not changed:
        return False

    if backup:
        try:
            bak = path + '.bak'
            if not os.path.exists(bak):
                shutil.copy2(path, bak)
        except Exception as e:
            # 备份失败不应阻止写入，但给出提示
            print(f'Warning: 备份失败 {path} -> {e}')

    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        print(f'{action}: {path}')
        return True
    except Exception as e:
        print(f'Failed to write {path}: {e}')
        return False

PRIME_ENV = 'env __NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia'
DESKTOP_DIRS = [
    '/usr/share/applications',
    os.path.expanduser('~/.local/share/applications')
]
# 系统会话与用户会话 .desktop 路径
SYSTEM_SESSION_DIRS = [
    '/usr/share/wayland-sessions',
]
USER_SESSION_DIRS = [
    os.path.expanduser('~/.local/share/wayland-sessions'),
]
# 常见应用关键词（不包含桌面环境专有关键字）
COMMON_APPS_BASE = [
    # Browsers
    'firefox', 'chrome', 'chromium', 'brave', 'vivaldi', 'opera', 'librewolf', 'waterfox', 'edge', 'tor', 'epiphany', 'falkon',
    # IDEs / Editors
    'code', 'code-insiders', 'vscodium', 'codium', 'sublime', 'pycharm', 'idea', 'clion', 'goland', 'webstorm', 'rider', 'datagrip',
    'android-studio', 'atom', 'kate', 'gedit', 'notepadqq', 'neovide', 'nvim-qt',
    # Desktop Environments / Shells
    'yakuake', 'xfce4-terminal', 'mate-terminal', 'tilix', 'alacritty', 'kitty',
    # File managers
    'nautilus', 'nemo', 'thunar', 'dolphin', 'pcmanfm', 'doublecmd',
    # Office / Productivity（）
    'libreoffice', 'onlyoffice', 'wps', 'wpp', 'okular' , 'xreader', 'atril', 'zathura', 'xmind', 'obsidian', 'zotero',
    # Graphics / Media
    'gimp', 'inkscape', 'krita', 'pinta', 'blender', 'shotwell', 'darktable', 'rawtherapee',
    'vlc', 'mpv', 'rhythmbox', 'audacious', 'audacity', 'kdenlive', 'shotcut', 'handbrake', 'obs', 'obs-studio', 'cheese', 'pavucontrol',
    # Messaging / Communication / Social
    'slack', 'discord', 'telegram', 'element', 'signal', 'thunderbird', 'teams', 'zoom', 'skype', 'feishu', 'lark', 'wecom', 'whatsapp', 'wechat', 'qq',
    # Cloud / Sync
    'dropbox', 'insync', 'megasync', 'nextcloud',
    # Virtualization / Containers
    'virtualbox', 'vmware', 'virt-manager', 'qemu', 'gns3',
    # Gaming
    'steam', 'lutris', 'heroic', 'bottles',
    # Download / Network
    'qbittorrent', 'transmission', 'motrix', 'filezilla',
]


ALLOW_SHORT_KEYWORDS = {'qq'}  # 允许的短关键字白名单

def _should_patch_exec(exec_cmd: str, keywords) -> bool:
    try:
        # 删除字段代码，保留原次序
        parts = [p for p in shlex.split(exec_cmd) if not p.startswith('%')]
    except Exception:
        parts = exec_cmd.split()
    # 跳过 env 与变量赋值
    i = 0
    if i < len(parts) and parts[i] == 'env':
        i += 1
        while i < len(parts) and '=' in parts[i] and not parts[i].startswith('-'):
            i += 1
    # 候选 token：前 3-4 个非选项 token
    candidates = []
    while i < len(parts) and len(candidates) < 4:
        tok = parts[i]
        i += 1
        if tok.startswith('-'):
            continue
        candidates.append(tok.lower())
    if not candidates:
        candidates = [exec_cmd.lower()]
    for key in keywords:
        if len(key) < 3 and key not in ALLOW_SHORT_KEYWORDS:
            continue
        k = key.lower()
        for tok in candidates:
            if k in tok:
                return True
    return False

def patch_desktop_file(path, keywords):
    def _mutator(lines: List[str]) -> Tuple[List[str], bool]:
        changed = False
        for i, line in enumerate(lines):
            if line.startswith('Exec=') and PRIME_ENV not in line:
                exec_cmd = line[len('Exec='):].strip()
                if _should_patch_exec(exec_cmd, keywords):
                    # 避免重复添加
                    if not exec_cmd.startswith(PRIME_ENV):
                        lines[i] = f'Exec={PRIME_ENV} {exec_cmd}\n'
                        changed = True
        return lines, changed

    safe_edit_file(path, _mutator, backup=False, action='Patched')

def _strip_prime_prefix_from_exec(line: str) -> str:
    """若 Exec 行包含 PRIME 前缀则移除，否则原样返回。"""
    if not line.startswith('Exec='):
        return line
    exec_cmd = line[len('Exec='):].lstrip()
    prefix = PRIME_ENV + ' '
    if exec_cmd.startswith(prefix):
        return 'Exec=' + exec_cmd[len(prefix):] + ('\n' if not line.endswith('\n') else '')
    return line

def rollback_desktop_file(path: str) -> bool:
    """从单个 .desktop 的 Exec 行移除 PRIME 前缀。返回是否有修改。"""
    def _mutator(lines: List[str]) -> Tuple[List[str], bool]:
        changed = False
        new_lines: List[str] = []
        for line in lines:
            new_line = _strip_prime_prefix_from_exec(line)
            if new_line != line:
                changed = True
            new_lines.append(new_line)
        return new_lines, changed

    return safe_edit_file(path, _mutator, backup=False, action='Rolled back')

def has_nvidia_dgpu() -> bool:
    """尽量无依赖地检测是否存在 NVIDIA 独显及驱动。
    返回 True 表示可以尝试使用 PRIME offload。
    """
    # 1) 驱动暴露的设备节点或 /proc 信息
    if os.path.exists('/dev/nvidiactl') or os.path.isdir('/proc/driver/nvidia/gpus') or os.path.exists('/proc/driver/nvidia/version'):
        return True
    # 2) 通过 sysfs 检查 PCI 设备供应商 ID（0x10de 为 NVIDIA）
    sysfs_root = '/sys/bus/pci/devices'
    try:
        for dev in glob.glob(os.path.join(sysfs_root, '*/vendor')):
            try:
                with open(dev, 'r', encoding='utf-8', errors='ignore') as f:
                    vendor = f.read().strip().lower()
                if vendor == '0x10de':
                    return True
            except Exception:
                continue
    except Exception:
        pass
    # 3) 可选：调用 nvidia-smi 验证（若存在）
    nvsmi = shutil.which('nvidia-smi')
    if nvsmi:
        try:
            out = subprocess.run([nvsmi, '-L'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=2)
            if out.returncode == 0 and out.stdout:
                return True
        except Exception:
            pass
    return False

def ensure_dir(path: str):
    try:
        os.makedirs(path, exist_ok=True)
    except Exception as e:
        print(f'Failed to ensure dir {path}: {e}')

def _classify_session(lines):
    """基于文件内容简单判断是 GNOME 还是 KDE 会话。返回 'gnome' | 'kde' | None"""
    joined = '\n'.join(lines).lower()
    # 常见 Exec/Name 识别
    if 'gnome' in joined or 'gnome-session' in joined:
        return 'gnome'
    if 'plasma' in joined or 'startplasma' in joined or 'kde' in joined:
        return 'kde'
    return None

def _dest_session_dir(src_path: str):
    return os.path.expanduser('~/.local/share/wayland-sessions')

def patch_session_inplace(src_path: str, want: str):
    """直接在系统会话 .desktop 中原地写入（先备份 .bak）。
    want: 'gnome'|'kde'|'both'
    """
    def _mutator(lines: List[str]) -> Tuple[List[str], bool]:
        sess = _classify_session(lines)
        if want != 'both' and sess != want:
            return lines, False
        changed = False
        new_lines = list(lines)
        for i, line in enumerate(new_lines):
            if line.startswith('Exec=') and PRIME_ENV not in line:
                exec_cmd = line[len('Exec='):].strip()
                if not exec_cmd.startswith(PRIME_ENV):
                    new_lines[i] = f'Exec={PRIME_ENV} {exec_cmd}\n'
                    changed = True
        return new_lines, changed

    safe_edit_file(src_path, _mutator, backup=True, action='Patched session (inplace)')


def _session_file_contains_prime(path: str) -> bool:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('Exec=') and PRIME_ENV in line:
                    return True
    except Exception:
        pass
    return False

def rollback_sessions_all():
    """回滚会话修改：删除用户覆盖，并移除系统会话文件中的 PRIME 前缀。"""
    total = 0
    # 删除用户覆盖文件
    for d in USER_SESSION_DIRS:
        if not os.path.isdir(d):
            continue
        for file in glob.glob(os.path.join(d, '*.desktop')):
            if _session_file_contains_prime(file):
                try:
                    os.remove(file)
                    print(f'Removed session override: {file}')
                    total += 1
                except Exception as e:
                    print(f'Failed to remove session {file}: {e}')
    # 回滚系统会话文件（原地去除前缀）
    for d in SYSTEM_SESSION_DIRS:
        if not os.path.isdir(d):
            continue
        for file in glob.glob(os.path.join(d, '*.desktop')):
            try:
                if rollback_desktop_file(file):
                    total += 1
            except Exception:
                continue
    return total

def _desktop_name_from_file(path: str) -> str:
    name = ''
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('Name='):
                    name = line[len('Name='):].strip()
                    break
    except Exception:
        pass
    return name

def _search_candidates(query: str):
    """按 query 在应用与会话 .desktop 中检索候选项。返回 [(kind, path, title)]。
    kind: 'app' | 'session'
    title: 友好名称（Name 或文件名）
    """
    q = (query or '').lower()
    results = []
    # apps
    for d in DESKTOP_DIRS:
        if not os.path.isdir(d):
            continue
        for file in glob.glob(os.path.join(d, '*.desktop')):
            base = os.path.basename(file).lower()
            if q in base:
                results.append(('app', file, _desktop_name_from_file(file) or os.path.basename(file)))
                continue
            nm = _desktop_name_from_file(file).lower()
            if q and q in nm:
                results.append(('app', file, _desktop_name_from_file(file) or os.path.basename(file)))
    # sessions (用户覆盖优先，其次系统)
    for d in USER_SESSION_DIRS + SYSTEM_SESSION_DIRS:
        if not os.path.isdir(d):
            continue
        for file in glob.glob(os.path.join(d, '*.desktop')):
            base = os.path.basename(file).lower()
            if q in base:
                results.append(('session', file, _desktop_name_from_file(file) or os.path.basename(file)))
                continue
            nm = _desktop_name_from_file(file).lower()
            if q and q in nm:
                results.append(('session', file, _desktop_name_from_file(file) or os.path.basename(file)))
    return results

def rollback_all():
    """回滚所有修改：应用 .desktop 去掉前缀 + 删除用户会话覆盖。"""
    app_count = 0
    for d in DESKTOP_DIRS:
        if not os.path.isdir(d):
            continue
        for file in glob.glob(os.path.join(d, '*.desktop')):
            if rollback_desktop_file(file):
                app_count += 1
    sess_count = rollback_sessions_all()
    print(f'Rollback done. apps={app_count}, sessions_removed={sess_count}')

def _patch_session_dir_all():
    """对系统 Wayland 会话文件进行原地注入（备份 .bak）。"""
    for d in SYSTEM_SESSION_DIRS:
        if not os.path.isdir(d):
            continue
        for file in glob.glob(os.path.join(d, '*.desktop')):
            patch_session_inplace(file, 'both')

def desktop_interactive(query: str = None):
    """交互式选择桌面会话文件进行PRIME注入。"""
    q = (query or '').lower()
    # 收集所有会话文件
    session_files = []
    for d in SYSTEM_SESSION_DIRS:
        if not os.path.isdir(d):
            continue
        for file in glob.glob(os.path.join(d, '*.desktop')):
            base = os.path.basename(file).lower()
            title = _desktop_name_from_file(file) or os.path.basename(file)
            name_l = title.lower()
            if q and (q not in base and q not in name_l):
                continue
            session_files.append(('session', file, title))
    
    if not session_files:
        print('未找到桌面会话文件。')
        return
    
    print('找到以下可能的 .desktop 项：')
    for idx, (kind, path, title) in enumerate(session_files, 1):
        print(f'  [{idx}] {kind}: {title} -> {path}')
    
    sel = input('输入要add的编号（逗号分隔），或 a 全选，q 取消：').strip().lower()
    if sel in ('q'):
        print('已取消。')
        return
    
    indexes = []
    if sel in ('a'):
        indexes = list(range(1, len(session_files)+1))
    else:
        try:
            for part in sel.split(','):
                part = part.strip()
                if part:
                    indexes.append(int(part))
        except Exception:
            print('输入无效，已取消。')
            return
    
    total = 0
    for i in indexes:
        if i < 1 or i > len(session_files):
            continue
        kind, path, _ = session_files[i-1]
        try:
            patch_session_inplace(path, 'both')
            total += 1
        except Exception as e:
            print(f'Patch failed for {path}: {e}')
    
    if total:
        print(f'Added PRIME to {total} session target(s).')
    return total

def add_targets(items):
    """根据提供的路径或关键字为 .desktop 注入 PRIME 环境。
    """
    total = 0
    for it in items or []:
        it = it.strip()
        if not it:
            continue
        # 直接路径
        if os.path.exists(it) and it.endswith('.desktop'):
            try:
                patch_desktop_file(it, COMMON_APPS_BASE)
                total += 1
            except Exception as e:
                print(f'Skip {it}: {e}')
            continue
        # 关键字检索
        cands = _search_candidates(it)
        if not cands:
            print(f'未找到匹配：{it}')
            continue
        
        # 只保留 app 类型的候选项
        app_cands = [(kind, path, title) for kind, path, title in cands if kind == 'app']
        if not app_cands:
            print(f'未找到匹配的应用：{it}')
            continue
        
        # 显示找到的候选项
        print('找到以下可能的 .desktop 项：')
        for idx, (kind, path, title) in enumerate(app_cands, 1):
            print(f'  [{idx}] {kind}: {title} -> {path}')
        
        # 交互式选择
        sel = input('输入要add的编号（逗号分隔），或 a 全选，q 取消：').strip().lower()
        if sel in ('q'):
            print('已取消。')
            continue
        
        indexes = []
        if sel in ('a'):
            indexes = list(range(1, len(app_cands)+1))
        else:
            try:
                for part in sel.split(','):
                    part = part.strip()
                    if part:
                        indexes.append(int(part))
            except Exception:
                print('输入无效，已取消。')
                continue
        
        # 处理选中的项
        for i in indexes:
            if i < 1 or i > len(app_cands):
                continue
            kind, path, _ = app_cands[i-1]
            try:
                patch_desktop_file(path, COMMON_APPS_BASE)
                total += 1
            except Exception as e:
                print(f'Patch failed for {path}: {e}')
    if total:
        print(f'Added PRIME to {total} target(s).')
    return total

def rollback_interactive(query: str):
    """按关键字检索，交互式选择回滚项。"""
    candidates = _search_candidates(query)
    if not candidates:
        print('未找到匹配项。')
        return
    print('找到以下可能的 .desktop 项：')
    for idx, (kind, path, title) in enumerate(candidates, 1):
        print(f'  [{idx}] {kind}: {title} -> {path}')
    sel = input('输入要回滚的编号（逗号分隔），或 a 全选，q 取消：').strip().lower()
    if sel in ('q', 'quit', 'exit', ''):
        print('已取消。')
        return
    indexes = []
    if sel in ('a', 'all'):
        indexes = list(range(1, len(candidates)+1))
    else:
        try:
            for part in sel.split(','):
                part = part.strip()
                if part:
                    indexes.append(int(part))
        except Exception:
            print('输入无效，已取消。')
            return
    for i in indexes:
        if i < 1 or i > len(candidates):
            continue
        kind, path, _ = candidates[i-1]
        if kind == 'app':
            rollback_desktop_file(path)
        else:
            # 对会话：删除用户覆盖（若选择的是系统会话，将尝试删除对应名称在用户目录的覆盖文件）
            user_dir = _dest_session_dir(path)
            override_path = os.path.join(user_dir, os.path.basename(path))
            target_path = override_path if os.path.exists(override_path) else path
            try:
                if os.path.commonpath([target_path, os.path.expanduser('~')]) == os.path.expanduser('~'):
                    # 仅删除用户目录下文件
                    os.remove(target_path)
                    print(f'Removed session override: {target_path}')
                else:
                    # 系统会话不直接删；若其 Exec 有前缀则进行去除
                    if not rollback_desktop_file(target_path):
                        print(f'未修改系统会话：{target_path}')
            except Exception as e:
                print(f'Failed to handle session {target_path}: {e}')



def main():
    parser = argparse.ArgumentParser(description='为常用应用开启独显')
    parser.add_argument('--rollback', nargs='?', const='__ALL__', metavar='QUERY',
                        help='回滚修改；不带参数回滚全部；带参数则按关键字检索并交互选择回滚项。')
    parser.add_argument('--desktop', nargs='?', const='__ALL__', metavar='QUERY',
                        help='处理桌面会话文件；不带参数显示所有会话；带参数按关键字过滤并交互选择。')
    parser.add_argument('--add', nargs='+', metavar='QUERY_OR_PATH',
                        help='按路径或关键字添加')
    parser.add_argument('--all', action='store_true',
                        help='处理常用应用列表')
    args = parser.parse_args()

    # 回滚模式优先执行
    if args.rollback is not None:
        if args.rollback == '__ALL__':
            rollback_all()
        else:
            rollback_interactive(args.rollback)
        return

    if not (args.desktop or args.add or args.all):
        parser.print_help()
        return

    # 必须以 root 运行（便于修改系统目录 /usr/share/...）；若不是则退出
    try:
        if hasattr(os, 'geteuid') and os.geteuid() != 0:
            print('无root权限')
            return
    except Exception:
        pass

    # 运行前先检测是否存在 NVIDIA 独显与驱动
    if not has_nvidia_dgpu():
        print('未检测到 NVIDIA 独显或驱动，未进行任何修改。')
        return

    # 分支：优先处理 --add；否则按 --desktop 或 --all
    if args.add:
        add_targets(args.add)
        return
    if args.desktop is not None:
        query = None if args.desktop == '__ALL__' else args.desktop
        desktop_interactive(query)
        return
    # --all：处理常用应用 .desktop 列表
    if args.all:
        keywords = list(COMMON_APPS_BASE)
        for d in DESKTOP_DIRS:
            if not os.path.isdir(d):
                continue
            for file in glob.glob(os.path.join(d, '*.desktop')):
                patch_desktop_file(file, keywords)

if __name__ == '__main__':
    main()