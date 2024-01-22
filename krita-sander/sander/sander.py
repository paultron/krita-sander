import sys
import os
import json


from urllib.request import urlopen, Request
from pathlib import Path
from random import randint, random, shuffle

from krita import * # Krita, DockWidget

from PyQt5.QtCore import QFile, QByteArray
from PyQt5.QtWidgets import QDockWidget, QFileDialog, QWidget, QPushButton, QVBoxLayout, QLabel
from PyQt5.QtGui import QIcon, QImage
from PyQt5.uic import loadUi

DOCKER_TITLE = 'Sander'


AIR =   '0'
SAND =  '1'
WATER = '2'
OIL =   '3'
ROCK =  '4'
BLOOD = '5'


AIRC =   [255, 255, 255, 255]
SANDC =  [255, 255, 0,   255]
WATERC = [0,   0,   255, 255]
OILC =   [64,  64,   64, 255]
ROCKC =  [128, 128, 128, 255]
BLOODC = [255, 0, 0,   255]

# WIDTH = 0
# HEIGHT = 0


# self.pixelBytes = QByteArray([])

def getType(rgba):
    match rgba:
        case [255, 255, 255, 255]: 
            return AIR
        case [255, 255, 0,   255]: 
            return SAND
        case [0,0,255,255]: 
            return WATER
        case [128,128,128,255]: 
            return ROCK
        case [255, 0, 0,   255]: 
            return BLOOD
        case _: 
            return "INVALID"
        
def tofl(rgba: list):
    return [x/255.0 for x in rgba]

def unfl(rgba: list):
    return [round(x*255) for x in rgba]

def cmul(rgbaTop, rgbaBtm):
    rgbaBtm = [x/255.0 for x in rgbaBtm]
    rgbaTop = [x/255.0 for x in rgbaTop]
    return unfl([rgbaTop[x]*rgbaBtm[x] for x in range(4)])

def getRGBA (img: QByteArray, indx):
    #takes whole xy pre div by 4
    indx = int(4*indx)
    # BGRA TO RGBA
    return [int.from_bytes(img[indx + 2], 'little'), 
            int.from_bytes(img[indx + 1], 'little'), 
            int.from_bytes(img[indx + 0], 'little'), 
            int.from_bytes(img[indx + 3], 'little')]






