# APT 人物替换 Skill（本地 ComfyUI / RunningHub 双后端）

把 ROSÉ & Bruno Mars《APT.》MV 的前 44 段做**全流程人物替换**：保留每一镜的动作、机位、运镜、时间与场景，把两位原片人物整体替换成你自己的参考图角色（示例使用一号=霍比特人、二号=瘦削类人生物），最后按原始帧数表拼回成片、整条换上原声音轨。

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
└── docs/
    ├── 本地环境准备.md        # 硬件要求＋整合包网盘下载
    ├── RunningHub准备.md      # 注册邀请链接＋配置
    ├── 提示词规则-完整版.md    # 逐条提示词规则（源自复刻包，含实测修正）
    └── R2VA提示词模板.md      # 六段式全参考提示词模板
```

> 注：本仓库只含方法与脚本，**不含任何原 MV 音视频素材**；运行所需的素材结构（分段源片、简介、帧数表、参考图、音轨）请按 SKILL.md 的目录约定自行准备。

## 许可与免责

- 许可沿袭原复刻包 [LICENSE.txt](LICENSE.txt)：允许学习、改造和分发，**分发时必须说明来源并保留原作者 wuwukasi 署名**；实质性改造后同样须注明原作者、来源与修改内容。
- 本项目仅供学习与研究。原 MV 的音乐与画面版权归原权利方所有；使用本技能产生的成片请自行承担传播风险，请勿用于商业用途。
