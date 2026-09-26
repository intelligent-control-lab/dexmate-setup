#!/usr/bin/env python3
"""Build the static bilingual manual using only Python's standard library."""
from pathlib import Path
from html import escape
import json

ROOT=Path(__file__).resolve().parents[1]
DOC=ROOT/'docs'
sections=[]
DIMENSIONS=json.loads((DOC/'assets/dimensions.json').read_text())
def code(s): return '<div class="code"><button class="copy" type="button">Copy</button><pre><code>'+escape(s.strip())+'</code></pre></div>'
def note(s): return '<aside class="note">'+s+'</aside>'
def fig(file,caption): return f'<figure><a href="assets/{file}" target="_blank" rel="noopener"><img src="assets/{file}" alt="{escape(caption)}" width="{DIMENSIONS[file][0]}" height="{DIMENSIONS[file][1]}" loading="lazy"></a><figcaption>{caption}</figcaption></figure>'
def video(n,caption): return f'<figure><video controls playsinline preload="metadata" width="720" height="1280" poster="assets/IMG_{n}-poster.jpg"><source src="assets/IMG_{n}.mp4" type="video/mp4"></video><figcaption>{caption} · <a href="assets/IMG_{n}.mp4" download>MP4</a></figcaption></figure>'
def grid(*items): return '<div class="gallery">'+''.join(items)+'</div>'
def table(head,rows): return '<div class="table-wrap"><table><thead><tr>'+''.join('<th>'+s+'</th>' for s in head)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(v)+'</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table></div>'
def add(id,zh,en,z,e): sections.append((id,zh,en,z,e))
repo='https://github.com/intelligent-control-lab/dexmate-setup'
waves='https://docs.waveshare.com/MAX9296-GMSL-Deser-Module/Jetson-Orin'

add('hardware','一次性硬件安装','One-time hardware setup',
note('<strong>断电后接线。</strong>夹爪使用机器人 24V 供电；Waveshare 板从 Jetson 40-pin 排针取 <strong>5V</strong>。原笔记“2/4 接红 24V”已按附图和官方手册纠正：<strong>2、4 接红色 5V，6 接黑色 GND；这里绝不能接 24V。</strong>')+
'<h3>1 · 夹爪线束与腕部相机</h3><ol><li>使用已组装好的线束：一端接 CAN adapter；左右两侧各有 4-pin / 6-pin 接口。<strong>6-pin 接夹爪，4-pin 接机器人</strong>。按接口键位插合，不根据线色猜测 pinout。</li><li>相机线也必须连接。腕部只接<strong>偏向内部的一侧</strong>，以 IMG_9360 的实际安装方向为准。</li><li>CAN adapter 插到机器人 USB 口。<strong>两个 switch 都拨向 K 一侧</strong>，参照 IMG_9369。这是照片中这一型号的安装方向；不要把它和 Waveshare 的四位 CFG 开关混淆。</li><li>检查线束松弛量与固定位置，避免关节运动牵扯插头。整体走线参考 IMG_9361 与 IMG_9368。</li></ol>'+
grid(fig('IMG_9360.jpg','IMG_9360 · 腕部相机：连接偏向内部的接口。'),fig('IMG_9369.jpg','IMG_9369 · USB-CAN：两个开关都在 K 一侧。'))+
grid(fig('IMG_9361.jpg','IMG_9361 · 双臂、夹爪与相机整体连接示例。'),video('9368','IMG_9368 · 整体线束与 USB-CAN 安装 walkthrough'))+
'<h3>2 · MAX9296 采集板、铜柱与 CSI 排线</h3><ol><li>先用 kit 自带铜柱连接采集板与 PCB；按下图定位电源、CFG 和 CSI 接口。</li><li>连接电源：两根红线分别接 Jetson 40-pin 的 <strong>2 与 4（均为 5V）</strong>，黑线接 <strong>6（GND）</strong>。按编号定位，勿把 1 的 3.3V 或机器人 24V 当作此电源。</li><li>Waveshare CFG 按板上编号 1→4 设置为 <strong>0100</strong>。</li><li>拆下机器人原有铜柱并保存。先用 <strong>15mm 铜柱固定钢架</strong>，再接 <strong>10mm 铜柱</strong>安装剩余内存／存储组件及风扇。确认堆叠后的绝缘间隙、风扇空间和排线弯曲半径。</li><li>如果拿到<strong>母母相机线</strong>：拆开机内通往腕部相机的连接，接到采集板。如果拿到<strong>公母相机线</strong>：拆下机器人后盖的外部相机接口，以公母线直接连接；IMG_9277 演示的是这一种。</li><li>拆除原先接 Jetson <strong>CAM1</strong> 的排线，换用 kit 附带排线，连接 <strong>Jetson CAM1 ↔ Waveshare CSI0</strong>。不要理解成将原先的整个相机链路随意转接。头部 ZED Link 保留在 <strong>CAM0</strong>；双腕 Waveshare 使用 CAM1。</li><li>连接后逐一核对电源极性、锁扣、走线和固定件，再通电。</li></ol>'+
grid(fig('waveshare-power.webp','Waveshare 官方参考 · 双红线接 5V，黑线接 GND。'),fig('jetson-pinout.png','40-pin 编号：2 = 5V，4 = 5V，6 = GND。'))+
grid(fig('waveshare-switch.webp','Waveshare CFG · 按 1、2、3、4 顺序设置 0100。'),fig('IMG_9276.jpg','IMG_9276 · 实际 CSI 排线与安装堆叠近照。'))+
grid(video('9277','IMG_9277 · 公母相机线、后盖接口与内部 PCB 安装 walkthrough'),fig('waveshare-kit.webp','Waveshare kit · 采集板与双 GMSL 链路示意。'))+
fig('jetson-board.jpg','Jetson 载板外观参考；以实际 PCB 上 CAM0 / CAM1 丝印为准。')+
note('<strong>保存全部拆下来的零件：</strong>原铜柱、后盖接口、原排线、螺丝与支架分别装袋标记。机器人之后需要归还，必须能恢复原状。')+f'<p class="source">接线依据：用户现场照片和说明；电源、CSI 与 CFG 已核对 <a href="{waves}">Waveshare 官方 Jetson Orin 文档</a>。铜柱尺寸是本机器人现场安装方案。</p>',
note('<strong>Power off before wiring.</strong> The grippers use the robot’s 24V supply. The Waveshare board uses <strong>5V from the Jetson 40-pin header</strong>. The original “24V on pins 2/4” note is corrected using the supplied pinout and vendor guide: <strong>red leads to pins 2 and 4 (5V); black to pin 6 (GND). Never apply 24V here.</strong>')+
'<h3>1 · Gripper harness and wrist cameras</h3><ol><li>Use the assembled harness: one end connects to the CAN adapter; each arm branch has a 4-pin and a 6-pin connector. <strong>6-pin → gripper; 4-pin → robot.</strong> Respect connector keying; do not infer pinout from wire colors.</li><li>Connect the camera cable too. Use only the <strong>inward-facing wrist camera connection</strong>, as shown in IMG_9360.</li><li>Plug the CAN adapter into the robot’s USB port. Set <strong>both switches toward K</strong>, matching IMG_9369. This orientation applies to the photographed adapter; it is separate from the Waveshare four-position CFG setting.</li><li>Secure the harness with enough slack for joint travel. Refer to IMG_9361 and IMG_9368 for the complete installation.</li></ol>'+
grid(fig('IMG_9360.jpg','IMG_9360 · Connect the inward-facing wrist camera port.'),fig('IMG_9369.jpg','IMG_9369 · USB-CAN adapter: both switches toward K.'))+
grid(fig('IMG_9361.jpg','IMG_9361 · Complete arms, grippers and camera wiring.'),video('9368','IMG_9368 · Overall harness and USB-CAN walkthrough'))+
'<h3>2 · MAX9296 board, standoffs and CSI ribbon</h3><ol><li>Use the kit’s included standoffs to join the capture board and PCB. Locate power, CFG and CSI before installation.</li><li>Connect both red leads to Jetson header <strong>pins 2 and 4 (5V)</strong>, and black to <strong>pin 6 (GND)</strong>. Pin 1 is 3.3V. The robot’s 24V input is a different circuit.</li><li>Set Waveshare CFG to <strong>0100</strong> in numbered switch order 1→4.</li><li>Remove and save the robot’s original standoffs. Secure the steel frame with <strong>15mm standoffs</strong>, then add <strong>10mm standoffs</strong> for the remaining memory/storage assembly and fan. Check insulation clearance, fan clearance and cable bends.</li><li>With a <strong>female-to-female camera cable</strong>, disconnect the internal wrist-camera connection and connect it to the capture board. With a <strong>male-to-female cable</strong>, remove the external-camera connector from the robot’s rear cover and connect directly; IMG_9277 demonstrates this route.</li><li>Remove the ribbon previously attached to Jetson <strong>CAM1</strong>. Use the kit ribbon for <strong>Jetson CAM1 ↔ Waveshare CSI0</strong>. This is a replacement ribbon connection, not a general reroute of the old camera chain. Keep the head’s ZED Link on <strong>CAM0</strong>; Waveshare wrists use CAM1.</li><li>Check polarity, latches, routing and fasteners before powering on.</li></ol>'+
grid(fig('waveshare-power.webp','Waveshare reference · Both red leads to 5V; black to GND.'),fig('jetson-pinout.png','40-pin header: 2 = 5V, 4 = 5V, 6 = GND.'))+
grid(fig('waveshare-switch.webp','Waveshare CFG · 0100 in numbered order 1, 2, 3, 4.'),fig('IMG_9276.jpg','IMG_9276 · Installed CSI ribbon and board stack.'))+
grid(video('9277','IMG_9277 · Male-to-female cable, rear connector and internal PCB walkthrough'),fig('waveshare-kit.webp','Waveshare kit · Capture board and dual GMSL links.'))+
fig('jetson-board.jpg','Jetson carrier reference; identify CAM0 / CAM1 from the actual PCB markings.')+
note('<strong>Keep every removed part.</strong> Bag and label the original standoffs, rear connectors, ribbon cables, screws and brackets. The robot must be returned later and its original assembly must remain recoverable.')+f'<p class="source">Sources: supplied installation notes and media; power, CSI and CFG cross-checked against the <a href="{waves}">Waveshare Jetson Orin guide</a>. Standoff dimensions describe this robot’s installation.</p>')

