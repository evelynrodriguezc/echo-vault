"""Control digit: uppercase, letters A=1..Z=26, digits kept, separators dropped, ISO 7064 style 98 - (100N mod 97)."""


def to_number(body):
    digits = ""
    for ch in body.upper():
        if ch.isdigit():
            digits += ch
        elif "A" <= ch <= "Z":
            digits += str(ord(ch) - 64)
    return int(digits or "0")


def control(body):
    return 98 - (100 * to_number(body)) % 97
