import queue
import threading

from .letter_drawing import create_letter_plan
from .letters import get_letter_width
from .robot_writer import write_plan


LETTER_GAP = 5.0


class LetterQueue:
    def __init__(self, move_function, result_reporter=None):
        self.move_function = move_function
        self.result_reporter = result_reporter

        self.queue = queue.Queue()

        # Järgmise tähe alguspunkt lokaalses X-suunas.
        self.cursor_x = 0.0

        self.worker = threading.Thread(
            target=self._worker_loop,
            daemon=True,
        )

        self.worker.start()

    def add(self, letter, job_id=None):
        self.queue.put((letter, job_id))

    def pending_count(self):
        return self.queue.qsize()

    def _process_job(self, letter, job_id):
        result = "error"
        try:
            print(f"Writing queued letter: {letter} (id={job_id})")
            plan = create_letter_plan(letter)
            # write_plan waits for every move, including the final pen lift.
            write_plan(plan, self.move_function, offset_x=self.cursor_x)
            self.cursor_x += get_letter_width(letter) + LETTER_GAP
            result = "done"
            print(f"Finished letter {letter}. Next cursor: {self.cursor_x:.1f} mm")
        except Exception as error:
            print(f"Letter write failed (id={job_id}): {error}")

        # Reporting failures must never requeue or redraw the letter.
        if job_id is not None and self.result_reporter is not None:
            try:
                self.result_reporter.submit(job_id, result)
            except Exception as error:
                print(f"Could not queue result for job {job_id}: {error}")

    def _worker_loop(self):
        while True:
            letter, job_id = self.queue.get()
            try:
                self._process_job(letter, job_id)
            finally:
                self.queue.task_done()
