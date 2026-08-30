import unittest

from app.main import app


class SpeechApiTests(unittest.TestCase):
    def test_transcription_route_is_registered(self) -> None:
        route = next((route for route in app.routes if getattr(route, "path", None) == "/api/speech/transcribe"), None)

        self.assertIsNotNone(route)
        self.assertIn("POST", route.methods)


if __name__ == "__main__":
    unittest.main()
