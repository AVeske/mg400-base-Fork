from flask import jsonify, request

from .letter_drawing import create_letter_plan


def register_letter_routes(app, letter_queue):

    @app.route("/api/letter", methods=["POST"])
    def receive_letter():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify(ok=False, error="Expected a JSON object"), 400

        job_id = data.get("id")
        if "id" in data and (type(job_id) is not int or not 0 <= job_id <= 2147483647):
            return jsonify(ok=False, error="id must be a non-negative 32-bit integer"), 400

        letter = data.get("letter")

        if not letter:
            return jsonify({
                "ok": False,
                "error": "Missing letter"
            }), 400

        if not isinstance(letter, str):
            return jsonify(ok=False, error="letter must be a string"), 400
        letter = letter.upper()

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

        letter_queue.add(letter, job_id=job_id)

        print(f"Queued letter: {letter}")

        return jsonify({
            "ok": True,
            "letter": letter,
            "id": job_id,
            "queued": True,
            "pending": letter_queue.pending_count()
        }), 202