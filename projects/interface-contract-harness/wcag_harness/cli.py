"""Command-line interface."""

from __future__ import annotations

import argparse
import functools
import json
import sys
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .engine import common_project_base, execute_suite
from .model import ContractInputError
from .reports import verify_report_bundle, write_report_bundle


def _run(manifest: Path, output: Path) -> tuple[dict[str, object], int]:
    report, inputs = execute_suite(manifest)
    base = common_project_base(manifest, output)
    write_report_bundle(report, inputs, output, base)
    status = report["suite"]["status"]
    result: dict[str, object] = {
        "cases": report["summary"]["cases"],
        "fixture_bundle_sha256": report["input_binding"]["bundle_sha256"],
        "report": str((output / "report.html").resolve()),
        "status": status,
    }
    return result, 0 if status == "matched" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="interface-contract-harness",
        description="Run bounded accessibility-oriented contracts over synthetic HTML fixtures.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser("run", help="run a fixture manifest")
    run_parser.add_argument("--manifest", type=Path, default=Path("fixtures/manifest.json"))
    run_parser.add_argument("--out", type=Path, default=Path("build"))
    verify_parser = subparsers.add_parser("verify", help="verify a report hash chain")
    verify_parser.add_argument("--audit", type=Path, default=Path("build/audit.json"))
    verify_parser.add_argument("--seal", type=Path, default=Path("build/audit.sha256"))
    demo_parser = subparsers.add_parser("demo", help="build, and optionally serve, the demo")
    demo_parser.add_argument("--manifest", type=Path, default=Path("fixtures/manifest.json"))
    demo_parser.add_argument("--out", type=Path, default=Path("build"))
    demo_parser.add_argument("--serve", action="store_true")
    demo_parser.add_argument("--open", action="store_true", dest="open_browser")
    demo_parser.add_argument("--host", default="127.0.0.1")
    demo_parser.add_argument("--port", type=int, default=8765)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "verify":
            print(json.dumps(verify_report_bundle(args.audit, args.seal), sort_keys=True))
            return 0
        if args.command == "demo":
            if args.open_browser and not args.serve:
                raise ContractInputError("--open requires --serve")
            if not 1 <= args.port <= 65_535:
                raise ContractInputError("demo port must be between 1 and 65535")
            if args.host not in {"127.0.0.1", "localhost", "::1"}:
                raise ContractInputError("demo server host must be loopback-only")
        result, exit_code = _run(args.manifest, args.out)
        print(json.dumps(result, sort_keys=True))
        if args.command == "demo" and args.serve:
            if exit_code:
                print("refusing to serve a regressed demo", file=sys.stderr)
                return exit_code
            base = common_project_base(args.manifest, args.out)
            relative_report = (args.out.resolve() / "report.html").relative_to(base)
            url = f"http://{args.host}:{args.port}/{relative_report.as_posix()}"
            handler = functools.partial(SimpleHTTPRequestHandler, directory=str(base))
            server = ThreadingHTTPServer((args.host, args.port), handler)
            print(f"serving {url}", file=sys.stderr)
            if args.open_browser:
                webbrowser.open(url)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
            finally:
                server.server_close()
        return exit_code
    except ContractInputError as exc:
        print(json.dumps({"error": str(exc), "status": "input-rejected"}, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