prereqs=table(['Component','Pinned version / target'],[
['Jetson','Orin Nano 8GB · p3767-0005 + p3768 carrier'],['L4T / kernel','36.5.0 / 5.15.185-tegra · aarch64'],['Python','System Python 3.10'],['Firmware / dexcontrol / dextop','0.5.x / 0.5.0 / 0.5.0'],['dexsensor / ZED SDK','0.7.6 / 5.2.3'],['ZED Link Duo','1.4.3-LI-MAX96712-L4T36.5.0'],['python-can / dexmate-urdf / pin','4.6.1 / 0.8.4 / 4.1.0']])
install=code(r'''git clone https://github.com/intelligent-control-lab/dexmate-setup.git
cd dexmate-setup
/usr/bin/python3 scripts/install.py

# Replace YOUR_SERIAL with this robot's actual identifier.
sudo /usr/bin/python3 scripts/install.py --apply \
  --robot-name dm/YOUR_SERIAL-1u --user dexmate \
  --install-deps --camera-boot --activate-camera-boot --configure-head''')
add('install','新机器人快速安装','Quick installation on a new robot',
'<p>先完成硬件安装、机器人自己的证书与厂商基础环境。以下安装器复制本仓库夹爪库、相机初始化库、位姿脚本、驱动和 systemd 配置；不会刷机、更新固件或自动执行运动。</p>'+prereqs+
'<h3>准备厂商基础环境</h3><p>使用 <a href="https://software.dexmate.ai/packages/dexsensor">Dexmate 软件站</a>的 dexsensor 0.7.6、<a href="https://www.stereolabs.com/developers/release/5.2">Stereolabs ZED SDK 5.2 历史版本页</a>中的 5.2.3，以及对应内核的 ZED Link Duo 1.4.3。先按厂商流程安装，再运行本仓库安装器。完整文件名和 SHA256 在仓库 <code>provenance/vendor-installers.json</code>。这些厂商安装包与证书不在公共 Git 中；Python 依赖从 PyPI 安装，故此流程需要联网。</p>'+install+
'<p>第一条 <code>install.py</code> 只读检查并显示计划。<code>--apply</code> 才会写入；<code>--install-deps</code> 安装 apt 和固定版本 Python 依赖；<code>--camera-boot</code> 基于新机器自身 initrd 生成独立启动文件；<code>--activate-camera-boot</code> 才修改 DEFAULT；<code>--configure-head</code> 备份并替换 dexsensor 模板。只想预先添加启动项时省略 activate 参数。</p>'+
note('脚本严格拒绝不匹配的内核、载板、Python 与 L4T。它保留新机器的 root= 参数和原 Stereolabs 启动项，不复制源机器 PARTUUID。所有被替换的普通文件备份在 <code>/var/backups/dexmate-setup/时间戳/</code>；Python venv、用户组和 systemd enable 状态需按回退说明单独处理。')+
'<h3>安装后</h3><ol><li>检查 <code>/boot/extlinux/extlinux.conf</code> 新增的 <code>DexmateSetupHeadWrists</code> 项。接好显示器和键盘，确认原启动项仍可选。</li><li>安排人工重启；安装器不重启，也不启动 CAN 或相机服务。</li><li>重新登录，使 video / i2c 组权限生效，然后执行下方只读检查。</li><li>按后文分别验收头部、双腕相机和夹爪；位姿运动最后在现场监督下进行。</li></ol>'+code('source /opt/dexmate-setup/env.sh\ncd ~/dexmate-setup\npython3 scripts/doctor.py')+
'<p>此处 <code>~/dexmate-setup</code> 是示例克隆位置。安装位置固定为 <code>/opt/dexmate-setup/{gripper,poses,venv}</code> 与 <code>/opt/wrist-cameras</code>，不会覆盖旧 <code>~/py_scripts</code>。</p>',
'<p>Complete hardware assembly, this robot’s own certificate and vendor base software first. The installer deploys the local gripper library, wrist initialization/API, pose scripts, drivers and services. It does not flash the robot, update firmware or command movement.</p>'+prereqs+
'<h3>Prepare the vendor baseline</h3><p>Install dexsensor 0.7.6 from <a href="https://software.dexmate.ai/packages/dexsensor">Dexmate software</a>, ZED SDK 5.2.3 from the <a href="https://www.stereolabs.com/developers/release/5.2">Stereolabs 5.2 release archive</a>, and ZED Link Duo 1.4.3 for the exact kernel. Follow the vendor installation process first. Exact filenames and hashes are in <code>provenance/vendor-installers.json</code>. Vendor installers and robot certificates are excluded from public Git; Python dependencies come from PyPI, so this process needs Internet access.</p>'+install+
'<p>Running <code>install.py</code> alone only checks and prints a plan. <code>--apply</code> writes changes; <code>--install-deps</code> installs apt and pinned Python packages; <code>--camera-boot</code> builds a separate initrd from this robot’s own image; <code>--activate-camera-boot</code> changes DEFAULT; <code>--configure-head</code> backs up and replaces the dexsensor template. Omit the activate flag to stage an entry without selecting it.</p>'+
note('The installer rejects mismatched kernel, board, Python and L4T versions. It preserves the target machine’s root= arguments and original Stereolabs entry, never copying the source machine’s PARTUUID. Replaced regular files are saved under <code>/var/backups/dexmate-setup/timestamp/</code>. Python environments, group changes and service-enable state require the separate rollback steps.')+
'<h3>After installation</h3><ol><li>Review the new <code>DexmateSetupHeadWrists</code> entry in extlinux. Attach a display and keyboard and verify the fallback entries are available.</li><li>Schedule a manual reboot. The installer neither reboots nor starts CAN/camera services.</li><li>Log in again for video / i2c group membership, then run the read-only check below.</li><li>Accept the head, wrists and grippers separately; perform supervised pose motion last.</li></ol>'+code('source /opt/dexmate-setup/env.sh\ncd ~/dexmate-setup\npython3 scripts/doctor.py')+
'<p><code>~/dexmate-setup</code> is an example clone location. Installed files live in <code>/opt/dexmate-setup/{gripper,poses,venv}</code> and <code>/opt/wrist-cameras</code>; the old <code>~/py_scripts</code> is not overwritten.</p>')

