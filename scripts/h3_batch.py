# -*- coding: utf-8 -*-
"""按段提交本地 ComfyUI SparkH3 人物替换任务（替代 rh_batch.py 的 RunningHub 后端）。

前置：先启动 SparkH3 包的 ComfyUI（D:\\ComfyUI_SparkH3\\运行comfyui - SparkH3.bat，端口 30001）。
配置仍读 并发数.txt（同时在跑的段数上限）；api_key.txt / ai应用.txt 只给 RunningHub 回退用，本地不需要。

提示词读 提示词\\NNN.txt（六段式 R2VA 格式原样使用），末尾自动追加 H3 固定尾缀；
009/011/040 按包规则在尾缀前加一行「源片原有文字保留」说明（TEXT_KEEP 可改）。
参考图按 CAST 直连 一号.png / 二号.png（一号=Picture 1，二号=Picture 2），源视频读 补齐生成用 里带帧数的 mp4，
帧长用文件名上的帧数（都是 17n+5，与 H3 要求一致）。

状态记 h3_state.json；成功立刻经 /view 接口下载到 完成分段\\NNN.mp4（输出目录被启动参数
重定向到 D:\\ComfyUI-Shared\\output，走 HTTP 取回不依赖本地路径）。同一段连续失败 3 次就放弃。

用法：
  python h3_batch.py submit 001 003 ...   # 提交并等到全部完成（跳过已成功，失败自动重试）
  python h3_batch.py status               # 查状态并下载已完成的段
  python h3_batch.py download             # 同 status
  python h3_batch.py print 001 ...        # 干跑：上传素材、建图、打印摘要，不提交
可选参数放在子命令前面：--mp 2.0 --steps 6 --seed N --sr（回 RTX 超分）--host H --port P --template 路径
2026-11-02 定档：默认 2MP 原生 1920x1088、无超分、6 步、speed 档。
"""
import argparse
import importlib
import json
import os
import random
import subprocess
import sys
import time
import types
from pathlib import Path

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "补齐生成用")
PROMPT = os.path.join(ROOT, "提示词")
REF = os.path.join(ROOT, "替换用参考图")
OUT = os.path.join(ROOT, "完成分段")
STATE = os.path.join(ROOT, "h3_state.json")
ORIG_TABLE = os.path.join(SRC, "原始帧数.txt")
MAX_ATTEMPTS = 3
# SparkH3 包的 h3-api 目录；开源分发时可用环境变量 H3_API_DIR 指向自己的安装位置
H3_API_DIR = os.environ.get("H3_API_DIR", r"D:\ComfyUI_SparkH3\h3-api")

# 提示词末尾的固定尾缀：H3 技能要求原文照抄，不得改写。
SUFFIX = ("【禁止项】 文字/UI/水印/Logo/角标/可读文字/真实UI 【强制声明】 无背景音乐,"
          "仅保留环境音与人声和音效;画面禁字幕/文字/水印/Logo;禁止可读文字(指画面字幕文字,不含人声台词)。")
# 画面里必须保留源片文字的段（总体使用规则第 12 条；030 为 2026-11-03 逐帧核对新增：黑色手绘字母）：
# 在尾缀前加一行说明，禁令只针对新增文字。
TEXT_KEEP = {"009", "011", "030", "040"}
TEXT_KEEP_LINE = ("【源片文字保留】<Video 1> 画面里已有的手写歌词、飞过的字母与字样是源片原有内容,"
                  "按 <Video 1> 原样保留、不删改、不重画；禁止可读文字的禁令只针对新增文字。")

# 固定映射：文件名就是人物编号；逻辑一只使用 一号.png，逻辑二只使用 二号.png。
# 002 全段没有人，不提交；004、007、017 按用户决定用原片，不在这里。
CAST = {
    "001": "一二", "003": "一二", "005": "二", "006": "一二",
    "008": "一二", "009": "一二", "010": "一二", "011": "一二", "012": "一二",
    "013": "一二", "014": "一二", "015": "一二", "016": "一二", "018": "一二",
    "019": "一二", "020": "一二", "021": "一二", "022": "一二", "023": "一二", "024": "一二",
    "025": "一二", "026": "一二", "027": "一", "028": "一二", "029": "一二",
    "030": "一二", "031": "一二", "032": "一二", "033": "一二", "034": "一二",
    "035": "一二", "036": "一二", "037": "一二", "038": "一", "039": "一二",
    "040": "一二", "041": "二", "042": "二", "043": "一二", "044": "一二",
}
IMG = {"一": os.path.join(REF, "一号.png"), "二": os.path.join(REF, "二号.png")}

