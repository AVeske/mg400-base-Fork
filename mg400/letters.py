#Letter coordinates, that will be sent to draw the letters

LETTERS = {
    "A": [
        [(0, 0), (8, 24), (16, 0)],
        [(4, 12), (12, 12)],
    ],

    "B": [
        [(0, 0), (0, 24)],
        [(0, 24), (10, 24), (14, 21), (14, 15), (10, 12), (0, 12)],
        [(0, 12), (10, 12), (14, 9), (14, 3), (10, 0), (0, 0)],
    ],

    "C": [
        [(16, 21), (13, 24), (4, 24), (0, 20), (0, 4), (4, 0), (13, 0), (16, 3)],
    ],

    "S": [
        [(16, 24), (4, 24), (0, 20), (0, 16), (12, 16), (16, 12), (16, 4), (12, 0), (0, 0)],
    ],

    "D": [
        [(0, 0), (0, 24)],
        [(0, 24), (9, 24), (14, 20), (16, 14), (16, 10), (14, 4), (9, 0), (0, 0)],
    ],

    "I": [
        [(2, 24), (14, 24)],
        [(8, 24), (8, 0)],
        [(2, 0), (14, 0)],
    ],

    "T": [
        [(0, 24), (16, 24)],
        [(8, 24), (8, 0)],
    ],

    "H": [
        [(0, 0), (0, 24)],
        [(16, 0), (16, 24)],
        [(0, 12), (16, 12)],
        ],

    "E": [
        [(0, 0), (0, 24)],
        [(0, 24), (16, 24)],
        [(0, 12), (12, 12)],
        [(0, 0), (16, 0)],
    ],
}

def get_letter_strokes(letter):
    letter = letter.upper()

    if letter not in LETTERS:
        raise ValueError(f"Unknown letter: {letter}")

    return LETTERS[letter]

def get_letter_width(letter):
    strokes = get_letter_strokes(letter)

    x_values = [
        x
        for stroke in strokes
        for x, _ in stroke
    ]

    return max(x_values) - min(x_values)