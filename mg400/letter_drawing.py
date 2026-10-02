#Create a plan and a way for the robot to move- send the plan to actually write

from .letters import get_letter_strokes


def create_letter_plan(letter):
    strokes = get_letter_strokes(letter)

    plan = []

    for stroke in strokes:
        if not stroke:
            continue

        first_x, first_y = stroke[0]

        plan.append({
            "action": "pen_up"
        })

        plan.append({
            "action": "move",
            "x": first_x,
            "y": first_y
        })

        plan.append({
            "action": "pen_down"
        })

        for x, y in stroke[1:]:
            plan.append({
                "action": "move",
                "x": x,
                "y": y
            })

        plan.append({
            "action": "pen_up"
        })

    return plan