from flask import jsonify, request

from .letter_drawing import create_letter_plan


def register_letter_routes(app, letter_queue):

    @app.route("/api/letter", methods=["POST"])
    def receive_letter():
        data = request.json or {}

        letter = data.get("letter")

        if not letter:
            return jsonify({
                "ok": False,
                "error": "Missing letter"
            }), 400

        letter = str(letter).upper()

        if len(letter) != 1:
            return jsonify({
                "ok": False,
                "error": "Letter must contain exactly one character"
            }), 400

        # Kontrollime enne queue'sse lisamist,
        # et selline täht üldse olemas on.
        try:
            create_letter_plan(letter)
        except ValueError as error:
            return jsonify({
                "ok": False,
                "error": str(error)
            }), 400

        letter_queue.add(letter)

        print(f"Queued letter: {letter}")

        return jsonify({
            "ok": True,
            "letter": letter,
            "queued": True,
            "pending": letter_queue.pending_count()
        }), 202