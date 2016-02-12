#!/usr/bin/env python

# Author: Ryan Myers
# Models: Jeff Styers, Reagan Heller
#
# Last Updated: 2015-03-13
#
# This tutorial provides an example of creating a character
# and having it walk around on uneven terrain, as well
# as implementing a fully rotatable camera.

from direct.showbase.ShowBase import ShowBase
from panda3d.core import CollisionTraverser, CollisionNode
from panda3d.core import CollisionHandlerQueue, CollisionRay
from panda3d.core import Filename, AmbientLight, DirectionalLight
from panda3d.core import PandaNode, NodePath, Camera, TextNode
from panda3d.core import CollideMask
from direct.gui.OnscreenText import OnscreenText
from direct.actor.Actor import Actor
import random
import sys
import os
import math

# Function to put instructions on the screen.
def addInstructions(pos, msg):
    return OnscreenText(text=msg, style=1, fg=(1, 1, 1, 1), scale=.05,
                        shadow=(0, 0, 0, 1), parent=base.a2dTopLeft,
                        pos=(0.08, -pos - 0.04), align=TextNode.ALeft)

CAMDIST_MAX = 5.0
CAMDIST_MIN = 2.0
CAMERA_TARGET_HEIGHT_DELTA = 3.0
CAMERA_POSITION_HEIGHT_DELTA_MIN = 1.0
CAMERA_POSITION_HEIGHT_DELTA_MAX = 2.0

