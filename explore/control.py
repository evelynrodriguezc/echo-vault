"""Control digit: uppercase, letters A=1..Z=26, digits kept, separators dropped, ISO 7064 style 98 - (100N mod 97)."""


def to_digits(body):
    digits = ""
    for ch in body.upper():
        if "0" <= ch <= "9":  # ASCII only: unicode digits are ignored like other symbols
            digits += ch
        elif "A" <= ch <= "Z":
            digits += str(ord(ch) - 64)
    return digits or "0"


def control(body):
    r = 0
    for d in to_digits(body):  # streaming mod 97: no big integers, any message length
        r = (r * 10 + int(d)) % 97
    return 98 - (100 * r) % 97
