from flask import jsonify, request

from .letter_drawing import create_letter_plan
from .robot_writer import write_plan, writer_configured


def register_letter_routes(app, move_function):

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

        try:
            plan = create_letter_plan(letter)
        except ValueError as error:
            return jsonify({
                "ok": False,
                "error": str(error)
            }), 400

        print(f"Received letter: {letter}")

        for step in plan:
            print(step)

        print("Writer configured:", writer_configured())

        if writer_configured():
            try:
                print("Starting robot write")

                write_plan(plan, move_function)

                print("Robot write finished")

            except RuntimeError as error:
                print("Robot write error:", error)

                return jsonify({
                    "ok": False,
                    "letter": letter,
                    "error": str(error)
                }), 500

        return jsonify({
            "ok": True,
            "letter": letter,
            "steps": len(plan),
            "robot_configured": writer_configured()
        })