session=code('''ssh dexmate@ROBOT_IP
source /opt/dexmate-setup/env.sh
dextop topic list --timeout 10
dextop doctor check
systemctl status dexsensor wrist-camera-init.service --no-pager
cat /run/wrist-cameras/ready.json''')
add('session','每次使用：连接与检查','Every session: connect and check',
'<p>正常使用只需连接已经配置好的机器人，不要重复一次性安装。WiFi 地址来自 DHCP，可能变化；在机器人屏幕运行 <code>ip -br addr</code> 查看。有线参考地址 Jetson <code>192.168.50.20</code>，SoC <code>192.168.50.21</code>。使用该机器自己的 SSH 凭据。</p>'+session+
'<p><code>ROBOT_NAME</code> 必须是 <code>dm/序列号-1u</code>（斜杠）。非交互 SSH 不读取 <code>~/.bashrc</code>，要显式 source 环境。IP 变化只需更新连接目标，不用重装。</p>'+code('ssh dexmate@ROBOT_IP \'source /opt/dexmate-setup/env.sh; dextop doctor check\'')+
note('<code>Robot()</code> 构造过程可能让头部回到 home，包括 <code>inspect_joints.py</code> 与位姿 <code>--dry-run</code>。只要像素时使用 <code>Sensors()</code>，避免建立 Robot 会话。'),
'<p>For a configured robot, connect and inspect; do not repeat one-time setup. The WiFi DHCP address can change: read <code>ip -br addr</code> at the robot console. Reference wired addresses are Jetson <code>192.168.50.20</code> and SoC <code>192.168.50.21</code>. Use this robot’s own SSH credentials.</p>'+session+
'<p><code>ROBOT_NAME</code> uses <code>dm/SERIAL-1u</code> with a slash. Non-interactive SSH does not source <code>~/.bashrc</code>; source the installed environment explicitly. A changed IP does not require reinstallation.</p>'+code('ssh dexmate@ROBOT_IP \'source /opt/dexmate-setup/env.sh; dextop doctor check\'')+
note('<code>Robot()</code> may home the head during construction, including in <code>inspect_joints.py</code> and pose <code>--dry-run</code>. Use <code>Sensors()</code> directly when you only need images.'))

head=code('''from dexcontrol.core.config import get_robot_config
from dexcontrol.sensors.manager import Sensors

configs = get_robot_config()
configs.sensors["head_camera"].enabled = True
sensors = Sensors({"head_camera": configs.sensors["head_camera"]})
try:
    sensors.wait_for_all_active(timeout=10)
    obs = sensors.head_camera.get_obs(
        obs_keys=["left_rgb", "right_rgb", "depth"], include_timestamp=True)
    if any(obs[k] is None for k in ("left_rgb", "right_rgb", "depth")):
        raise RuntimeError("Head streams are not ready")
    print(obs["left_rgb"]["data"].shape)
    print(sensors.head_camera.get_camera_info())
finally:
    sensors.shutdown()''')
wrist=code('''from wrist_cameras import WristCameras

with WristCameras() as cameras:
    obs = cameras.get_obs(timeout=3)
    for name, frame in obs.items():
        print(name, frame["rgb"].shape, frame["frame_id"])
        # RGB uint8: (1536, 1920, 3)
        # frame["timestamp_ns"]: pipeline PTS, NOT Unix time
        # frame["received_monotonic_ns"]: host monotonic clock''')
add('sensors','读取头部与腕部相机','Read head and wrist cameras',
'<h3>头部：订阅现有 dexsensor 服务</h3><p>在 source 了环境的 Jetson 上运行。不要启动第二个头部服务，也不要同时让另一个 ZED SDK 进程占用相机。此示例不构造 Robot。</p>'+head+
'<p>左右 RGB 形状为 <code>(1200,1920,3)</code>，深度是米制浮点 <code>(1200,1920)</code>。带时间戳时每流含 <code>data / timestamp_ns / receive_time_ns</code>；默认不带时间戳时直接返回数组，尚未就绪时可能为 None。<code>configs.sensors</code> 是字典，字段必须写 <code>enabled</code>。深度同时需要服务 enabled、<code>depth_mode="NEURAL"</code> 和 <code>[sensors.streams] depth=true</code>。头部内参通过 <code>get_camera_info()</code> 读取，不复制另一台机器的标定。</p>'+
'<h3>双腕：本机 WristCameras API</h3>'+wrist+
'<p>API 从 sysfs 自动识别 A/B 设备，不固定 video0/1；A/B 是连接器标签，尚不能直接当作左／右手。必须先有当前 boot 的 ready.json。每次读取默认等待两路新帧，返回可修改副本；独占两路设备和软件触发。上下文退出时停止取流并释放锁。它是本机接口，没有接入 Dexmate 的 ZED X One 腕部条目，也不提供硬件同步。</p>'+note('所有 RGB 数据交给 OpenCV 保存前，先 <code>cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)</code>；PIL 可直接使用。每次相机只有一个读取进程。'),
'<h3>Head: subscribe to the existing dexsensor service</h3><p>Run on the Jetson after sourcing the environment. Do not start a second head service or open another ZED SDK owner. This example does not construct Robot.</p>'+head+
'<p>Left/right RGB are <code>(1200,1920,3)</code>; depth is floating-point metres, <code>(1200,1920)</code>. Timestamp-enabled streams contain <code>data / timestamp_ns / receive_time_ns</code>; otherwise each value is the array, and may be None before readiness. <code>configs.sensors</code> is a dictionary and the field is <code>enabled</code>. Depth requires service enabling, <code>depth_mode="NEURAL"</code> and <code>[sensors.streams] depth=true</code>. Read intrinsics with <code>get_camera_info()</code>; do not copy another robot’s calibration.</p>'+
'<h3>Wrists: local WristCameras API</h3>'+wrist+
'<p>The API discovers A/B devices through sysfs instead of assuming video0/1. A/B are connector labels, not verified left/right assignments. A current-boot ready.json is required. Each read waits for fresh frames on both cameras and returns independent copies. One process owns both devices and software triggering; context exit stops capture and releases the lock. This is an on-robot API, separate from Dexmate’s ZED X One entries, with no hardware synchronization.</p>'+note('Before saving RGB with OpenCV, use <code>cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)</code>. PIL accepts RGB directly. Use one reader per camera.'))