class Game(ShowBase):
    def __init__(self):
        # Set up the window, camera, etc.
        ShowBase.__init__(self)

        # Set the background color to black
        self.win.setClearColor((0, 0, 0, 1))

        # This is used to store which keys are currently pressed.
        self.keyMap = {
            "left": 0, "right": 0, "forward": 0, "backward": 0, "cam-left": 0, "cam-right": 0}

        # Post the instructions
        self.inst1 = addInstructions(0.06, "[ESC]: Quit")
        self.inst2 = addInstructions(0.12, "[Left Arrow]: Rotate Left")
        self.inst3 = addInstructions(0.18, "[Right Arrow]: Rotate Right")
        self.inst4 = addInstructions(0.24, "[Up Arrow]: Run Forward")
        self.inst5 = addInstructions(0.30, "[Down Arrow]: Run Backward")
        self.inst6 = addInstructions(0.36, "[A]: Rotate Camera Left")
        self.inst7 = addInstructions(0.42, "[S]: Rotate Camera Right")

        # Set up the environment
        #
        # This environment model contains collision meshes.  If you look
        # in the egg file, you will see the following:
        #
        #    <Collide> { Polyset keep descend }
        #
        # This tag causes the following mesh to be converted to a collision
        # mesh -- a mesh which is optimized for collision, not rendering.
        # It also keeps the original mesh, so there are now two copies ---
        # one optimized for rendering, one for collisions.

        self.environ = loader.loadModel("models/world")
        self.environ.reparentTo(render)

        # Create the main character

        playerStartPos = self.environ.find("**/start_point").getPos()
        self.player = Actor("models/player",
                           {"run": "models/player-run",
                            "walk": "models/player-walk"})
        self.player.reparentTo(render)
        self.player.setScale(.2)
        self.player.setPos(playerStartPos + (0, 0, 0.5))

        # Create a floater object, which floats 2 units above player.  We
        # use this as a target for the camera to look at.

        self.floater = NodePath(PandaNode("floater"))
        self.floater.reparentTo(self.player)
        self.floater.setZ(CAMERA_TARGET_HEIGHT_DELTA)

        # Accept the control keys for movement and rotation

        key_map = {
            "escape":         lambda: sys.exit(),
            "arrow_left":     lambda: self.setKey("left", True),
            "arrow_right":    lambda: self.setKey("right", True),
            "arrow_up":       lambda: self.setKey("forward", True),
            "arrow_down":     lambda: self.setKey("backward", True),
            "a":              lambda: self.setKey("cam-left", True),
            "s":              lambda: self.setKey("cam-right", True),
            "arrow_left-up":  lambda: self.setKey("left", False),
            "arrow_right-up": lambda: self.setKey("right", False),
            "arrow_up-up":    lambda: self.setKey("forward", False),
            "arrow_down-up":  lambda: self.setKey("backward", False),
            "a-up":           lambda: self.setKey("cam-left", False),
            "s-up":           lambda: self.setKey("cam-right", False)
            }
        for key, action in key_map.iteritems():
            self.accept(key, action)

        taskMgr.add(self.move, "moveTask")

        # Game state variables
        self.isMoving = False

        # Set up the camera
        self.disableMouse()
        self.camera.setPos(self.player.getX(), self.player.getY() + 10, 2)

        # We will detect the height of the terrain by creating a collision
        # ray and casting it downward toward the terrain.  One ray will
        # start above player's head, and the other will start above the camera.
        # A ray may hit the terrain, or it may hit a rock or a tree.  If it
        # hits the terrain, we can detect the height.  If it hits anything
        # else, we rule that the move is illegal.
        self.cTrav = CollisionTraverser()

        self.playerGroundRay = CollisionRay()
        self.playerGroundRay.setOrigin(0, 0, 9)
        self.playerGroundRay.setDirection(0, 0, -1)
        self.playerGroundCol = CollisionNode('playerRay')
        self.playerGroundCol.addSolid(self.playerGroundRay)
        self.playerGroundCol.setFromCollideMask(CollideMask.bit(0))
        self.playerGroundCol.setIntoCollideMask(CollideMask.allOff())
        self.playerGroundColNp = self.player.attachNewNode(self.playerGroundCol)
        self.playerGroundHandler = CollisionHandlerQueue()
        self.cTrav.addCollider(self.playerGroundColNp, self.playerGroundHandler)

        self.camGroundRay = CollisionRay()
        self.camGroundRay.setOrigin(0, 0, 9)
        self.camGroundRay.setDirection(0, 0, -1)
        self.camGroundCol = CollisionNode('camRay')
        self.camGroundCol.addSolid(self.camGroundRay)
        self.camGroundCol.setFromCollideMask(CollideMask.bit(0))
        self.camGroundCol.setIntoCollideMask(CollideMask.allOff())
        self.camGroundColNp = self.camera.attachNewNode(self.camGroundCol)
        self.camGroundHandler = CollisionHandlerQueue()
        self.cTrav.addCollider(self.camGroundColNp, self.camGroundHandler)

        # Uncomment this line to see the collision rays
        #self.playerGroundColNp.show()
        #self.camGroundColNp.show()

        # Uncomment this line to show a visual representation of the
        # collisions occuring
        #self.cTrav.showCollisions(render)

        # Create some lighting
        ambientLight = AmbientLight("ambientLight")
        ambientLight.setColor((.3, .3, .3, 1))
        directionalLight = DirectionalLight("directionalLight")
        directionalLight.setDirection((-5, -5, -5))
        directionalLight.setColor((1, 1, 1, 1))
        directionalLight.setSpecularColor((1, 1, 1, 1))
        render.setLight(render.attachNewNode(ambientLight))
        render.setLight(render.attachNewNode(directionalLight))

    # Records the state of the arrow keys
    def setKey(self, key, value):
        self.keyMap[key] = value

    # Accepts arrow keys to move either the player or the menu cursor,
    # Also deals with grid checking and collision detection
    def move(self, task):

        # Get the time that elapsed since last frame.  We multiply this with
        # the desired speed in order to find out with which distance to move
        # in order to achieve that desired speed.
        dt = globalClock.getDt()

        # If the camera-left key is pressed, move camera left.
        # If the camera-right key is pressed, move camera right.

        if self.keyMap["cam-left"]:
            self.camera.setX(self.camera, -20 * dt)
        if self.keyMap["cam-right"]:
            self.camera.setX(self.camera, +20 * dt)

        # save player's initial position so that we can restore it,
        # in case he falls off the map or runs into something.

        startpos = self.player.getPos()

        # If a move-key is pressed, move player in the specified direction.

        if self.keyMap["left"]:
            self.player.setH(self.player.getH() + 300 * dt)
        if self.keyMap["right"]:
            self.player.setH(self.player.getH() - 300 * dt)
        if self.keyMap["forward"]:
            self.player.setY(self.player, -25 * dt)
        if self.keyMap["backward"]:
            self.player.setY(self.player, 25 * dt)

        # If player is moving, loop the run animation.
        # If he is standing still, stop the animation.

        if self.keyMap["forward"] or self.keyMap["backward"] or self.keyMap["left"] or self.keyMap["right"]:
            if self.isMoving is False:
                self.player.loop("run")
                self.isMoving = True
        else:
            if self.isMoving:
                self.player.stop()
                self.player.pose("walk", 5)
                self.isMoving = False

        # If the camera is too far from player, move it closer.
        # If the camera is too close to player, move it farther.

        camvec = self.player.getPos() - self.camera.getPos()
        camvec.setZ(0)
        camdist = camvec.length()
        camvec.normalize()
        if camdist > CAMDIST_MAX:
            self.camera.setPos(self.camera.getPos() + camvec * (camdist - int(CAMDIST_MAX)))
            camdist = CAMDIST_MAX
        if camdist < CAMDIST_MIN:
            self.camera.setPos(self.camera.getPos() - camvec * (int(CAMDIST_MIN) - camdist))
            camdist = CAMDIST_MIN

        # Normally, we would have to call traverse() to check for collisions.
        # However, the class ShowBase that we inherit from has a task to do
        # this for us, if we assign a CollisionTraverser to self.cTrav.
        self.cTrav.traverse(render)

        # Adjust player's Z coordinate.  If player's ray hit terrain,
        # update his Z. If it hit anything else, or didn't hit anything, put
        # him back where he was last frame.

        entries = list(self.playerGroundHandler.getEntries())
        entries.sort(key=lambda x: x.getSurfacePoint(render).getZ())

        if len(entries) > 0 and entries[0].getIntoNode().getName() == "terrain":
            self.player.setZ(entries[0].getSurfacePoint(render).getZ())
        else:
            self.player.setPos(startpos)

        # Keep the camera at one foot above the terrain,
        # or two feet above player, whichever is greater.

        entries = list(self.camGroundHandler.getEntries())
        entries.sort(key=lambda x: x.getSurfacePoint(render).getZ())

        if len(entries) > 0 and entries[0].getIntoNode().getName() == "terrain":
            self.camera.setZ(entries[0].getSurfacePoint(render).getZ() + CAMERA_POSITION_HEIGHT_DELTA_MIN)
        if self.camera.getZ() < self.player.getZ() + CAMERA_POSITION_HEIGHT_DELTA_MAX:
            self.camera.setZ(self.player.getZ() + CAMERA_POSITION_HEIGHT_DELTA_MAX)

        # The camera should look in player's direction,
        # but it should also try to stay horizontal, so look at
        # a floater which hovers above player's head.
        self.camera.lookAt(self.floater)

        return task.cont


game = Game()
game.run()