# 包内自带便携版 ffmpeg，优先给 h3_submit 数帧用
_FFDIR = os.path.join(ROOT, "ffmpeg")
if os.path.isfile(os.path.join(_FFDIR, "ffprobe.exe")):
    os.environ["PATH"] = _FFDIR + os.pathsep + os.environ.get("PATH", "")

sys.path.insert(0, H3_API_DIR)
try:
    h3 = importlib.import_module("h3_submit")  # 复用建图/上传/提交逻辑
except Exception as e:
    raise SystemExit(f"导入 {H3_API_DIR}\\h3_submit.py 失败：{e}\n请确认 SparkH3 包在原位且已装 requests")


def concurrency():
    path = os.path.join(ROOT, "并发数.txt")
    if not os.path.isfile(path):
        return 1
    text = open(path, encoding="utf-8").read().strip().splitlines()[0].strip()
    try:
        n = int(text)
    except ValueError:
        raise SystemExit(f"并发数.txt 不是整数：{text}")
    if n < 1:
        raise SystemExit("并发数.txt 至少是 1")
    return n


def video_path(num):
    hits = [f for f in os.listdir(SRC) if f.startswith(num + " ") and f.endswith(".mp4")]
    if len(hits) != 1:
        raise SystemExit(f"{num} 的源视频不唯一: {hits}")
    return os.path.join(SRC, hits[0])


def frames_of(num):
    # 帧长用源视频文件名里的帧数（补齐后帧数，17n+5）
    name = os.path.basename(video_path(num))
    return int(name.split(" ")[1].replace(".mp4", ""))


def orig_keep_frames():
    """原始帧数.txt：组装时每段保留的帧数，用来验收输出够不够长。"""
    keep = {}
    with open(ORIG_TABLE, encoding="utf-8") as f:
        for line in f:
            parts = line.split()
            if len(parts) >= 2 and parts[0].endswith(".mp4") and parts[0][:3].isdigit():
                keep[parts[0][:3]] = int(parts[1])
    return keep


def probe_frames(path):
    ffprobe = os.path.join(_FFDIR, "ffprobe.exe")
    if not os.path.isfile(ffprobe):
        ffprobe = "ffprobe"
    r = subprocess.run(
        [ffprobe, "-v", "error", "-select_streams", "v:0", "-count_frames",
         "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", path],
        capture_output=True, text=True)
    if r.returncode != 0:
        return None
    try:
        return int(r.stdout.strip())
    except ValueError:
        return None


def full_prompt(num):
    body = open(os.path.join(PROMPT, num + ".txt"), encoding="utf-8").read().strip()
    lines = []
    if num in TEXT_KEEP:
        lines.append(TEXT_KEEP_LINE)
    lines.append(SUFFIX)
    return body + "\n\n" + "\n".join(lines)


def make_namespace(num, prompt_text, seed, cfg, base):
    return types.SimpleNamespace(
        prompt=prompt_text, ar="16:9", mp=cfg.mp,
        seconds=frames_of(num) / 24.0, seed=seed, steps=cfg.steps,
        sr_scale=cfg.sr_scale, prefix=f"apt复刻/{num}", ref_size="max",
        image=[IMG[c] for c in CAST[num]], video=[video_path(num)],
        video_seconds=0, audio=[], base=base)


# ---------- 状态 ----------

def load_state():
    if os.path.exists(STATE):
        with open(STATE, encoding="utf-8") as f:
            return json.load(f)
    return {"tasks": {}}


def save_state(state):
    tmp = STATE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(tmp, STATE)


def attempts_of(state, num):
    return int(state["tasks"].get(num, {}).get("attempts") or 0)