posecmd=code('''source /opt/dexmate-setup/env.sh
cd /opt/dexmate-setup/poses
python3 goto_ready.py --dry-run  # may home the head
# Supervised motion, only after checking workspace clearance:
python3 goto_ready.py
python3 goto_rest.py''')
poses=table(['Pose','Left arm (rad)','Right arm (rad)'],[
['pre_move','[1.7289, .0101, .0041, -.9924, -.2311, .5011, -.0066]','[-1.5683, -.0026, .0031, -.9916, .0908, -.4138, -.0018]'],
['brickbench_home / manip_init','[0, 1.2, 1.4, -1.57, -1.57, 1, -.35]','[0, -1.2, -1.4, -1.57, 1.57, -1, .35]']])
add('poses','机械臂与头部位姿','Arm and head poses',
note('<strong>先清空运动范围并准备物理急停。</strong>这里的数值来自参考机器人，必须重新检查新机器人上的工具尺寸、线束、标定和实际间隙。夹爪不受 dexcontrol 管理，退出 Python 不能保证夹爪停止。')+
'<p>运行时可控关节共 17 DOF：双臂各 7，头部 3；无已发布的 torso/chassis 控制。头部轴顺序为 pitch / yaw / pitch，负 j3 向下。新版本 <code>goto_ready.py</code> 先右臂后左臂，默认 0.04rad/步、0.8s 等待，并设置参考头部视角约 <code>[0,0,-0.505622]</code>。<code>goto_rest.py</code> 先左臂后右臂。头部角度与相机外参必须在新机重验。</p>'+poses+posecmd+
'<p><code>--head</code> 或 <code>--head-rad J1,J2,J3</code> 可覆盖默认头部目标。原 <code>head_pose.py</code> 作为历史库保留；最新 goto_pose 的标定头部路径使用有界 <code>set_joint_pos_vel</code>。头部会话退出后可能松弛，依赖该视角的采图要保持同一会话。</p>'+
'<h3>为什么必须分臂运动</h3><p>参考路径 pre_move→manip_init 的最小腕心间距：同时 0.354m、左先 0.431m、右先 0.459m；反向左先更宽。脚本按实际分步路径做 FK，低于 0.35m 就拒绝。此仓库补充了 FK 依赖缺失时直接拒绝的检查；腕心距离仍不是完整碰撞证明。</p>'+
fig('pose-reference-1.png','历史 URDF 图 · pre_move、manip_init 与 folded 的夹爪间隙对比。')+
note('<strong>禁止 folded / folded_closed_hand。</strong>原 URDF 不含实际第三方夹爪；即便 gripper URDF 的原厂夹爪模型也不能准确代表本工具。folded 曾让夹爪交叉并损坏 CAN 线。参考原厂夹爪模型中 folded 张开时的最小距离为 0；不要用该姿态收纳。使用已重新检查过的 pre_move。')+
'<p><code>get_joint_pos()</code>、<code>get_joint_vel()</code>、臂电流及 wrench/button state 可经 Robot 读取，但构造时可能动头。<code>set_joint_pos</code> 支持绝对／相对目标；不要把位姿示例改成未经验证的高速循环。物理急停与 <code>robot.estop.activate()</code> 是互补关系。运行结束先完成受监督的回位，不要随意让机械臂失电下垂。</p>',
note('<strong>Clear the workspace and keep the physical e-stop available.</strong> These values come from a reference robot. Recheck tool dimensions, harnesses, calibration and physical clearance on each new unit. Grippers are independent of dexcontrol; exiting Python does not guarantee that they stop.')+
'<p>The published runtime has 17 controllable DOF: 7 per arm and 3 in the head, with no torso/chassis control topics. Head axes are pitch / yaw / pitch; negative j3 looks down. The latest <code>goto_ready.py</code> moves right arm first, at 0.04rad/step and 0.8s waits, then sets the reference head view near <code>[0,0,-0.505622]</code>. <code>goto_rest.py</code> moves left arm first. Revalidate head pose and camera extrinsics on a new robot.</p>'+poses+posecmd+
'<p><code>--head</code> or <code>--head-rad J1,J2,J3</code> overrides the head target. The historical <code>head_pose.py</code> is retained; the latest goto_pose calibrated-head path uses bounded <code>set_joint_pos_vel</code>. The head can relax after its session exits; keep the same live session for capture that depends on its pose.</p>'+
'<h3>Why move one arm at a time?</h3><p>Reference pre_move→manip_init minimum wrist distances were 0.354m concurrent, 0.431m left-first and 0.459m right-first; left-first is wider on return. The script evaluates the actual stepped path by FK and refuses distances below 0.35m. This repository also refuses missing FK dependencies. Wrist-centre distance is still not a complete collision proof.</p>'+
fig('pose-reference-1.png','Historical URDF rendering · Gripper clearance at pre_move, manip_init and folded.')+
note('<strong>Never use folded / folded_closed_hand.</strong> The stock URDF omits the fitted third-party grippers; even the vendor gripper URDF does not model this tool exactly. A folded move crossed the grippers and damaged a CAN cable. The vendor gripper model computes zero open-jaw clearance at folded. Use a revalidated pre_move for parking.')+
'<p>Joint positions, velocities, arm currents and wrench/button states can be read through Robot, but construction may move the head. <code>set_joint_pos</code> supports absolute/relative targets; do not turn examples into unvalidated high-rate control. Software <code>robot.estop.activate()</code> complements the physical e-stop. Finish with a supervised return pose; do not casually de-energize arms and let them sag.</p>')

gcode=code('''source /opt/dexmate-setup/env.sh
cd /opt/dexmate-setup/gripper
python3 gripper_selftest.py check  # no motion; does CAN queries/bus setup
# Supervised full test: check -> open -> close -> stop
python3 gripper_selftest.py all''')
gapi=code('''from gripper import Grippers

g = Grippers()
try:
    g.home()                    # physical homing; jaw motion
    g.both_move_to(0.4, speed=500)
    print(g.position(), g.status())
    # g.grip(current=0.6)      # current-limited grasp
finally:
    g.halt()                   # stop before closing the socket
    g.close_bus()''')
