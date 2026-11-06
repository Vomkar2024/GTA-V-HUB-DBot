from __future__ import annotations

import unittest

from gta_hub.branding import FOOTER, PURPLE, make_embed, safe_latency_ms, safe_url, truncate


class BrandingUnitTests(unittest.TestCase):
    def test_safe_latency_ms(self) -> None:
        self.assertEqual(safe_latency_ms(0.045), "45 ms")
        self.assertEqual(safe_latency_ms(0.1234), "123 ms")
        self.assertEqual(safe_latency_ms(float("inf")), "N/A")
        self.assertEqual(safe_latency_ms(float("-inf")), "N/A")
        self.assertEqual(safe_latency_ms(float("nan")), "N/A")
        self.assertEqual(safe_latency_ms(-0.5), "N/A")
        self.assertEqual(safe_latency_ms(None), "N/A")
        self.assertEqual(safe_latency_ms("invalid"), "N/A")

    def test_make_embed(self) -> None:
        embed = make_embed("Test Title", "Test Description")
        self.assertEqual(embed.title, "Test Title")
        self.assertEqual(embed.description, "Test Description")
        self.assertEqual(embed.color, PURPLE)
        self.assertEqual(embed.footer.text, FOOTER)

    def test_truncate(self) -> None:
        self.assertEqual(truncate("Hello World", 5), "Hell…")
        self.assertEqual(truncate("Short", 10), "Short")
        self.assertEqual(truncate("", 5), "")
        self.assertEqual(truncate(None, 5), "")
        self.assertEqual(truncate("A", 1), "A")
        self.assertEqual(truncate("Long string", 0), "")

    def test_safe_url(self) -> None:
        self.assertEqual(safe_url("https://rockstargames.com"), "https://rockstargames.com")
        self.assertEqual(safe_url("http://localhost:8080"), "http://localhost:8080")
        self.assertIsNone(safe_url("javascript:alert(1)"))
        self.assertIsNone(safe_url("ftp://example.com"))
        self.assertIsNone(safe_url(None))
        self.assertIsNone(safe_url("https://" + "a" * 600))


if __name__ == "__main__":
    unittest.main()