def given_up(state, num):
    t = state["tasks"].get(num) or {}
    return t.get("status") == "FAILED" and attempts_of(state, num) >= MAX_ATTEMPTS


def is_active(state, num):
    t = state["tasks"].get(num) or {}
    return t.get("status") in ("RUNNING", "QUEUED") and bool(t.get("prompt_id"))


def needs_submit(state, num):
    t = state["tasks"].get(num)
    if t is None:
        return True
    if t.get("status") == "SUCCESS" and t.get("file"):
        return False
    if given_up(state, num):
        return False
    if t.get("status") == "FAILED":
        return True
    return False


# ---------- 提交 / 轮询 / 下载 ----------

def check_server(base):
    import requests
    try:
        requests.get(base + "/system_stats", timeout=5)
    except Exception as e:
        raise SystemExit(
            f"连不上 ComfyUI（{base}）：{e}\n"
            f"请先运行 D:\\ComfyUI_SparkH3\\运行comfyui - SparkH3.bat 启动服务")


def bypass_sr(graph):
    """2026-11-02 定档：默认绕过 RTX 超分。71(视频保存) 直连 79(VAEDecode)，删 67/69。
    build_graph 会无条件写 67 的缩放值，所以必须在建图之后再改接线。"""
    graph["71"]["inputs"]["images"] = ["79", 0]
    graph.pop("69", None)
    graph.pop("67", None)
    return graph


def submit(num, state, cfg, base):
    import requests
    attempts = attempts_of(state, num) + 1
    seed = cfg.seed if cfg.seed is not None else random.randrange(2 ** 48)
    prompt = full_prompt(num)
    ns = make_namespace(num, prompt, seed, cfg, base)
    template = json.load(open(cfg.template, encoding="utf-8"))
    print(f"{num}: 参考图 {len(ns.image)} 张 + 源视频 1 段，帧长 {frames_of(num)}，seed {seed}"
          f"，{'1920x1088 原生(无超分)' if not cfg.sr else f'超分x{cfg.sr_scale}'}", flush=True)
    graph = h3.build_graph(template, ns)  # 内含上传与标签核对
    if not cfg.sr:
        graph = bypass_sr(graph)
    pid = h3.submit(base, graph)
    state["tasks"][num] = {
        "prompt_id": pid, "status": "RUNNING", "seed": seed,
        "frames": frames_of(num), "attempts": attempts, "prefix": ns.prefix,
    }
    save_state(state)
    print(f"submitted {num} -> {pid} attempt {attempts}", flush=True)


def mark_failed(num, state, err):
    t = state["tasks"].setdefault(num, {})
    t["status"] = "FAILED"
    t["error"] = str(err)[:500]
    t["attempts"] = max(attempts_of(state, num), 1)
    save_state(state)
    n = t["attempts"]
    if n >= MAX_ATTEMPTS:
        print(f"{num} FAILED attempt {n}/{MAX_ATTEMPTS}, give up: {t['error']}", flush=True)
    else:
        print(f"{num} FAILED attempt {n}/{MAX_ATTEMPTS}, will retry: {t['error']}", flush=True)


def try_submit(num, state, cfg, base):
    try:
        submit(num, state, cfg, base)
        return True
    except SystemExit as e:
        mark_failed(num, state, e)
        return False
    except Exception as e:  # requests / OSError / JSON 等
        mark_failed(num, state, e)
        return False


