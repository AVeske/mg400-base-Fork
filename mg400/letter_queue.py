import queue
import threading

from .letter_drawing import create_letter_plan
from .letters import get_letter_width
from .robot_writer import write_plan


LETTER_GAP = 5.0


class LetterQueue:
    def __init__(self, move_function):
        self.move_function = move_function

        self.queue = queue.Queue()

        # Järgmise tähe alguspunkt lokaalses X-suunas.
        self.cursor_x = 0.0

        self.worker = threading.Thread(
            target=self._worker_loop,
            daemon=True,
        )

        self.worker.start()

    def add(self, letter):
        self.queue.put(letter)

    def pending_count(self):
        return self.queue.qsize()

    def _worker_loop(self):
        while True:
            letter = self.queue.get()

            try:
                print(f"Writing queued letter: {letter}")

                plan = create_letter_plan(letter)

                write_plan(
                    plan,
                    self.move_function,
                    offset_x=self.cursor_x,
                )

                width = get_letter_width(letter)

                self.cursor_x += width + LETTER_GAP

                print(
                    f"Finished letter {letter}. "
                    f"Next cursor: {self.cursor_x:.1f} mm"
                )

            except Exception as error:
                print(f"Letter write failed: {error}")

            finally:
                self.queue.task_done()