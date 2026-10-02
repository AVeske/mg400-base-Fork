#Letter coordinates, that will be sent to draw the letters

LETTERS = {
    "A": [
        [(0, 0), (10, 30), (20, 0)],
        [(5, 15), (15, 15)],
    ],

    "B": [
        [(0, 0), (0, 30)],
        [(0, 30), (12, 30), (16, 25), (12, 20), (0, 20)],
        [(0, 20), (12, 20), (16, 15), (12, 10), (0, 10)],
    ],

    "C": [
        [(18, 27), (14, 30), (5, 30), (0, 25), (0, 5), (5, 0), (14, 0), (18, 3)],
    ],
}

def get_letter_strokes(letter):
    letter = letter.upper()

    if letter not in LETTERS:
        raise ValueError(f"Unknown letter: {letter}")

    return LETTERS[letter]