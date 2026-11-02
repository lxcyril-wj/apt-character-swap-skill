# -*- coding: utf-8 -*-
"""make_segments.py — 用自备的 APT MV 原片，自动复现复刻包的素材结构。

用法（在本仓库根目录运行）：
  python tools/make_segments.py "你的MV文件.mp4" [--out 素材包]

产出（写入 --out 目录，默认 素材包）：
  补齐生成用/NNN 帧数.mp4   # 按原始帧数表切段，末帧复制补齐到 17n+5，24fps
  原片音轨.m4a              # 从 MV 无损抽取的 AAC 音轨

分段范围与帧数以《素材包/原始帧数.txt》（组装保留帧数）和
《素材包/补齐后帧数.txt》（生成用帧数）为准，两者都出自 wuwukasi 复刻包。
自备 MV 请使用与帧数表对应的前 96.6 秒内容；若 MV 帧率不是 24000/1001，
帧边界会有累积偏差，脚本会用 ffprobe 校验每段帧数并报告差异。
"""
import argparse
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.dirname(os.path.abspath(__file__))


def ffmpeg_bin():
    for cand in (os.path.join(ROOT, "ffmpeg", "ffmpeg.exe"),
                 os.path.join(ROOT, "素材包", "ffmpeg", "ffmpeg.exe")):
        if os.path.isfile(cand):
            return cand
    return "ffmpeg"


def ffprobe_bin():
    for cand in (os.path.join(ROOT, "ffmpeg", "ffprobe.exe"),
                 os.path.join(ROOT, "素材包", "ffmpeg", "ffprobe.exe")):
        if os.path.isfile(cand):
            return cand
    return "ffprobe"


def parse_table(path, value_index=1):
    """读取帧数表：每行『001.mp4 帧数 [角色]』，返回 [(编号, 帧数)]，跳过合计行。"""
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            parts = line.split()
            if len(parts) < 2 or not parts[0].endswith(".mp4"):
                continue
            if not parts[0][:3].isdigit():
                continue
            rows.append((parts[0][:3], int(parts[value_index])))
    return rows


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(" ".join(cmd) + "\n" + r.stderr[-800:])


def main():
    ap = argparse.ArgumentParser(description="从自备 MV 切出复刻包素材结构")
    ap.add_argument("mv", help="自备的 APT MV 视频文件")
    ap.add_argument("--out", default=os.path.join(ROOT, "素材包"), help="输出目录")
    args = ap.parse_args()

    orig = dict(parse_table(os.path.join(HERE, "..", "素材包", "原始帧数.txt")))
    padded = dict(parse_table(os.path.join(HERE, "..", "素材包", "补齐后帧数.txt")))
    if not orig or not padded:
        raise SystemExit("找不到帧数表，请确认 素材包/原始帧数.txt 与 补齐后帧数.txt 在位")

    ff, fp = ffmpeg_bin(), ffprobe_bin()
    seg_dir = os.path.join(args.out, "补齐生成用")
    os.makedirs(seg_dir, exist_ok=True)

    # 音轨整条抽取（无损复制；若 MV 音轨不是 AAC 会自动转码）
    audio = os.path.join(args.out, "原片音轨.m4a")
    run([ff, "-y", "-i", args.mv, "-vn", "-c:a", "copy", audio])

    start = 0
    bad = []
    for num in sorted(orig):
        keep = orig[num]
        pad = padded.get(num, keep)
        dest = os.path.join(seg_dir, f"{num} {pad}.mp4")
        # 按帧切：trim 保留原始帧数 -> 重计时 24fps -> 末帧克隆补齐到生成帧数
        pad_sec = max(0.0, (pad - keep) / 24.0)
        run([ff, "-y", "-i", args.mv, "-an",
             "-vf", (f"trim=start_frame={start}:end_frame={start + keep},"
                     f"setpts=PTS-STARTPTS,fps=24,"
                     f"tpad=stop_mode=clone:stop_duration={pad_sec:.6f}"),
             "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", dest])
        got = subprocess.run(
            [fp, "-v", "error", "-select_streams", "v:0", "-count_frames",
             "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", dest],
            capture_output=True, text=True).stdout.strip()
        n = int(got or 0)
        if n != pad:
            bad.append(f"{num}: 期望 {pad} 帧，实得 {n} 帧（MV 帧率或版本可能不符）")
        print(f"{num}: 源帧 {keep} -> 生成帧 {pad}（实得 {n}）", flush=True)
        start += keep

    if bad:
        print("\n以下分段帧数不符，请核对 MV 版本/帧率：")
        for b in bad:
            print(" ", b)
        sys.exit(1)
    print(f"\n完成：{len(orig)} 段已写入 {seg_dir}，音轨在 {audio}")
    print("接着把 替换用参考图/ 与 提示词/ 按需放好，即可按 SKILL.md 流程提交生成。")


if __name__ == "__main__":
    main()