add('grippers','夹爪 API 与 CAN 验收','Gripper API and CAN acceptance',
'<p>夹爪是两个 MG4005-i10 V3，通过 Jhoinrch RH-02 USB-CAN 控制，不属于 <code>robot.left_hand</code>。适配器是 <code>can1</code>，不是 Jetson 自带 <code>can0</code>；1Mbit/s，gs_usb 驱动。照片中两个 switch 朝 K；该参考双端内部终端电阻布线要求适配器 R120 关闭，断电测 CAN H/L 约 60Ω。不能仅凭其他型号上的开关方向推断电气状态。</p>'+gcode+
'<p>重接线先用 selftest 扫描 1–32 ID，确认 ACK、状态与故障。<code>check</code> 不驱动电机，但会建立 CAN 接口并发查询，并非完全被动；完整测试必须实际完成 open、close、stop。旧库假定 1=左、2=右，重新布线后不能直接沿用。历史上左线缆断芯的记录不是当前电机状态。</p>'+gapi+
'<p><code>move_to(0..1)</code> 是闭合到张开的比例，home 后才有效。双爪用 <code>both_move_to</code>，不要串行循环两个 <code>move_to</code>。<code>close</code> 是空爪到闭合位置；碰到物体仍可能堵转，抓取应使用限流 <code>grip</code>。每次供电或 release 后重新 home；保存的多圈编码值不可跨掉电复用。</p>'+table(['操作','含义'],[['halt / 0x81','停止运动，保持上电与标定'],['release / 0x80','失能、夹爪松开，多圈坐标丢失'],['close_bus','只关 SocketCAN，不能替代 halt'],['0xA4','带速度限制的绝对位置；0xA2 是速度控制']])+
'<p>只运行一个 CAN 客户端。电机不会主动广播，空 candump 不能证明断线；TX 固定为 3 表示邮箱卡在未确认帧，不能当作通信成功。自由运动通常低于 0.3A，硬限位约 2–2.5A；这是参考观测，不是新夹爪的自动安全标定。</p>',
'<p>Two MG4005-i10 V3 grippers use a Jhoinrch RH-02 USB-CAN adapter independently of <code>robot.left_hand</code>. The adapter is <code>can1</code>, not Jetson’s built-in <code>can0</code>: 1Mbit/s with gs_usb. Match both K-side switches in the photo. The reference bus has internal termination at both grippers, so adapter R120 is off; expect about 60Ω between CAN H/L with power removed. Switch orientation alone is not portable across adapter models.</p>'+gcode+
'<p>After rewiring, use selftest to discover IDs 1–32 and verify ACKs, telemetry and faults. <code>check</code> does not move motors, but sets up the CAN interface and sends queries; it is not passive. A full test includes open, close and stop. The older library assumes 1=left and 2=right; revalidate after rewiring. Historical left-cable damage does not establish today’s motor status.</p>'+gapi+
'<p><code>move_to(0..1)</code> spans closed to open after homing. Use <code>both_move_to</code> for concurrent jaws rather than looping over blocking calls. <code>close</code> goes to the empty-jaw closed target and can stall on an object; use current-limited <code>grip</code> for grasping. Rehome after power loss or release; saved multi-turn encoder values do not survive de-energizing reliably.</p>'+table(['Operation','Meaning'],[['halt / 0x81','Stop motion; keep power and calibration frame'],['release / 0x80','Disable motor; jaws limp, multi-turn frame lost'],['close_bus','Close SocketCAN only; not a substitute for halt'],['0xA4','Speed-limited absolute position; 0xA2 is speed control']])+
'<p>Run one CAN client at a time. Motors only answer polls, so an empty candump proves nothing. TX stuck at 3 means unacknowledged mailboxes, not success. Reference free-travel current was below 0.3A, hard-stop current about 2–2.5A; these observations do not automatically calibrate a new gripper’s safety limits.</p>')

add('network','网络、证书与软件架构','Networking, certificates and architecture',
'<p><strong>dextop</strong> 负责证书、固件与诊断；<strong>dexcontrol</strong> 在运行控制代码的机器上使用；<strong>dexsensor</strong> 只在 Jetson 采集并发布相机数据；<strong>socbridge</strong> 在 SoC 提供网页管理。它们通过 Zenoh 通信。默认在 Jetson 本机运行，远程工作站需要相同网络、匹配软件与该机器授权的证书。</p>'+
'<h3>第一次联网</h3><p>可用 DisplayPort 显示器加 USB 键鼠，或有线网连接。工作站使用未占用的 <code>192.168.50.2–254</code> 地址（避开 .20/.21），掩码 /24。无已知 WiFi 时机器人可开热点；不同批次参考地址为 <code>10.42.0.1</code> 或 <code>192.168.4.1</code>。热点凭据以交付信息为准。加入已知网络后热点消失、SSH 断开是正常现象。</p>'+code('nmcli device wifi list\nsudo nmcli --ask device wifi connect "YOUR_SSID"')+
'<h3>证书与固件：每台机器独立</h3><p>通过 <code>https://192.168.50.21:57832</code> 的 SoC portal 安装该机器证书；需要时从工作站用 sshuttle 建立路由。未安装 portal 的机器，按厂商流程执行 socbridge 安装。不要将证书、私钥、WiFi 密码提交到 Git。</p>'+code('dextop cert unpack /secure/path/THIS_ROBOT.dzcfg\ndextop firmware info\n# If socbridge is absent, follow the vendor procedure:\n# dextop firmware install-socbridge')+
'<p>升级固件必须遵循厂商版本配套流程；本仓库固定 dexcontrol 0.5.0，面向固件 0.5.x。固件升级、证书导入、SoC 网络恢复均不由快速安装器自动完成。外部工作站还需设置 <code>ZENOH_CONFIG</code> 为本机证书目录下的 <code>zenoh_peer_config.json5</code>，并显式设置 ROBOT_NAME；ROBOT_IP 可辅助发现。<code>dextop node install-service</code> 会启动 relay，无需再运行第二个 node。</p>',
'<p><strong>dextop</strong> manages certificates, firmware and diagnostics; <strong>dexcontrol</strong> runs where control code runs; <strong>dexsensor</strong> captures/publishes sensors on the Jetson; <strong>socbridge</strong> provides the SoC web portal. Communication uses Zenoh. Onboard execution is the default; a workstation needs compatible software, LAN access and an authorized certificate for this robot.</p>'+
'<h3>First network connection</h3><p>Use a DisplayPort monitor with USB keyboard/mouse, or Ethernet. Give the workstation a free <code>192.168.50.2–254</code> address excluding .20/.21, with /24 netmask. Without a known WiFi network the robot may create a hotspot; reference batch addresses are <code>10.42.0.1</code> or <code>192.168.4.1</code>. Obtain credentials from the delivery information. Joining WiFi makes the hotspot disappear and the SSH session disconnect.</p>'+code('nmcli device wifi list\nsudo nmcli --ask device wifi connect "YOUR_SSID"')+
'<h3>Certificates and firmware are per robot</h3><p>Install the robot’s own certificate through the SoC portal at <code>https://192.168.50.21:57832</code>; use sshuttle routing from an external workstation if needed. Install socbridge through the vendor procedure if absent. Never commit certificates, keys or WiFi passwords to Git.</p>'+code('dextop cert unpack /secure/path/THIS_ROBOT.dzcfg\ndextop firmware info\n# If socbridge is absent, follow the vendor procedure:\n# dextop firmware install-socbridge')+
'<p>Follow the vendor’s matched-version firmware process. This repository pins dexcontrol 0.5.0 for firmware 0.5.x. The installer does not update firmware, import certificates or restore SoC networking. Workstations also need <code>ZENOH_CONFIG</code> pointing to the local certificate’s <code>zenoh_peer_config.json5</code> and an explicit ROBOT_NAME; ROBOT_IP can assist discovery. <code>dextop node install-service</code> starts the relay itself; do not start a duplicate node.</p>')

