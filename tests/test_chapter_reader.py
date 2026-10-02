import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"


class FixtureHandler(BaseHTTPRequestHandler):
    manifest_status = 200
    manifest_body = []
    manifest_raw = None

    def log_message(self, format, *args):
        pass

    def _send(self, status, content_type, body=b""):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _route(self):
        path = unquote(urlparse(self.path).path)

        if path in ("/", "/index.html"):
            self._send(200, "text/html; charset=utf-8", (ROOT / "index.html").read_bytes())
        elif path == "/chapters.json":
            if self.manifest_status == 200:
                body = self.manifest_raw
                if body is None:
                    body = json.dumps(self.manifest_body, ensure_ascii=False).encode("utf-8")
                self._send(200, "application/json; charset=utf-8", body)
            else:
                self._send(self.manifest_status, "text/plain", b"missing")
        elif path.endswith(".pdf") and "-" in Path(path).name:
            self._send(200, "application/pdf", b"%PDF-1.7 fixture")
        else:
            self._send(404, "text/plain", b"missing")

    def do_GET(self):
        self._route()

    def do_HEAD(self):
        self._route()


class ChapterManifestTests(unittest.TestCase):
    def setUp(self):
        FixtureHandler.manifest_status = 200
        FixtureHandler.manifest_body = []
        FixtureHandler.manifest_raw = None
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=True, executable_path=CHROME)

    def tearDown(self):
        self.browser.close()
        self.playwright.stop()
        self.server.shutdown()
        self.server.server_close()

    def open_page(self, viewport=None):
        page = self.browser.new_page(viewport=viewport or {"width": 1280, "height": 900})
        page.goto(f"http://127.0.0.1:{self.server.server_port}/index.html", wait_until="networkidle")
        return page

    def test_parses_and_sorts_named_pdf_files(self):
        FixtureHandler.manifest_body = [
            {"name": "10-dziesiąty.pdf", "path": "/unblack/10-dziesiąty.pdf"},
            {"name": "not-a-chapter.pdf", "path": "/unblack/not-a-chapter.pdf"},
            {"name": "2-drugi_rozdział.pdf", "path": "/unblack/2-drugi_rozdział.pdf"},
            {"name": "0-wstęp.pdf", "path": "/unblack/0-wstęp.pdf"},
        ]

        page = self.open_page()
        buttons = page.locator(".chapter-button")

        self.assertEqual(buttons.count(), 3)
        self.assertIn("00", buttons.nth(0).inner_text())
        self.assertIn("Wstęp", buttons.nth(0).inner_text())
        self.assertIn("02", buttons.nth(1).inner_text())
        self.assertIn("Drugi rozdział", buttons.nth(1).inner_text())
        self.assertIn("10", buttons.nth(2).inner_text())
        self.assertIn("Dziesiąty", buttons.nth(2).inner_text())

        buttons.nth(1).click()
        self.assertEqual(page.locator("#pdfViewer").get_attribute("src"), "/unblack/2-drugi_rozdzia%C5%82.pdf#view=FitH")
        self.assertEqual(page.locator("#downloadButton").get_attribute("href"), "/unblack/2-drugi_rozdzia%C5%82.pdf")
        self.assertEqual(page.locator("#downloadButton").get_attribute("download"), "2-drugi_rozdział.pdf")

    def test_duplicate_index(self):
        FixtureHandler.manifest_body = [
            {"name": "1-pierwszy.pdf", "path": "/unblack/1-pierwszy.pdf"},
            {"name": "1-drugi.pdf", "path": "/unblack/1-drugi.pdf"},
        ]

        page = self.open_page()

        self.assertEqual(page.locator("#chapterHeading").inner_text(), "Błąd konfiguracji")
        self.assertIn("1", page.locator(".chapter-message").inner_text())
        self.assertEqual(page.locator(".chapter-button").count(), 0)

    def test_manifest_failure(self):
        FixtureHandler.manifest_raw = b"not-json"

        page = self.open_page()

        self.assertEqual(page.locator("#chapterHeading").inner_text(), "Błąd konfiguracji")
        self.assertEqual(page.locator("#openButton").get_attribute("href"), None)
        self.assertEqual(page.locator("#downloadButton").get_attribute("href"), None)
        self.assertEqual(page.locator("#openButton").get_attribute("aria-disabled"), "true")

    def test_empty_manifest(self):
        FixtureHandler.manifest_body = [
            {"name": "okladka.pdf", "path": "/unblack/okladka.pdf"},
        ]

        page = self.open_page()

        self.assertEqual(page.locator("#chapterHeading").inner_text(), "Brak rozdziałów")
        self.assertIn("0-wstęp.pdf", page.locator(".chapter-message").inner_text())

    def test_file_fallback(self):
        page = self.browser.new_page(viewport={"width": 390, "height": 844})
        page.goto((ROOT / "index.html").resolve().as_uri(), wait_until="load")
        page.wait_for_function("document.querySelector('#chapterList').getAttribute('aria-busy') === 'false'")

        self.assertEqual(page.locator(".chapter-button").count(), 1)
        self.assertEqual(page.locator("#chapterHeading").inner_text(), "Wstęp")
        self.assertEqual(page.locator("#pdfViewer").get_attribute("src"), "0-wstęp.pdf#view=FitH")
        self.assertIn("GitHub Pages", page.locator("#readerHelp").inner_text())

    def test_unprocessed_jekyll_manifest_uses_local_fallback(self):
        FixtureHandler.manifest_raw = (ROOT / "chapters.json").read_bytes()

        page = self.open_page()

        self.assertEqual(page.locator(".chapter-button").count(), 1)
        self.assertEqual(page.locator("#chapterHeading").inner_text(), "Wstęp")
        self.assertEqual(page.locator("#pdfViewer").get_attribute("src"), "0-wstęp.pdf#view=FitH")
        self.assertIn("GitHub Pages", page.locator("#readerHelp").inner_text())

    def test_filename_markup_is_rendered_as_text(self):
        FixtureHandler.manifest_body = [
            {
                "name": "1-<img src=x onerror=window.titleInjected=1>.pdf",
                "path": "/unblack/1-title.pdf",
            },
        ]

        page = self.open_page()

        self.assertEqual(page.locator(".chapter-title img").count(), 0)
        self.assertEqual(page.evaluate("window.titleInjected"), None)
        self.assertIn("<img", page.locator(".chapter-title").inner_text())

    def test_pdf_path_segments_are_url_encoded(self):
        FixtureHandler.manifest_body = [
            {"name": "1-a#b.pdf", "path": "/unblack/1-a#b.pdf"},
        ]

        page = self.open_page()

        self.assertEqual(
            page.locator("#pdfViewer").get_attribute("src"),
            "/unblack/1-a%23b.pdf#view=FitH",
        )
        self.assertEqual(
            page.locator("#downloadButton").get_attribute("href"),
            "/unblack/1-a%23b.pdf",
        )

    def test_navigation_and_responsive_layout(self):
        FixtureHandler.manifest_body = [
            {"name": "0-wstęp.pdf", "path": "/unblack/0-wstęp.pdf"},
            {"name": "1-pierwszy.pdf", "path": "/unblack/1-pierwszy.pdf"},
            {"name": "2-drugi.pdf", "path": "/unblack/2-drugi.pdf"},
        ]

        for viewport in ({"width": 390, "height": 844}, {"width": 1440, "height": 1000}):
            with self.subTest(viewport=viewport):
                page = self.browser.new_page(viewport=viewport)
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(f"http://127.0.0.1:{self.server.server_port}/index.html", wait_until="networkidle")

                self.assertTrue(page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth"))
                self.assertEqual(page.locator(".chapter-button[aria-current='true']").count(), 1)
                self.assertIn("Wstęp", page.locator(".chapter-button[aria-current='true']").inner_text())

                page.locator("#nextChapter").click()
                self.assertEqual(page.locator("#chapterHeading").inner_text(), "Pierwszy")
                self.assertIn("01", page.locator(".chapter-button[aria-current='true']").inner_text())
                self.assertEqual(page.locator("#downloadButton").get_attribute("download"), "1-pierwszy.pdf")
                self.assertFalse(page.locator("#previousChapter").is_disabled())
                self.assertFalse(errors, errors)
                page.close()


if __name__ == "__main__":
    unittest.main()
