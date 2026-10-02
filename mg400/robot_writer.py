#Will do the actual writing on the robot
# Need väärtused määratakse laboris päris roboti, paberi ja pastakahoidiku järgi.
ORIGIN_X = -39.0
ORIGIN_Y = -364.0

PEN_UP_Z = -60.0
PEN_DOWN_Z = -72.0

TOOL_R = -68.0


def writer_configured():
    return all(
        value is not None
        for value in (
            ORIGIN_X,
            ORIGIN_Y,
            PEN_UP_Z,
            PEN_DOWN_Z,
        )
    )


def _require_config():
    if not writer_configured():
        raise RuntimeError(
            "Robot writer is not configured. "
            "Set ORIGIN_X, ORIGIN_Y, PEN_UP_Z and PEN_DOWN_Z."
        )


def _move(move_function, x, y, z):
    print(f"Calling move_to: x={x}, y={y}, z={z}")

    ok, reason = move_function(
        x=x,
        y=y,
        z=z,
        r=TOOL_R,
        wait=True,
    )

    print(f"move_to result: ok={ok}, reason={reason}")

    if not ok:
        raise RuntimeError(
            f"Robot move failed at x={x}, y={y}, z={z}: {reason}"
        )


def write_plan(plan, move_function):
    """
    Execute a drawing plan using the supplied robot movement function.

    X/Y coordinates in the plan are relative to ORIGIN_X/ORIGIN_Y.
    """

    _require_config()

    current_x = ORIGIN_X
    current_y = ORIGIN_Y
    pen_down = False

    for step in plan:
        action = step["action"]

        if action == "pen_up":
            pen_down = False

            _move(
                move_function,
                current_x,
                current_y,
                PEN_UP_Z,
            )

        elif action == "pen_down":
            pen_down = True

            _move(
                move_function,
                current_x,
                current_y,
                PEN_DOWN_Z,
            )

        elif action == "move":
            current_x = ORIGIN_X + step["x"]
            current_y = ORIGIN_Y + step["y"]

            z = PEN_DOWN_Z if pen_down else PEN_UP_Z

            _move(
                move_function,
                current_x,
                current_y,
                z,
            )

        else:
            raise ValueError(f"Unknown drawing action: {action}")