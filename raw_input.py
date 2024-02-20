""" cross platofrm module to handle raw input from terminal """
import os
import sys

if os.name == "posix":
    import termios
    import tty
elif os.name == "nt":
    from msvcrt import getch as getch_encoded
else:
    sys.exit("Operating system not recognised")


# CLEAN TERMINAL
if os.name == "posix":
    def clear():
        """ clear screen """
        os.system("clear")
elif os.name == "nt":
    def clear():
        """ clear screen """
        os.system("cls")


# FETCH KEYBOARD INPUT
if os.name == "posix":
    def getch() -> str:
        """ read raw terminal input """
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

    conv_arrows = {"D": "left", "C": "right", "A": "up", "B": "down"}
    def get_key() -> str:
        """ process correct string for keyboard input """
        key_pressed = getch()
        match key_pressed:
            case "\r":
                return "enter"
            case "\t":
                return "tab"
            case "\x1b":
                if getch() == "[":
                    return conv_arrows.get(getch(), None)
            case "\x7f":
                return "backspace"
            case _:
                return key_pressed

elif os.name == "nt":
    def getch() -> str:
        """ read raw terminal input """
        letter = getch_encoded()
        try:
            return letter.decode('ascii')
        except:
            return letter

    conv_arrows = {"K": "left", "M": "right", "H": "up", "P": "down"}
    def get_key() -> str:
        """ process correct string for keyboard input """
        key_pressed = getch()
        match key_pressed:
            case "\r":
                return "enter"
            case "\t":
                return "tab"
            case b"\xe0":
                return conv_arrows.get(getch(), None)
            case b"\x08":
                return "backspace"
            case _:
                return key_pressed