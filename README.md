# nvidia-prime-desktop-patcher

~~为常用桌面应用（.desktop 启动器）注入 PRIME Offload 环境变量，并可选地（加 --desktop）为 GNOME/KDE 整个会话注入，从而在混合显卡机型上用 NVIDIA 独显运行。~~
其实就是我开独显waydroid会崩所以才弄了这个


## 功能
- 为常用应用开启独显
- 为桌面环境开启独显
- 安全写入：系统会话不直接修改，采用用户覆盖可随时删除回滚。

## 适用场景
~~我的电脑~~
- Laptop/PC 带核显+NVIDIA 独显，希望仅在需要时用独显渲染应用或整个桌面。

## 参数

- `--add QUERY_OR_PATH [QUERY_OR_PATH ...]`
	- 为匹配的应用 .desktop 启动器注入 PRIME；支持传入关键字或 .desktop 的绝对路径。
	- 关键字模式下会列出候选项：
		- 输出形如：`找到以下可能的 .desktop 项：` 然后编号列表
		- 提示：`输入要add的编号（逗号分隔），或 a 全选，q 取消：`
	- 示例：
		- `sudo python nvidia-prime-desktop-patcher.py --add qq`
		- `sudo python nvidia-prime-desktop-patcher.py --add /usr/share/applications/qq.desktop`

- `--desktop [QUERY]`
	- 处理桌面会话文件（如 GNOME/KDE），支持可选关键字过滤；进入交互式选择：
		- 输出形如：`找到以下可能的 .desktop 项：` 然后编号列表
		- 提示：`输入要add的编号（逗号分隔），或 a 全选，q 取消：`
	- 不带参数显示所有会话；带参数仅显示名称或文件名包含该关键字的会话。
	- 示例：
		- `sudo python nvidia-prime-desktop-patcher.py --desktop`
		- `sudo python nvidia-prime-desktop-patcher.py --desktop kde`

- `--rollback [QUERY]`
	- 回滚修改；不带参数回滚全部（应用 + 会话相关）；带参数则按关键字检索并交互选择回滚项。
	- 交互模式提示：`输入要回滚的编号（逗号分隔），或 a 全选，q 取消：`
	- 示例：
		- `sudo python nvidia-prime-desktop-patcher.py --rollback`
		- `sudo python nvidia-prime-desktop-patcher.py --rollback qq`

- `--all`
	- 按内置的常用应用关键字列表批量注入 PRIME（非交互）。

提示：需要 root 权限，并且仅在检测到 NVIDIA 独显/驱动时才会执行修改。



## 工作原理简述
- 遍历 `/usr/share/applications` 与 `~/.local/share/applications` 下的 `*.desktop`，匹配常用应用关键字，将 Exec 行前置 `env __NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia`。
- 扫描系统会话目录，识别 GNOME/KDE 会话，将修改写入用户目录生成一个覆盖版本，不直接修改系统文件。
- 通过 `/dev`、`/proc/driver/nvidia`、`/sys/bus/pci/devices/*/vendor` 与可用的 `nvidia-smi -L` 来检测独显存在性。