def refresh(state, base):
    import requests
    for num, t in list(state["tasks"].items()):
        if t.get("status") != "RUNNING" or not t.get("prompt_id"):
            continue
        try:
            r = requests.get(f"{base}/history/{t['prompt_id']}", timeout=30).json()
        except Exception as e:
            print(f"{num} query error: {e}", flush=True)
            continue
        if t["prompt_id"] not in r:
            print(f"{num} 运行中/排队", flush=True)
            continue
        entry = r[t["prompt_id"]]
        status = entry.get("status", {})
        msgs = status.get("messages") or []
        err = next((m[1] for m in msgs if m and m[0] == "execution_error"), None)
        if err or status.get("status_str") == "error":
            reason = (err or {}).get("exception_message") or status.get("status_str") or "error"
            t["status"] = "FAILED"
            t["error"] = str(reason)[:500]
            n = attempts_of(state, num)
            if n >= MAX_ATTEMPTS:
                print(f"{num} FAILED attempt {n}/{MAX_ATTEMPTS}, give up: {t['error']}", flush=True)
            else:
                print(f"{num} FAILED attempt {n}/{MAX_ATTEMPTS}, will retry: {t['error']}", flush=True)
        elif status.get("completed"):
            files = []
            for out in (entry.get("outputs") or {}).values():
                for items in out.values():
                    if isinstance(items, list):
                        files += [it for it in items
                                  if isinstance(it, dict) and it.get("filename")]
            if not files:
                t["status"] = "FAILED"
                t["error"] = "completed but no output file"
                print(f"{num} completed but no output file", flush=True)
            else:
                t["results"] = files
                t["status"] = "SUCCESS"
                print(f"{num} SUCCESS {len(files)} file(s)", flush=True)
        else:
            print(f"{num} {status.get('status_str', '?')}", flush=True)
    save_state(state)


def download(state, base, keep=None):
    import requests
    keep = keep if keep is not None else orig_keep_frames()
    os.makedirs(OUT, exist_ok=True)
    for num, t in state["tasks"].items():
        if t.get("status") != "SUCCESS" or t.get("file"):
            continue
        files = t.get("results") or []
        if not files:
            continue
        # 取最后一个输出文件（与 rh_batch 一致；正常只有 VHS_VideoCombine 一个）
        it = files[-1]
        dest = os.path.join(OUT, f"{num}.mp4")
        try:
            with requests.get(f"{base}/view", params={
                    "filename": it["filename"], "subfolder": it.get("subfolder", ""),
                    "type": it.get("type", "output")}, stream=True, timeout=600) as r:
                r.raise_for_status()
                with open(dest, "wb") as f:
                    for chunk in r.iter_content(1 << 16):
                        f.write(chunk)
        except Exception as e:
            t["download_fails"] = int(t.get("download_fails") or 0) + 1
            print(f"{num} download error ({t['download_fails']}/3): {e}", flush=True)
            if t["download_fails"] >= 3:
                t["status"] = "FAILED"
                t["error"] = "download failed 3 times"
            save_state(state)
            continue
        got = probe_frames(dest)
        need = keep.get(num, 0)
        if got is not None and got < need:
            t["status"] = "FAILED"
            t["error"] = f"输出只有 {got} 帧，少于组装需要的 {need} 帧"
            t.pop("file", None)
            print(f"{num} FAILED: {t['error']}", flush=True)
            save_state(state)
            continue
        t["file"] = dest
        t["download_fails"] = 0
        save_state(state)
        print(f"downloaded {num} -> {dest} ({got} 帧)", flush=True)


def poll_and_download(state, base):
    refresh(state, base)
    download(state, base)


def active_nums(state):
    return [n for n in state["tasks"] if is_active(state, n)]


def fill_slots(nums, state, cfg, base, limit):
    submitted = []
    active = active_nums(state)
    for num in nums:
        if not needs_submit(state, num):
            if given_up(state, num):
                print(f"skip {num}, given up after {attempts_of(state, num)} failures", flush=True)
            elif state["tasks"].get(num, {}).get("status") == "SUCCESS":
                print(f"skip {num}, already SUCCESS", flush=True)
            else:
                print(f"skip {num}, already {state['tasks'][num].get('status')}", flush=True)
            continue
        while len(active) >= limit:
            print(f"在跑 {len(active)} 个，等 30 秒", flush=True)
            time.sleep(30)
            poll_and_download(state, base)
            active = active_nums(state)
            retry_now = [n for n in nums if needs_submit(state, n) and not given_up(state, n)]
            if retry_now and len(active) < limit:
                break
        if not needs_submit(state, num) or given_up(state, num):
            continue
        if try_submit(num, state, cfg, base):
            submitted.append(num)
        else:
            time.sleep(5)
        active = active_nums(state)
    return submitted


