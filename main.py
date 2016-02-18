#!/usr/bin/env python

from direct.showbase.ShowBase import ShowBase

def main():
    print "Please wait while initializing Panda3d..."
    stub = ShowBase()
    stub.destroy()

    print "Now launching the real thing in a loop..."
    exec("import game")
    while True:
        exec("game.Game().run()")
        exec("reload(game)")

if __name__ == '__main__':
    main()

