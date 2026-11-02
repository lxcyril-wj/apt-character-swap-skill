# APT 人物替换 Skill（本地 ComfyUI / RunningHub 双后端）

把 ROSÉ & Bruno Mars《APT.》MV 的前 44 段做**全流程人物替换**：保留每一镜的动作、机位、运镜、时间与场景，把两位原片人物整体替换成你自己的参考图角色（示例使用一号=霍比特人、二号=瘦削类人生物），最后按原始帧数表拼回成片、整条换上原声音轨。

## 🎬 效果展示（均为本地 H3 后端生成成片的实际抽帧）

| | |
|---|---|
| ![020 双人全身舞段](docs/images/showcase_020.png) | ![044 贴纸剪贴风对视](docs/images/showcase_044.png) |
| ![016 墨镜搭肩合唱](docs/images/showcase_016.png) | ![001 开场定场镜头](docs/images/showcase_001.png) |

| 020 舞段·闪电特效 | 009 手写歌词逐行写出 | 015 墨镜摘戴转移 |
|---|---|---|
| ![020 动图](docs/images/demo_020.gif) | ![009 动图](docs/images/demo_009.gif) | ![015 动图](docs/images/demo_015.gif) |

一条技能，两种出图后端随你选：

- **本地后端**：ComfyUI + Spark-H3 加速包，H3 模型 1920×1088 原生直出，免费无限量（需 RTX 40 系 24G 显存）
- **RunningHub 云端后端**：R2VA 应用零配置，注册即用，按量计费

## 🙏 鸣谢与来源

**本 Skill 基于 [wuwukasi](https://github.com/) 的《APT 复刻包》制作，感谢原作者 wuwukasi** ——项目结构、逐段中文简介与帧数表、R2VA 六段式提示词模板、RunningHub 提交/组装/校验脚本与全套提示词规则均源自其复刻包，原许可（见 [LICENSE.txt](LICENSE.txt)）随项目保留。

在本作上的主要改造（已按许可注明）：

1. 新增**本地 ComfyUI SparkH3 生成后端**（`h3_batch.py`）：H3 模型 2MP 原生 1920×1088 直出、默认绕过 RTX 超分、状态管理/失败重试/自动下载验帧，与 RH 后端共用全部提示词与组装流程
2. 逐段抽帧实测并修正了原简介/规则中十余处与源片不符的细节（硬切帧号、持麦手、手写字内容、字母循环、运镜存在性等），修正均已回写规则文档
3. 校验器身份词与参考图解耦，换图即换词；新增画面文字保留段的自动尾缀处理

## 🚀 快速开始

### 路线 A：本地生成（免费）

1. 下载整合包及模型：**https://pan.quark.cn/s/54d2b9913687**
2. 按 [docs/本地环境准备.md](docs/本地环境准备.md) 安装启动（RTX 4090/24G 实测：141 帧双参考约 5 分钟/段，全片约 2 小时）

### 路线 B：RunningHub 云端

1. 注册（走邀请链接，感谢支持项目）：
   - 国内用户：https://www.runninghub.cn/?inviteCode=cn-v1008
   - 海外用户：https://www.runninghub.ai/?inviteCode=rh-v1641
2. 按 [docs/RunningHub准备.md](docs/RunningHub准备.md) 配好 `api_key.txt` 等三个 txt

### 然后按 [SKILL.md](SKILL.md) 走完整流程

`准备素材 → 逐段写六段式提示词 → validate_prompts.py 校验到 errors 0 → h3_batch.py / rh_batch.py 批量提交 → 抽帧验收 → assemble.py 组装成片`

## 目录

```
├── SKILL.md                  # 主文档：双后端全流程（生成前先问本地还是 RH）
├── README.md
├── LICENSE.txt               # 原复刻包许可（署名条款，保留）
├── scripts/
│   ├── h3_batch.py           # 本地 ComfyUI 批量提交（默认 1920×1088 无超分）
│   ├── rh_batch.py           # RunningHub 批量提交
│   ├── validate_prompts.py   # 提示词机械校验
│   └── assemble.py           # 按帧数表组装成片（24000/1001 重计时＋换音轨）
├── tools/
│   └── make_segments.py      # 自备 MV 一键切段＋补帧＋抽音轨，复现素材结构
├── 工作流/
│   ├── H3-API-Spark-template.json        # 本地后端 ComfyUI 工作流（文/图/参考生）
│   └── H3-API-audio-Spark-template.json  # 本地后端音频驱动工作流
├── 素材包/
│   ├── 分段简介/ … 原始帧数.txt / 补齐后帧数.txt / 替换用参考图/
│   └── README.md             # ⭐ 含"带 MV/音频素材完整版"的网盘说明
└── docs/
    ├── 本地环境准备.md        # 硬件要求＋整合包网盘下载
    ├── RunningHub准备.md      # 注册邀请链接＋配置
    ├── 提示词规则-完整版.md    # 逐条提示词规则（源自复刻包，含实测修正）
    ├── R2VA提示词模板.md      # 六段式全参考提示词模板
    └── images/                # 效果展示图与动图
```

## 📦 复刻素材怎么来

- **方法性素材已随仓库开源**：44 段中文简介、原始/补齐帧数表、示例参考图（`素材包/`），加上 `tools/make_segments.py`，自备正版 MV 即可一键复现全部素材结构。
- **带参考 MV / 音频素材的完整版在网盘**（与整合包及模型同盘）：**https://pan.quark.cn/s/54d2b9913687**
  出于版权原因，原 MV 分段视频与音轨不在本仓库分发；网盘素材同样仅供个人学习，请勿二次传播。

## 🔧 ComfyUI 工作流

`工作流/` 内是本地后端实际使用的 ComfyUI API 工作流（H3 主模型 + ref2v_turbo LoRA + Spark-H3 稀疏注意力加速 + int8 视频 VAE），`h3_batch.py` 提交时自动套用；想改采样器、步数、Spark 档位或恢复 RTX 超分链路，直接改这里的 JSON（对应关系见 SKILL.md）。

## 许可与免责

- 许可沿袭原复刻包 [LICENSE.txt](LICENSE.txt)：允许学习、改造和分发，**分发时必须说明来源并保留原作者 wuwukasi 署名**；实质性改造后同样须注明原作者、来源与修改内容。
- 本项目仅供学习与研究。原 MV 的音乐与画面版权归原权利方所有；使用本技能产生的成片请自行承担传播风险，请勿用于商业用途。
