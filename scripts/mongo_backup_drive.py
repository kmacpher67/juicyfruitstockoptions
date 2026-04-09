#!/usr/bin/env python3
"""Google Drive backup helper for Mongo backup package files.

Requires one of:
- DRIVE_ACCESS_TOKEN env var
- DRIVE_ACCESS_TOKEN_CMD env var (command returning access token)

Supports:
- upload
- verify
- upload-and-verify
- retention
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import mimetypes
import os
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any
from urllib import error, parse, request

DRIVE_API_BASE = "https://www.googleapis.com/drive/v3"
DRIVE_UPLOAD_BASE = "https://www.googleapis.com/upload/drive/v3/files"


def _utc_now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def _get_token(cli_token: str | None) -> str:
    if cli_token:
        return cli_token.strip()

    env_token = os.environ.get("DRIVE_ACCESS_TOKEN", "").strip()
    if env_token:
        return env_token

    token_cmd = os.environ.get("DRIVE_ACCESS_TOKEN_CMD", "").strip()
    if token_cmd:
        try:
            proc = subprocess.run(token_cmd, shell=True, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as exc:
            stderr = (exc.stderr or "").strip()
            stdout = (exc.stdout or "").strip()
            detail = stderr or stdout or str(exc)
            raise RuntimeError(
                "DRIVE_ACCESS_TOKEN_CMD failed. "
                f"Command: {token_cmd!r}. Details: {detail}"
            ) from exc

        token = proc.stdout.strip()
        if token:
            return token
        raise RuntimeError(
            "DRIVE_ACCESS_TOKEN_CMD returned an empty token. "
            f"Command: {token_cmd!r}"
        )

    raise RuntimeError(
        "No Google Drive token available. "
        "Set DRIVE_ACCESS_TOKEN or DRIVE_ACCESS_TOKEN_CMD "
        "(recommended: DRIVE_ACCESS_TOKEN_CMD='gcloud auth application-default print-access-token')."
    )


def _http_json(url: str, method: str, token: str, data: bytes | None = None, headers: dict[str, str] | None = None) -> dict[str, Any]:
    req_headers = {
        "Authorization": f"Bearer {token}",
    }
    if headers:
        req_headers.update(headers)

    req = request.Request(url, data=data, method=method, headers=req_headers)
    try:
        with request.urlopen(req, timeout=120) as resp:
            body = resp.read()
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Drive API error {exc.code}: {detail}") from exc

    if not body:
        return {}
    return json.loads(body.decode("utf-8"))


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _upload_file(local_file: Path, folder_id: str, token: str) -> dict[str, Any]:
    if not local_file.is_file():
        raise FileNotFoundError(f"Backup package not found: {local_file}")

    meta = {
        "name": local_file.name,
        "parents": [folder_id],
    }

    mime = mimetypes.guess_type(local_file.name)[0] or "application/octet-stream"

    boundary = f"====codex-{uuid.uuid4().hex}===="
    meta_part = (
        f"--{boundary}\r\n"
        "Content-Type: application/json; charset=UTF-8\r\n\r\n"
        f"{json.dumps(meta)}\r\n"
    ).encode("utf-8")

    with local_file.open("rb") as fh:
        file_bytes = fh.read()

    file_part_header = (
        f"--{boundary}\r\n"
        f"Content-Type: {mime}\r\n\r\n"
    ).encode("utf-8")

    ending = f"\r\n--{boundary}--\r\n".encode("utf-8")
    body = meta_part + file_part_header + file_bytes + ending

    url = (
        f"{DRIVE_UPLOAD_BASE}?uploadType=multipart"
        "&fields=id,name,size,createdTime,modifiedTime,webViewLink,md5Checksum"
    )

    return _http_json(
        url,
        method="POST",
        token=token,
        data=body,
        headers={
            "Content-Type": f"multipart/related; boundary={boundary}",
        },
    )


def _download_file_bytes(file_id: str, token: str) -> bytes:
    url = f"{DRIVE_API_BASE}/files/{parse.quote(file_id)}?alt=media"
    req = request.Request(url, method="GET", headers={"Authorization": f"Bearer {token}"})
    try:
        with request.urlopen(req, timeout=300) as resp:
            return resp.read()
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Drive download error {exc.code}: {detail}") from exc


def _list_files(folder_id: str, token: str, prefix: str) -> list[dict[str, Any]]:
    q = f"'{folder_id}' in parents and trashed=false and name contains '{prefix}'"
    params = parse.urlencode(
        {
            "q": q,
            "fields": "files(id,name,createdTime,modifiedTime,size,webViewLink,md5Checksum)",
            "orderBy": "createdTime desc",
            "pageSize": "1000",
            "supportsAllDrives": "true",
            "includeItemsFromAllDrives": "true",
        }
    )
    url = f"{DRIVE_API_BASE}/files?{params}"
    payload = _http_json(url, method="GET", token=token)
    return payload.get("files", [])


def _delete_file(file_id: str, token: str) -> None:
    url = f"{DRIVE_API_BASE}/files/{parse.quote(file_id)}?supportsAllDrives=true"
    _http_json(url, method="DELETE", token=token)


def _append_log(log_file: Path, payload: dict[str, Any]) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=True) + "\n")


def cmd_upload(args: argparse.Namespace) -> int:
    token = _get_token(args.token)
    local_file = Path(args.file).resolve()

    upload = _upload_file(local_file, args.folder_id, token)
    result = {
        "timestamp_utc": _utc_now_iso(),
        "action": "upload",
        "local_file": str(local_file),
        "local_sha256": _file_sha256(local_file),
        "remote": upload,
    }
    _append_log(Path(args.log_file), result)
    print(json.dumps(result, indent=2))
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    token = _get_token(args.token)
    local_file = Path(args.file).resolve()
    remote_bytes = _download_file_bytes(args.file_id, token)

    local_sha = _file_sha256(local_file)
    remote_sha = hashlib.sha256(remote_bytes).hexdigest()
    ok = local_sha == remote_sha

    result = {
        "timestamp_utc": _utc_now_iso(),
        "action": "verify",
        "local_file": str(local_file),
        "file_id": args.file_id,
        "local_sha256": local_sha,
        "remote_sha256": remote_sha,
        "checksum_match": ok,
    }
    _append_log(Path(args.log_file), result)
    print(json.dumps(result, indent=2))
    return 0 if ok else 2


def cmd_upload_and_verify(args: argparse.Namespace) -> int:
    token = _get_token(args.token)
    local_file = Path(args.file).resolve()

    upload = _upload_file(local_file, args.folder_id, token)
    file_id = upload.get("id")
    if not file_id:
        raise RuntimeError(f"Upload response missing file id: {upload}")

    remote_bytes = _download_file_bytes(file_id, token)
    local_sha = _file_sha256(local_file)
    remote_sha = hashlib.sha256(remote_bytes).hexdigest()
    ok = local_sha == remote_sha

    result = {
        "timestamp_utc": _utc_now_iso(),
        "action": "upload-and-verify",
        "local_file": str(local_file),
        "local_sha256": local_sha,
        "remote_sha256": remote_sha,
        "checksum_match": ok,
        "remote": upload,
    }
    _append_log(Path(args.log_file), result)
    print(json.dumps(result, indent=2))
    return 0 if ok else 2


def cmd_retention(args: argparse.Namespace) -> int:
    token = _get_token(args.token)
    files = _list_files(args.folder_id, token, args.prefix)

    now = dt.datetime.now(dt.timezone.utc)
    cutoff = now - dt.timedelta(days=args.keep_days)

    kept = 0
    deleted: list[dict[str, Any]] = []

    for idx, item in enumerate(files):
        created_raw = item.get("createdTime")
        created = None
        if created_raw:
            created = dt.datetime.fromisoformat(created_raw.replace("Z", "+00:00"))

        keep = idx < args.keep_min
        if created and created >= cutoff:
            keep = True

        if keep:
            kept += 1
            continue

        file_id = item.get("id")
        if not file_id:
            continue
        _delete_file(file_id, token)
        deleted.append(item)

    result = {
        "timestamp_utc": _utc_now_iso(),
        "action": "retention",
        "folder_id": args.folder_id,
        "prefix": args.prefix,
        "keep_days": args.keep_days,
        "keep_min": args.keep_min,
        "total_seen": len(files),
        "kept": kept,
        "deleted": len(deleted),
        "deleted_files": [{"id": f.get("id"), "name": f.get("name")} for f in deleted],
    }
    _append_log(Path(args.log_file), result)
    print(json.dumps(result, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Google Drive helper for Mongo backup package automation")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_common(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--token", default=None, help="Google OAuth access token (optional if env provided)")
        sp.add_argument("--log-file", default="./logs/mongo_backup_drive_ops.jsonl")

    up = sub.add_parser("upload", help="Upload backup package to Drive folder")
    up.add_argument("--file", required=True)
    up.add_argument("--folder-id", required=True)
    add_common(up)
    up.set_defaults(func=cmd_upload)

    vf = sub.add_parser("verify", help="Verify remote file checksum by downloading and comparing")
    vf.add_argument("--file", required=True)
    vf.add_argument("--file-id", required=True)
    add_common(vf)
    vf.set_defaults(func=cmd_verify)

    uav = sub.add_parser("upload-and-verify", help="Upload file then verify checksum by re-download")
    uav.add_argument("--file", required=True)
    uav.add_argument("--folder-id", required=True)
    add_common(uav)
    uav.set_defaults(func=cmd_upload_and_verify)

    rt = sub.add_parser("retention", help="Delete old backup files from Drive folder")
    rt.add_argument("--folder-id", required=True)
    rt.add_argument("--prefix", default="mongo_backup_")
    rt.add_argument("--keep-days", type=int, default=30)
    rt.add_argument("--keep-min", type=int, default=10)
    add_common(rt)
    rt.set_defaults(func=cmd_retention)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
