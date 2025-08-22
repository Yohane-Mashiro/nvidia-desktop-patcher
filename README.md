# nvidia-prime-desktop-patcher

~~为常用桌面应用（.desktop 启动器）注入 PRIME Offload 环境变量，并可选地（加 --desktop）为 GNOME/KDE 整个会话注入，从而在混合显卡机型上用 NVIDIA 独显运行。~~

其实就是我开独显waydroid会崩所以才弄了这个


## 功能
- 为常用应用开启独显
- 为桌面环境开启独显
- 安全写入：系统会话不直接修改，采用用户覆盖可随时删除回滚。

## 适用场景
~~我的电脑~~
- 带核显+NVIDIA 独显的电脑，希望仅在需要时用独显渲染应用或整个桌面。

## 参数

| 参数 | 说明 | 示例 |
| --- | --- | --- |
| `--add QUERY_OR_PATH [QUERY_OR_PATH ...]` | 为匹配的应用 .desktop 打开独显启动；支持关键字或 .desktop 的绝对路径。<br>关键字模式会列出候选项并提示：`输入要add的编号（逗号分隔），或 a 全选，q 取消`。 | `sudo python nvidia-desktop-patcher.py --add qq`<br>`sudo python nvidia-desktop-patcher.py --add /usr/share/applications/qq.desktop` |
| `--desktop [QUERY]` | 处理桌面会话文件（GNOME/KDE 等），可选关键字过滤进入交互选择。<br>不带参数显示所有会话；带参数仅显示名称/文件名包含该关键字的会话。<br>交互候选输出形如：`找到以下可能的 .desktop 项：` 然后编号列表；提示同上。 | `sudo python nvidia-desktop-patcher.py --desktop`<br>`sudo python nvidia-desktop-patcher.py --desktop kde` |
| `--rollback [QUERY]` | 回滚修改。不带参数回滚全部（应用 + 会话）；带参数按关键字检索并交互选择回滚项。<br>交互提示：`输入要回滚的编号（逗号分隔），或 a 全选，q 取消`。 | `sudo python nvidia-desktop-patcher.py --rollback`<br>`sudo python nvidia-desktop-patcher.py --rollback qq` |
| `--all` | 按内置的常用应用关键字列表批量设置 | `sudo python nvidia-desktop-patcher.py --all` |

提示：需要 root 权限，并且仅在检测到 NVIDIA 独显/驱动时才会执行修改。