limits=table(['Joint','Left (rad)','Right (rad)'],[['j1','±3.071','±3.071'],['j2','[-.453,1.553]','[-1.553,.453]'],['j3','±3.071','±3.071'],['j4','[-3.071,.244]','[-3.071,.244]'],['j5','±3.071','±3.071'],['j6','±1.396','±1.396'],['j7','[-1.378,1.117]','[-1.117,1.378]']])
checks=code('''uname -r
cat /etc/nv_tegra_release
dextop doctor check
dextop topic list --timeout 10
dextop firmware info
systemctl status dexsensor wrist-camera-init.service can1.service --no-pager
journalctl -u wrist-camera-init.service -b --no-pager
cat /run/wrist-cameras/ready.json
ip -details -statistics link show can1''')
add('acceptance','安装验收与关节范围','Acceptance and joint limits',
'<p>按“平台 → 服务 → 图像 → CAN 查询 → 现场动作”顺序验收。<code>doctor.py</code> 只读检查内核、服务、当前 boot 标记、视频节点和 CAN 配置；不会发送关节指令、CAN 查询或相机寄存器初始化。静态通过不等于已收到图像或电机应答。</p>'+checks+
'<ol><li>核对上面的固定版本，确保无错误内核模块。</li><li>头部读取左右 RGB 和深度，检查形状与时间戳更新；双腕用 API 连续读取并确认两路 frame_id 都递增。</li><li>退出相机上下文后重新打开，确认锁被释放。A/B 对应物理哪只手需现场记录。</li><li>夹爪先 check，再在现场做完整 all；确认每个电机的实际方向与 ID。</li><li>最后检查 FK 依赖、工具间隙和急停，在新机重新验收 ready/rest；不要把历史采图成功当作冷启动或运动认证。</li></ol>'+
'<h3>参考机器人关节范围</h3>'+limits+'<p>Vega-1U 运行时发布双臂与头部，合计 17 DOF。固件表出现 torso 不能证明有可控腰部；以 topic 和组件为准。URDF 仍可能包含 Lift / torso_flip，离线模型维数不能代替运行时接口。新机器应读取自身 joint_pos_limit；表格是参考值。</p>',
'<p>Accept in this order: platform → services → frames → CAN queries → supervised movement. <code>doctor.py</code> only reads kernel, services, current-boot readiness, video nodes and CAN configuration; it sends no joint commands, CAN queries or camera initialization writes. Static success does not prove frame delivery or motor replies.</p>'+checks+
'<ol><li>Check the pinned versions and module compatibility.</li><li>Read head stereo RGB and depth, confirming shapes and advancing timestamps; read wrists repeatedly and confirm both frame_id values increase.</li><li>Close and reopen the wrist context to verify lock release. Record the physical A/B-to-hand mapping onsite.</li><li>Run gripper check, then supervised all. Confirm actual motor direction and ID.</li><li>Finally check FK dependencies, tool clearance and e-stop; revalidate ready/rest on the new robot. Historical capture success is not cold-boot or motion certification.</li></ol>'+
'<h3>Reference joint limits</h3>'+limits+'<p>The observed Vega-1U runtime publishes two arms and a head, totaling 17 DOF. A torso entry in the firmware table does not establish a controllable waist; use topics/components. URDF Lift / torso_flip joints may still exist in the offline model. Read the new robot’s own joint_pos_limit; this table is a reference.</p>')

rates=table(['2026-09-15 test','Observed rate'],[['Head left / right HD1200','15.105 fps each'],['Head NEURAL depth','15.054 fps'],['Wrist A / B native UYVY','9.327 / 9.293 fps'],['Full-resolution wrist RGB API + head subscriber','5.80 pairs/s'],['45.020s composed motion video','236 frames · 5.24 fps preview']])
add('camera-boot','相机启动链与驱动版本','Camera boot chain and driver versions',
'<p>头部 ZED X Mini 通过 ZED Link Duo / MAX96712 接 CAM0（serial_b、port-index 1、2 lanes）；双腕 OEM ISX031 / MAX9295 接 Waveshare MAX9296A，再由 CSI0 接 CAM1（serial_c、port-index 2、4 lanes）。OEM 腕相机输出 1920×1536 UYVY；不能套用配置中的通用 ZED X One 腕部条目。</p>'+
'<p>合并 overlay 保留头部的 26 个 VI/CSI 通道，并增加腕部 26/27。头部 TCA9546 位于 CAM0 GPIO mux 分支下，因此 tegra-camera 使用 parent-walk 补丁；腕部驱动适配 MAX9295 ID 和 3Gbps。仅有 video 节点不足以出图，还需要 OEM 寄存器初始化和软件触发。</p>'+
'<ol><li>extlinux 选择独立 overlay 和独立 initrd，保留原 Image、DTB 与 initrd。</li><li>initrd 在切根前，以只读 bind mount 提供补丁模块。</li><li>wrist-camera-init.service 等待两腕探测，初始化后写当前 boot 的 ready.json。正常 oneshot 状态是 active (exited)。</li><li>WristCameras 打开时取流和触发，关闭时停止；开机服务不会持续录像。头部仍由 dexsensor 发布。</li></ol>'+
note('<strong>导出当天的实际状态：</strong>2026-09-26，源机器人初始化读取 bus 9 / serializer 0x44 失败，ready.json 不存在。未在本次工作中重启或修复硬件。下面是 9 月 15 日历史成功数据，不是今天的验收。')+rates+
'<p>当时共同取流重叠 19.662s，时间戳递增，应用捕获/触发错误为 0；启动/停止仍有内核日志信息。30fps 腕部、长期稳定性、重插及完整新默认冷启动未建立验证结论。AGX 的 <code>5.15.148-rt</code> 整包不能安装到本 Nano 的 <code>5.15.185-tegra</code>。</p>'+
'<p>手动重新初始化前关闭所有腕部读者，再执行 <code>sudo systemctl restart wrist-camera-init.service</code>。不得热卸载 nvhost_isp5 或批量卸载相机栈，历史上已触发 kernel panic。内核升级后重建并重新验收，不绕过包依赖。</p>',
'<p>The head ZED X Mini connects through ZED Link Duo / MAX96712 to CAM0 (serial_b, port-index 1, 2 lanes). OEM ISX031 / MAX9295 wrists connect through Waveshare MAX9296A CSI0 to CAM1 (serial_c, port-index 2, 4 lanes). Wrist output is 1920×1536 UYVY. Generic ZED X One wrist entries do not apply.</p>'+
'<p>The combined overlay retains 26 head VI/CSI channels and adds wrists at 26/27. The head TCA9546 sits below the CAM0 GPIO mux, requiring a parent-walk tegra-camera patch. The wrist driver adapts MAX9295 identification and 3Gbps links. Video nodes alone do not produce frames: OEM register initialization and software triggering are also required.</p>'+
'<ol><li>Extlinux selects a separate overlay and initrd while retaining the original Image, DTB and initrd.</li><li>The initrd exposes patched modules through read-only bind mounts before switch-root.</li><li>wrist-camera-init.service waits for both probes, initializes cameras and writes a current-boot ready.json. active (exited) is normal for this oneshot.</li><li>WristCameras starts capture/triggering on open and stops on close; the boot service does not continuously record. dexsensor still publishes the head.</li></ol>'+
note('<strong>Actual export-day status:</strong> on 2026-09-26, the source robot failed to read serializer 0x44 on bus 9 and had no ready.json. This task did not reboot or repair the hardware. The following are historical September 15 results, not today’s acceptance.')+rates+
'<p>The raw test had 19.662s of shared capture, increasing timestamps and zero application-level capture/trigger errors. Startup/stop kernel messages remained. Thirty-fps wrists, long-duration stability, reconnects and a complete new-default cold boot were not established. The AGX <code>5.15.148-rt</code> package must not be installed wholesale on this <code>5.15.185-tegra</code> Nano.</p>'+
'<p>To reinitialize manually, close all wrist readers before <code>sudo systemctl restart wrist-camera-init.service</code>. Do not hot-unload nvhost_isp5 or batch-unload the camera stack: it previously caused a kernel panic. Rebuild and revalidate after kernel updates; never bypass package dependencies.</p>')

