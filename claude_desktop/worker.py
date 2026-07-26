# Claude Desktop — streaming worker thread
# Victorious Framework | Origin Source Labs

import anthropic
from PyQt6.QtCore import QThread, pyqtSignal


class StreamWorker(QThread):
    """Runs a Claude streaming request off the main thread."""

    chunk = pyqtSignal(str)          # text delta
    thinking_chunk = pyqtSignal(str) # thinking delta
    finished = pyqtSignal(dict)      # usage stats
    error = pyqtSignal(str)          # error message

    def __init__(self, api_key: str, params: dict):
        super().__init__()
        self._api_key = api_key
        self._params = params
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        try:
            client = anthropic.Anthropic(api_key=self._api_key)
            usage = {}

            with client.messages.stream(**self._params) as stream:
                for event in stream:
                    if self._stop:
                        break

                    if event.type == "content_block_start":
                        pass  # block type tracked via delta events

                    elif event.type == "content_block_delta":
                        delta = event.delta
                        if delta.type == "text_delta":
                            self.chunk.emit(delta.text)
                        elif delta.type == "thinking_delta":
                            self.thinking_chunk.emit(delta.thinking)

                if not self._stop:
                    msg = stream.get_final_message()
                    usage = {
                        "input": msg.usage.input_tokens,
                        "output": msg.usage.output_tokens,
                        "cache_read": getattr(msg.usage, "cache_read_input_tokens", 0) or 0,
                        "cache_write": getattr(msg.usage, "cache_creation_input_tokens", 0) or 0,
                    }

            self.finished.emit(usage)

        except anthropic.AuthenticationError:
            self.error.emit("Authentication failed — check your API key in Settings.")
        except anthropic.RateLimitError:
            self.error.emit("Rate limit reached. Please wait a moment and try again.")
        except anthropic.BadRequestError as e:
            self.error.emit(f"Bad request: {e.message}")
        except anthropic.APIConnectionError:
            self.error.emit("Connection error — check your internet connection.")
        except Exception as e:
            self.error.emit(str(e))