def wait_until_done(nums, state, cfg, base, limit):
    while True:
        poll_and_download(state, base)
        pending = [n for n in nums if needs_submit(state, n) and not given_up(state, n)]
        active = [n for n in nums if is_active(state, n)]
        if pending:
            fill_slots(pending, state, cfg, base, limit)
            continue
        if not active:
            break
        print(f"在跑 {len(active)} 个，等 30 秒", flush=True)
        time.sleep(30)


def report(state, nums):
    ok, failed = [], []
    for n in nums:
        t = state["tasks"].get(n) or {}
        (ok if t.get("status") == "SUCCESS" and t.get("file") else failed).append(n)
    print(f"完成 {len(ok)}/{len(nums)}", flush=True)
    if failed:
        print("失败或未完成： " + " ".join(failed), flush=True)
        for n in failed:
            t = state["tasks"].get(n) or {}
            print(f"  {n}: {t.get('status')} attempt {attempts_of(state, n)}/{MAX_ATTEMPTS}"
                  f" {t.get('error') or ''}", flush=True)
    return failed


def dry_run(nums, cfg, base):
    """干跑：上传素材、建图、打印摘要，不提交。"""
    check_server(base)
    template = json.load(open(cfg.template, encoding="utf-8"))
    for num in nums:
        seed = 12345
        ns = make_namespace(num, full_prompt(num), seed, cfg, base)
        h3.build_graph(template, ns)
        w, hh = h3.calc_resolution(ns.ar, ns.mp)
        mode = f"原生 {w}x{hh} (无超分)" if not cfg.sr else f"{w}x{hh} -> 超分x{cfg.sr_scale}"
        print(f"{num} 干跑 OK: {mode} | 帧长 {frames_of(num)} | "
              f"图 {len(ns.image)} 视频 {len(ns.video)} | 尾缀已追加"
              f"{'（含源片文字保留行）' if num in TEXT_KEEP else ''}", flush=True)


def main():
    ap = argparse.ArgumentParser(description="本地 ComfyUI SparkH3 批量提交")
    # 2026-11-02 用户定档：2MP 原生 1920x1088 直出、默认不用 RTX 超分（要回超分加 --sr）
    ap.add_argument("--mp", type=float, default=2.0, help="H3 生成分辨率(百万像素)，2.0 -> 1920x1088 原生")
    ap.add_argument("--sr", action="store_true", help="启用 RTX 超分节点（默认关闭，71 直连 VAEDecode）")
    ap.add_argument("--sr-scale", type=float, default=2.0, help="RTX 超分倍率（仅 --sr 时生效）")
    ap.add_argument("--steps", type=int, default=6)
    ap.add_argument("--seed", type=int, default=None, help="固定 seed（默认每段随机并记录在状态里）")
    ap.add_argument("--host", default=os.environ.get("COMFY_HOST", "127.0.0.1"))
    ap.add_argument("--port", type=int, default=int(os.environ.get("COMFY_PORT", "30001")))
    ap.add_argument("--template", default=os.path.join(H3_API_DIR, "H3-API-Spark-template.json"))
    ap.add_argument("cmd", choices=["submit", "status", "download", "print"])
    ap.add_argument("nums", nargs="*")
    cfg = ap.parse_args()
    base = f"http://{cfg.host}:{cfg.port}"

    if cfg.cmd in ("submit", "print"):
        nums = cfg.nums
        bad = [n for n in nums if n not in CAST]
        if not nums or bad:
            raise SystemExit(f"段号无效或为空: {bad}\n可提交的段: " + " ".join(sorted(CAST)))
        for n in nums:
            if not os.path.isfile(os.path.join(PROMPT, n + ".txt")):
                raise SystemExit(f"缺少 提示词\\{n}.txt")

    state = load_state()
    if cfg.cmd == "submit":
        check_server(base)
        limit = concurrency()
        fill_slots(nums, state, cfg, base, limit)
        wait_until_done(nums, state, cfg, base, limit)
        report(state, nums)
    elif cfg.cmd in ("status", "download"):
        if state["tasks"]:
            check_server(base)
            poll_and_download(state, base)
        else:
            print("还没有任务记录", flush=True)
    elif cfg.cmd == "print":
        dry_run(nums, cfg, base)


if __name__ == "__main__":
    main()