zhtraps=[['腕部服务读取 0x44 失败','先断电核对对应同轴链路、接口和供电，再看当前 boot 日志；不要先热卸载内核模块。'],['CAMERA NOT DETECTED，但 SDK 可用','检查 video 节点、zed_x_daemon 和内核 vermagic；用户态 SDK 能加载不代表内核驱动匹配。'],['深度配置 NEURAL 但日志 NONE','还需 sensors.streams.depth=true 和 enabled=true。'],['相机字段改了仍无数据','字段为 enabled，configs.sensors 是字典；确保 Jetson dexsensor 在运行。'],['一爪响应，一爪安静','检查该支路供电/断线；断电交换已知正常线以定位，错误帧不能当作 ID 回复。'],['CAN TX 固定为 3 / candump 空','未被 ACK 的邮箱可能堵住；电机只响应查询。核对 1Mbit/s、H/L、供电与终端。'],['USB-CAN 进入 DFU','检查 BOOT 开关，再拔插 USB；软件复位不能替代重新上电采样。'],['夹爪遥测读零或出现假 stall','多个 CAN 客户端相互回显；只保留一个。0x0010 通常表示输出级关闭。'],['头部回到 home / dry-run 也动了','Robot() 初始化有副作用。取图直接用 Sensors；保持同一头部控制会话。'],['SoC 超时 / portal 不通','检查 192.168.50.21 路由和 Jetson .20 静态地址；外部机器需要合适路由。'],['firmware info 超时但 topic list 成功','核对 ROBOT_NAME 的 dm/ 斜杠；topic list 通配符不能证明名称正确。'],['sudo 找不到 dextop','使用已安装的绝对可执行路径；不要假设 root 继承用户 PATH。'],['node 的 7447 端口占用','install-service 已启动 relay，不要重复启动。'],['ZED SDK 缺失但 pyzed 能 import','检查所用环境与 C++ 标准库；优先使用匹配的系统环境。'],['保存的图红蓝颠倒','RGB 转 BGR 再给 OpenCV。'],['SSH 下 ZED 初始化失败','不要使用 ssh -X；使用普通 SSH。']]
entraps=[['Wrist service cannot read 0x44','Power down and inspect that coax branch, connectors and supply; inspect this boot’s log before touching drivers.'],['CAMERA NOT DETECTED but SDK loads','Check video nodes, zed_x_daemon and module vermagic; userspace loading does not prove kernel compatibility.'],['NEURAL configured but log says NONE','Also enable sensors.streams.depth and the sensor itself.'],['Enabling camera yields no data','Use enabled and dictionary indexing; dexsensor must run on Jetson.'],['Only one gripper answers','Check power/open conductor on that branch; swap a known-good cable with power off. Ignore error frames in ID scans.'],['CAN TX stuck at 3 / empty candump','Unacknowledged mailboxes can stall; motors answer queries only. Check 1Mbit/s, H/L, power and termination.'],['USB-CAN enters DFU','Check the BOOT switch and unplug/replug USB; a software reset does not resample power-on state.'],['Zero telemetry / phantom stall','Multiple CAN clients can echo each other; keep one. Fault 0x0010 commonly means output stage disabled.'],['Head homes during dry-run','Robot() initialization has side effects. Use Sensors for images and keep the same head control session.'],['SoC timeout / portal unavailable','Check routing to .21 and Jetson’s .20 static address; external workstations need a route.'],['firmware info times out but topic list works','Verify the dm/ slash in ROBOT_NAME; wildcard topic listing does not validate the name.'],['sudo cannot find dextop','Use its installed absolute executable path; root may not inherit the user PATH.'],['Port 7447 already in use','install-service already started the relay; do not launch a duplicate.'],['ZED SDK missing but pyzed imports','Check the selected environment and C++ standard library; prefer the matching system environment.'],['Red/blue swapped in saved image','Convert RGB to BGR for OpenCV.'],['ZED fails under SSH','Use plain SSH, not ssh -X.']]
add('troubleshooting','故障排查','Troubleshooting',table(['现象','下一步'],zhtraps),table(['Symptom','Next check'],entraps))

add('recovery','刷机恢复与回退','Reflash recovery and rollback',
'<h3>刷机后恢复顺序</h3><ol><li>恢复匹配的 L4T 36.5.0 / 5.15.185-tegra 基础系统以及通往 SoC 的有线网络。</li><li>安装匹配的 ZED SDK 5.2.3、ZED Link Duo 与 dexsensor 0.7.6；用 <code>/usr/local/zed/tools/ZED_Explorer -a</code> 检查，但避免和运行中的 dexsensor 争用。</li><li>安装固定版本 dextop，设置本机机器人名称，导入该机器自己的证书；需要时安装 socbridge。</li><li>运行本仓库安装器，接控制台人工重启，逐项验收。</li></ol>'+
'<p>历史上 JetPack 6.2.3 / L4T 36.5.2 的内核 5.15.199 与本 ZED Link 模块不匹配。即使都叫 36.5，具体内核仍不同。不要使用 <code>--ignore-depends</code>：厂商 postinst 还会写显示和硬件引擎模块。需要系统降级时先做 apt 模拟并审查全部 nvidia-l4t 包；本仓库不会自动降级或刷 bootloader。</p>'+
'<h3>回退本仓库安装</h3><p>先在启动菜单选原 <code>Stereolabs</code> / <code>primary</code> 项，或从本次时间戳备份恢复 extlinux；不要把另一台机器的配置复制过来。每次安装的 <code>manifest.json</code> 列出修改路径及原文件是否存在。关闭所有读者，再恢复备份文件；对原本不存在的文件只移除本次安装的对应项。恢复后运行 <code>sudo depmod -a</code> 和 <code>sudo systemctl daemon-reload</code>，安排重启。</p>'+
'<p>文件备份不是系统镜像：apt/pip 依赖、video/i2c 组权限、systemd enable 链接需分别核对。若卸载本仓库专属服务，先明确旧机是否已使用它们，再决定禁用。不要直接删除正在使用的虚拟环境或热卸载相机模块。</p>',
'<h3>Recovery after reflash</h3><ol><li>Restore a matching L4T 36.5.0 / 5.15.185-tegra baseline and the wired route to the SoC.</li><li>Install matching ZED SDK 5.2.3, ZED Link Duo and dexsensor 0.7.6. Inspect with <code>/usr/local/zed/tools/ZED_Explorer -a</code> without competing with dexsensor.</li><li>Install pinned dextop, set this robot’s identity and unpack its own certificate; install socbridge if needed.</li><li>Run this installer, reboot manually with console access and complete acceptance.</li></ol>'+
'<p>Historically JetPack 6.2.3 / L4T 36.5.2 shipped 5.15.199, incompatible with these ZED Link modules. The shared “36.5” label is insufficient. Never use <code>--ignore-depends</code>: the vendor postinst also replaces display/hardware-engine modules. If a system downgrade is necessary, simulate apt first and review the complete nvidia-l4t package set. This installer does not downgrade or flash the bootloader.</p>'+
'<h3>Roll back this installation</h3><p>Select the original <code>Stereolabs</code> / <code>primary</code> boot entry, or restore extlinux from this installation’s timestamped backup. Never copy another machine’s boot config. The backup <code>manifest.json</code> lists changed paths and whether they existed. Close all readers, restore backed-up files, and remove only installation-owned files that had no previous version. Run <code>sudo depmod -a</code> and <code>sudo systemctl daemon-reload</code>, then schedule a reboot.</p>'+
'<p>File backups are not system images: review apt/pip dependencies, video/i2c memberships and systemd enable links separately. Before disabling a service, establish whether the robot already used it. Do not delete a live environment or hot-unload camera modules.</p>')

