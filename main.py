#!/usr/bin/env python

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
class Instructions(object):
    def __init__(self):
        self.y = 0.0
        self.y_delta = 0.06

    def add(self, msg):
        self.y += self.y_delta
        return OnscreenText(text=msg, style=1, fg=(1, 1, 1, 1), scale=.05,
                            shadow=(0, 0, 0, 1), parent=base.a2dTopLeft,
                            pos=(0.08, -self.y - 0.04), align=TextNode.ALeft)

BACKGROUND_COLOR = (0, 0, 0, 1) # BLACK
CAMERA_DISTANCE_MAX = 5.0 
CAMERA_DISTANCE_MIN = 2.0
CAMERA_TARGET_HEIGHT_DELTA = 3.0
CAMERA_POSITION_HEIGHT_DELTA_MIN = 1.0
CAMERA_POSITION_HEIGHT_DELTA_MAX = 2.0

class Game(ShowBase):
    def __init__(self):
        # Set up the window, camera, etc.
        ShowBase.__init__(self)

        # Set the background color to black
        self.win.setClearColor(BACKGROUND_COLOR)

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

        def key_on(name):
            return lambda: self.setKey(name, True)
        def key_off(name):
            return lambda: self.setKey(name, False)
        # Accept the control keys for movement and rotation
        key_map = [
            # alias            key          action                help
            # -----            ------       ------                ----
            ("escape",         None,        lambda: sys.exit(),   '[ESC]: Quit'),
            ("arrow_left",     'left',      key_on("left"),       "[Left Arrow]: Rotate Left"),
            ("arrow_right",    'right',     key_on("right"),      "[Right Arrow]: Rotate Right"),
            ("arrow_up",       'forward',   key_on("forward"),    "[Up Arrow]: Run Forward"),
            ("arrow_down",     'backward',  key_on("backward"),   "[Down Arrow]: Run Backward"),
            ("a",              'cam-left',  key_on("cam-left"),   "[A]: Rotate Camera Left"),
            ("s",              'cam-right', key_on("cam-right"),  "[S]: Rotate Camera Right"),
            ("arrow_left-up",  'left',      key_off("left"),      None),
            ("arrow_right-up", 'right',     key_off("right"),     None),
            ("arrow_up-up",    'forward',   key_off("forward"),   None),
            ("arrow_down-up",  'backward',  key_off("backward"),  None),
            ("a-up",           'cam-left',  key_off("cam-left"),  None),
            ("s-up",           'cam-right', key_off("cam-right"), None),
            ]
        self.keyMap = {}
        inst = Instructions()
        for alias, key, action, description in key_map:
            self.setKey(key, False)
            self.accept(alias, action)
            if description:
                inst.add(description)

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
        self.playerGroundColNp.show()
        self.camGroundColNp.show()

        # Uncomment this line to show a visual representation of the
        # collisions occuring
        self.cTrav.showCollisions(render)

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
        if camdist > CAMERA_DISTANCE_MAX:
            self.camera.setPos(self.camera.getPos() + camvec * (camdist - int(CAMERA_DISTANCE_MAX)))
            camdist = CAMERA_DISTANCE_MAX
        if camdist < CAMERA_DISTANCE_MIN:
            self.camera.setPos(self.camera.getPos() - camvec * (int(CAMERA_DISTANCE_MIN) - camdist))
            camdist = CAMERA_DISTANCE_MIN

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
