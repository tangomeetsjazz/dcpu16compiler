def start():
    x = (1 + 3 - 2) * 2 / 4 % 2
    y = doSomething(x)
    
    if y == 1 or not (x >= 3):
        z = y
    elif y == 2:
        z = 2
    else:
        z = x

    SCREEN[45] = 563

    end()

def doSomething(a):
    return 5

def end():
    exit()