add('sources','文件清单与依据','Files and sources',
'<p>软件与配置于 <strong>2026-09-26</strong> 从机器人通过 SSH 导出，版本、原始文件校验值与当日状态在仓库 <code>provenance/</code>。只有明确列出的运行库和配置进入 Git；证书、私钥、日志中的凭据及机器标定未上传。</p>'+table(['目录','用途'],[['software/gripper','Grippers / Motor 库、selftest 与历史说明'],['software/wrist_cameras','初始化、触发与双腕 RGB API'],['software/poses','ready/rest、位姿引擎、头部与只读传感器示例'],['drivers','精确版本模块、overlay、SHA256 与重建输入'],['scripts','安装、initrd 构建、只读检查和页面生成'],['docs/assets','四张实拍、两段 walkthrough、厂商图与原手册姿态图']])+f'<p><a href="{repo}">GitHub 仓库</a> · <a href="reference.html">原英文手册归档（已脱敏，带历史状态提示）</a> · <a href="{waves}">Waveshare 官方硬件文档</a> · <a href="https://pypi.org/project/dexcontrol/0.5.0/">Dexcontrol 0.5.0 版本兼容说明</a></p><p>旧手册来自 Dexmate wiki、厂商支持和实验室排错记录；本版保留日常操作、一次性 setup、驱动背景与历史限制，并新增带图硬件步骤。</p>',
'<p>Runtime files and configuration were exported over SSH on <strong>2026-09-26</strong>. Captured versions, original hashes and observed status are recorded in <code>provenance/</code>. Only allowlisted software/configuration enters Git; certificates, private keys, credential-bearing logs and per-robot calibration are excluded.</p>'+table(['Directory','Purpose'],[['software/gripper','Grippers / Motor library, selftest and historical notes'],['software/wrist_cameras','Initialization, trigger worker and dual-wrist RGB API'],['software/poses','Ready/rest, pose engine, head and sensor-only examples'],['drivers','Exact-version modules, overlay, SHA256 and rebuild inputs'],['scripts','Installer, initrd builder, read-only checks and site generator'],['docs/assets','Four field photos, two walkthroughs, vendor images and original pose figures']])+f'<p><a href="{repo}">GitHub repository</a> · <a href="reference.html">Original English manual archive (redacted, historical-status banner)</a> · <a href="{waves}">Waveshare hardware guide</a> · <a href="https://pypi.org/project/dexcontrol/0.5.0/">Dexcontrol 0.5.0 compatibility</a></p><p>The original manual draws on Dexmate wiki pages, vendor support and lab debugging. This edition retains daily operation, one-time setup, driver context and historical limits, and adds illustrated hardware instructions.</p>')

for lang in ['zh','en']:
 zh=lang=='zh'; title='Vega-1U 安装与使用手册' if zh else 'Vega-1U Setup & Field Manual'
 other='en.html' if zh else 'index.html'
 nav=''.join(f'<a href="#{s[0]}"><span>{i:02d}</span>{s[1 if zh else 2]}</a>' for i,s in enumerate(sections,1))
 content=''.join(f'<section id="{s[0]}"><div class="section-head"><span>{i:02d}</span><h2>{s[1 if zh else 2]}</h2></div>{s[3 if zh else 4]}</section>' for i,s in enumerate(sections,1))
 description='从线束、采集板到软件安装。一份可带到下一台机器的现场手册。' if zh else 'From the harness and capture board to software installation. A field manual for the next robot.'
 status='参考软件已导出 · 新机安装和冷启动仍需现场验收' if zh else 'Reference software exported · New-robot install and cold boot require onsite acceptance'
 html=f'''<!doctype html>
<html lang="{'zh-CN' if zh else 'en'}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="{description}"><title>{title} · ICL</title><link rel="stylesheet" href="style.css"><link rel="alternate" hreflang="{'en' if zh else 'zh-CN'}" href="{other}"></head>
<body><a class="skip" href="#main">{'跳转正文' if zh else 'Skip to content'}</a>
<header><a class="brand" href="{'index.html' if zh else 'en.html'}"><span class="brand-mark">ICL</span><span>DEXMATE <b>/ SETUP</b></span></a><div class="header-links"><a class="language" href="{other}">{'English' if zh else '中文'}</a><a href="{repo}">GitHub ↗</a></div></header>
<div class="layout"><aside class="sidebar"><div class="side-title">{'现场手册' if zh else 'FIELD MANUAL'} <span>2026.09</span></div><nav aria-label="{'章节' if zh else 'Chapters'}">{nav}</nav><div class="side-note">VEGA-1U<br>ORIN NANO 8GB<br>L4T 36.5.0</div></aside>
<main id="main"><div class="hero"><div class="eyebrow">INTELLIGENT CONTROL LAB / FIELD GUIDE 01</div><h1>{'把下一台机器人<br>配置好。' if zh else 'Set up the<br>next robot.'}</h1><p class="lead">{description}</p><div class="hero-actions"><a class="button" href="#hardware">{'硬件安装' if zh else 'Hardware setup'} ↓</a><a class="button secondary" href="#install">{'软件快速安装' if zh else 'Quick install'} →</a></div><div class="hero-meta"><span>17 DOF</span><span>HEAD + 2 WRISTS</span><span>USB-CAN GRIPPERS</span></div></div>
<div class="status"><span class="status-dot"></span>{status}</div>{content}<footer>Intelligent Control Lab · Vega-1U · 2026-09-26<br>{'图像、版本与验收状态请结合对应章节阅读。' if zh else 'Read images, versions and validation status together with their sections.'}</footer></main></div><script src="site.js"></script></body></html>'''
 if zh:
  for old,new in {'Component':'组件','Pinned version / target':'固定版本／目标平台','Pose':'位姿','Left arm (rad)':'左臂（rad）','Right arm (rad)':'右臂（rad）','Joint':'关节','Left (rad)':'左侧（rad）','Right (rad)':'右侧（rad）','2026-09-15 test':'2026-09-15 历史测试','Observed rate':'实测速率'}.items():
   html=html.replace('<th>'+old+'</th>','<th>'+new+'</th>')
 (DOC/('index.html' if zh else 'en.html')).write_text(html)
(DOC/'.nojekyll').touch()
print('Built Chinese and English manuals:',len(sections),'sections each')