class Sander(DockWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(DOCKER_TITLE)

        #path = os.fspath(Path(__file__).resolve().parent / "form.ui")

        #ui_file = QFile(path)
        #ui_file.open(QFile.ReadOnly)
        #self.uiForm = loadUi(ui_file)
        #ui_file.close()

        mainWidget = QWidget(self)

        self.buttonRead = QPushButton("Read", mainWidget)
        self.buttonRead.clicked.connect(self.readLayer)

        mainWidget.setLayout(QVBoxLayout())
        mainWidget.layout().addWidget(self.buttonRead)

        ##self.label1 = QLabel("")
        ##mainWidget.layout().addWidget(self.label1)

        self.buttonAdv = QPushButton("Adv", mainWidget)
        self.buttonAdv.clicked.connect(self.advance)
        self.buttonAdv.setDisabled(True)

        #mainWidget.setLayout(QVBoxLayout())
        mainWidget.layout().addWidget(self.buttonAdv)


        self.setWidget(mainWidget)

    def canvasChanged(self, canvas):
        pass

    def readLayer(self):
        self.activeDocument = Krita.instance().activeDocument()
        self.activeNode = self.activeDocument.activeNode()
        self.WIDTH = self.activeDocument.width()
        self.HEIGHT = self.activeDocument.height()
        self.pixelBytes = QByteArray(self.activeNode.pixelData(0, 0, self.WIDTH, self.HEIGHT))
        self.elems = [getType(getRGBA(self.pixelBytes, x)) for x in range(0, self.WIDTH*self.HEIGHT)]
        #  self.buttonRead.setText("".join(self.elems))
        self.momentum = [0]*self.WIDTH*self.HEIGHT # x,y
        self.hasColoredFlags = [False]*self.WIDTH*self.HEIGHT
        self.hasMovedFlags = [False]*self.WIDTH*self.HEIGHT
        self.buttonAdv.setDisabled(False)

    def advance(self):
        self.activeDocument = Krita.instance().activeDocument()
        self.activeNode = self.activeDocument.activeNode()
        self.WIDTH = self.activeDocument.width()
        self.HEIGHT = self.activeDocument.height()
        self.pixelBytes = QByteArray(self.activeNode.pixelData(0, 0, self.WIDTH, self.HEIGHT))

        for ind in range(self.WIDTH*self.HEIGHT):
            self.hasMovedFlags[ind] = False

        #for pix in range(0, len(self.pixelBytes)//4, -1):
        for y in reversed(range(0,self.HEIGHT)):
            tx = list(range(0,self.WIDTH))
            shuffle(tx)
            for x in tx:
                pix = self.imgind(x,y)
                doBreak = False
                # whole pixel values, not individual channels

                thisElem = self.elems[pix]

                ## If we have X momentum, prefer moving in the same direction we previously moved.
                ## Otherwise, pick left/right randomly, so there is no bias
                checkLeftFirst = False
                
                # if (thisElem[3] == 0): continue
                if (self.hasMovedFlags[pix] == True or thisElem == AIR or thisElem == ROCK): continue

                if (self.momentum[pix] == -1): 
                    checkLeftFirst = True
                elif (self.momentum[pix] == 1): 
                    checkLeftFirst = False
                else:
                    checkLeftFirst = (random() < 0.5)

                if checkLeftFirst:
                    dirs = [[0,1], [-1,1],[1,1]]
                else:
                    dirs = [[0,1], [1,1],[-1,1]]

                if (thisElem == WATER or thisElem == OIL or thisElem == BLOOD) and (y<self.HEIGHT-1):
                    if (random() >= 0.5):
                        dirs.extend([[-1,0], [1,0]])
                    else:
                        dirs.extend([[0,1], [-1,0]])

                if (self.canMove( thisElem, x, y+1)):
                    ## Ideally, we want to move down first
                    self.move( x, y, x, y+1)
                    continue

                # CHECK IF BLOOD OVER ROCK, THEN ENREDDEN AND REMOVE BLOOD
                if (thisElem == BLOOD ) and (y<self.HEIGHT-1):
                    
                    for xAdd,yAdd in dirs:
                        idx = self.imgind(x+xAdd,y+yAdd)
                        if ((self.elems[idx] == ROCK)or(self.elems[idx] == SAND)) and (self.hasColoredFlags[idx] == False):
                            self.multiplyAndRemove(x,y, x+xAdd,y+yAdd)
                            doBreak = True
                            break

                if doBreak == True: continue
                for xAdd,yAdd in dirs[1:]:
                    if (self.canMove( thisElem, x+xAdd, y+yAdd)):
                            self.move( x, y, x+xAdd, y+yAdd)
                            doBreak=True
                            break
                if doBreak == True: continue
                
                
        imageData = QImage(self.pixelBytes, self.WIDTH, self.HEIGHT, QImage.Format_RGBA8888)
        img = imageData.constBits() # sip.voidptr
        img.setsize(self.pixelBytes.count())
        imgBytes = QByteArray(img.asstring())

        self.activeNode.setPixelData(imgBytes, 0, 0, self.WIDTH, self.HEIGHT)

        self.activeDocument.refreshProjection()

    def putRGBA(self, img: QByteArray, x,y, rgba):
        img.replace(int(self.imgind(x,y)*4), 4, bytearray([rgba[2],rgba[1],rgba[0],rgba[3]]))

    def multiplyAndRemove(self, fromX, fromY, toX, toY):
        # get this/that pixel color
        thisColor = getRGBA(self.pixelBytes,self.imgind(fromX, fromY))
        thatColor = getRGBA(self.pixelBytes,self.imgind(toX, toY))
        # multiply to the second color
        endCol = cmul(thisColor, thatColor)
        # change the color
        self.putRGBA(self.pixelBytes, toX, toY, endCol)
        # set the colored flag
        self.hasColoredFlags[self.imgind(toX, toY)]= True
        # delete this pixel
        self.delPix(fromX, fromY)

    def delPix(self, x,y):
        indx = self.imgind(x,y)
        self.putRGBA(self.pixelBytes, x, y, [255,255,255,255])
        self.elems[indx] = AIR
        self.momentum[indx] = 0
        # self.hasMovedFlags[indx] = True

    def imgind(self, x, y): 
        return int(x + y * self.WIDTH)

    def canMove(self, substance, xTo, yTo):

        if (xTo<0 or xTo>=self.WIDTH or yTo<0 or yTo>=self.HEIGHT): return False
        # if getType(substance) == "INVALID": return False
        otherSubstance = self.elems[self.imgind(xTo,yTo)] # getRGBA(img,self.imgind(xTo,yTo)) ####img[ind(xTo, yTo)]
        # if (substance == FIRE): return (otherSubstance == OIL)
        if (otherSubstance == AIR): return True
        if (substance == SAND and ((otherSubstance == WATER) or (otherSubstance == BLOOD)) and random() < 0.5): return True
        return False

    def move(self, fromX, fromY, toX, toY):
        fromInd = self.imgind(fromX, fromY)
        toInd = self.imgind(toX, toY)

        # self.pixelBytes = QByteArray(Krita.instance().activeDocument().activeNode().pixelData(0, 0, self.WIDTH, self.HEIGHT))

        otherPixel = getRGBA(self.pixelBytes, toInd)
        ##thisElem= getRGBA(self.pixelBytes, fromInd)
        otherElem = self.elems[toInd]

        self.elems[toInd] = self.elems[fromInd]
        self.elems[fromInd] = otherElem

        self.putRGBA(self.pixelBytes, toX,  toY,   getRGBA(self.pixelBytes, fromInd)) 
        self.putRGBA(self.pixelBytes, fromX,fromY, otherPixel)


        self.hasMovedFlags[toInd] = True
        self.hasMovedFlags[fromInd] = True

        self.momentum[fromInd] = 0

        if (toX > fromX): self.momentum[toInd] = 1
        elif (toX < fromX): self.momentum[toInd] = -1
        else: self.momentum[toInd] = 0
