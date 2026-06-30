from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import mimetypes
import os
from pathlib import Path
import sys
import urllib.error
import urllib.request
import uuid


def load_active_projects(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    projects = payload.get("projects", payload)
    if not isinstance(projects, list):
        raise ValueError("Project config must be a list or an object with a 'projects' list.")

    return [
        project
        for project in projects
        if isinstance(project, dict) and project.get("status", "active") == "active"
    ]


def _join_items(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return "；".join(str(item).strip() for item in value if str(item).strip())
    return str(value).strip()


def build_report(projects: list[dict], now: dt.datetime | None = None) -> str:
    current = now or dt.datetime.now()
    lines = [
        f"早上好，今天是 {current:%Y-%m-%d}。",
        "以下是正在推进项目的早报。",
        "",
    ]

    if not projects:
        lines.append("目前没有标记为 active 的项目。")
        return "\n".join(lines)

    for index, project in enumerate(projects, start=1):
        lines.append(f"{index}. {project.get('name', '未命名项目')}")

        goal = _join_items(project.get("goal"))
        if goal:
            lines.append(f"目标：{goal}")

        progress = _join_items(project.get("progress"))
        if progress:
            lines.append(f"进展：{progress}")

        next_step = _join_items(project.get("next"))
        if next_step:
            lines.append(f"下一步：{next_step}")

        blockers = _join_items(project.get("blockers"))
        if blockers:
            lines.append(f"风险或阻塞：{blockers}")

        lines.append("")

    return "\n".join(lines).strip() + "\n"


async def synthesize_edge_tts(text: str, output_path: Path, voice: str) -> None:
    try:
        import edge_tts
    except ImportError as exc:
        raise RuntimeError(
            "edge-tts is not installed. Run: python -m pip install -e '.[tts]'"
        ) from exc

    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(output_path))


def post_discord_webhook(webhook_url: str, content: str, audio_path: Path | None = None) -> None:
    if audio_path is None:
        body = json.dumps({"content": content[:1900]}, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            webhook_url,
            data=body,
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
    else:
        boundary = uuid.uuid4().hex
        payload = json.dumps({"content": content[:1800]}, ensure_ascii=False).encode("utf-8")
        file_bytes = audio_path.read_bytes()
        file_type = mimetypes.guess_type(audio_path.name)[0] or "audio/mpeg"

        parts = [
            f"--{boundary}\r\n".encode("utf-8"),
            b'Content-Disposition: form-data; name="payload_json"\r\n',
            b"Content-Type: application/json; charset=utf-8\r\n\r\n",
            payload,
            b"\r\n",
            f"--{boundary}\r\n".encode("utf-8"),
            f'Content-Disposition: form-data; name="files[0]"; filename="{audio_path.name}"\r\n'.encode(
                "utf-8"
            ),
            f"Content-Type: {file_type}\r\n\r\n".encode("utf-8"),
            file_bytes,
            b"\r\n",
            f"--{boundary}--\r\n".encode("utf-8"),
        ]
        request = urllib.request.Request(
            webhook_url,
            data=b"".join(parts),
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            if response.status >= 400:
                raise RuntimeError(f"Discord webhook failed with HTTP {response.status}.")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Discord webhook failed with HTTP {exc.code}: {detail}") from exc


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate and send a Chinese morning report.")
    parser.add_argument("--projects", type=Path, default=Path("config/projects.json"))
    parser.add_argument("--out-dir", type=Path, default=Path("out"))
    parser.add_argument("--tts-provider", choices=["none", "edge"], default=os.getenv("TTS_PROVIDER", "edge"))
    parser.add_argument("--voice", default=os.getenv("TTS_VOICE", "zh-CN-XiaoxiaoNeural"))
    parser.add_argument("--send-discord", action="store_true")
    parser.add_argument("--discord-webhook-url", default=os.getenv("DISCORD_WEBHOOK_URL"))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    args.out_dir.mkdir(parents=True, exist_ok=True)

    projects = load_active_projects(args.projects)
    report = build_report(projects)

    report_path = args.out_dir / "morning-report.txt"
    report_path.write_text(report, encoding="utf-8")

    audio_path: Path | None = None
    if args.tts_provider == "edge":
        audio_path = args.out_dir / "morning-report.mp3"
        asyncio.run(synthesize_edge_tts(report, audio_path, args.voice))

    if args.send_discord:
        if not args.discord_webhook_url:
            raise RuntimeError("DISCORD_WEBHOOK_URL is required when --send-discord is set.")
        post_discord_webhook(args.discord_webhook_url, report, audio_path)

    print(report)
    print(f"Wrote {report_path}")
    if audio_path:
        print(f"Wrote {audio_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

