import asyncio
import json
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from schema.poc.verifications import PocRunStatus
from service.poc.verifications import (
    _build_nuclei_execution_command,
    _execute_direct_nuclei,
    classify_nuclei_execution,
    render_poc_command,
)


class PocResultClassificationTest(unittest.TestCase):
    def test_matched_result(self):
        output = json.dumps({"template-id": "demo", "matcher-status": True})

        status, reason = classify_nuclei_execution(output, 0)

        self.assertEqual(status, PocRunStatus.PASSED)
        self.assertEqual(reason, "")

    def test_completed_without_match(self):
        output = json.dumps({"template-id": "demo", "matcher-status": False})

        status, reason = classify_nuclei_execution(output, 0)

        self.assertEqual(status, PocRunStatus.FAILED)
        self.assertIn("未满足", reason)

    def test_unreachable_target_is_execution_error(self):
        output = json.dumps({
            "template-id": "demo",
            "matcher-status": False,
            "error": "port closed or filtered",
        })

        status, reason = classify_nuclei_execution(output, 0)

        self.assertEqual(status, PocRunStatus.ERROR)
        self.assertIn("目标端口关闭", reason)

    def test_invalid_target_is_execution_error(self):
        output = json.dumps({
            "template-id": "demo",
            "matcher-status": False,
            "error": "failed to parse url got invalid scheme",
        })

        status, reason = classify_nuclei_execution(output, 0)

        self.assertEqual(status, PocRunStatus.ERROR)
        self.assertIn("目标地址格式", reason)

    def test_partial_request_error_keeps_completed_no_match(self):
        output = "\n".join([
            json.dumps({"template-id": "demo", "matcher-status": False}),
            json.dumps({
                "template-id": "demo",
                "matcher-status": False,
                "error": "connection refused",
            }),
        ])

        status, reason = classify_nuclei_execution(output, 0)

        self.assertEqual(status, PocRunStatus.FAILED)
        self.assertIn("部分请求失败", reason)

    def test_engine_failure_uses_diagnostic(self):
        status, reason = classify_nuclei_execution("[FTL] template loading failed", 1)

        self.assertEqual(status, PocRunStatus.ERROR)
        self.assertIn("template loading failed", reason)

    @unittest.skipUnless(Path("/usr/local/bin/nuclei").is_file(), "Nuclei is not installed")
    def test_tscan_style_template_end_to_end(self):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                body = (
                    b"most recent call last\nTraceback\nDON'T PANIC"
                    if self.path == "/match"
                    else b"normal page"
                )
                self.send_response(200)
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_args):
                pass

        template = {
            "id": "dont-panic-traceback",
            "info": {
                "name": "DON'T PANIC Traceback",
                "author": ["ritikchaddha"],
                "severity": "low",
            },
            "http": [{
                "method": "GET",
                "path": ["{{BaseURL}}"],
                "matchers": [{
                    "type": "word",
                    "part": "body",
                    "words": ["most recent call last", "Traceback", "DON'T PANIC"],
                    "condition": "and",
                    "case-insensitive": True,
                }],
            }],
        }
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        old_nuclei = os.environ.get("DAYBREAK_NUCLEI_BIN")
        os.environ["DAYBREAK_NUCLEI_BIN"] = "/usr/local/bin/nuclei"

        async def execute(target):
            command = render_poc_command(_build_nuclei_execution_command(template), target)
            output, exit_code = await _execute_direct_nuclei(command, 30)
            return classify_nuclei_execution(output, exit_code)

        try:
            port = server.server_address[1]
            matched = asyncio.run(execute(f"http://127.0.0.1:{port}/match"))
            not_matched = asyncio.run(execute(f"http://127.0.0.1:{port}/normal"))
            unreachable = asyncio.run(execute("http://127.0.0.1:1"))
        finally:
            server.shutdown()
            server.server_close()
            if old_nuclei is None:
                os.environ.pop("DAYBREAK_NUCLEI_BIN", None)
            else:
                os.environ["DAYBREAK_NUCLEI_BIN"] = old_nuclei

        self.assertEqual(matched, (PocRunStatus.PASSED, ""))
        self.assertEqual(not_matched[0], PocRunStatus.FAILED)
        self.assertIn("未满足", not_matched[1])
        self.assertEqual(unreachable[0], PocRunStatus.ERROR)
        self.assertIn("目标端口关闭", unreachable[1])


if __name__ == "__main__":
    unittest.main()
