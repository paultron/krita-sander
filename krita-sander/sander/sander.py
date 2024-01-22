import sys
import os
import json


from urllib.request import urlopen, Request
from pathlib import Path
from random import randint, random, shuffle

from krita import * # Krita, DockWidget

from PyQt5.QtCore import QFile, QByteArray
from PyQt5.QtWidgets import QDockWidget, QFileDialog, QWidget, QPushButton, QVBoxLayout
from PyQt5.QtGui import QIcon, QImage
from PyQt5.uic import loadUi

DOCKER_TITLE = 'Sander'


AIR =   [255, 255, 255, 255]
SAND =  [255, 255, 0,   255]
WATER = [0,   0,   255, 255]
OIL =   [64,  64,   64, 255]
ROCK =  [128, 128, 128, 255]

# WIDTH = 0
# HEIGHT = 0


# self.pixelBytes = QByteArray([])

def getType(rgba):
    match rgba:
        case [255,255,255,255]: 
            return "AIR"
        case [255,255,0,255]: 
            return "SAND"
        case [0,0,255,255]: 
            return "WATER"
        case [128,128,128,255]: 
            return "ROCK"
        case _: 
            return "INVALID"
        


def getRGBA(img: QByteArray, indx):
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

        buttonPass = QPushButton("Read", mainWidget)
        buttonPass.clicked.connect(self.readLayer)

        mainWidget.setLayout(QVBoxLayout())
        mainWidget.layout().addWidget(buttonPass)

        buttonAdv = QPushButton("Adv", mainWidget)
        buttonAdv.clicked.connect(self.advance)

        #mainWidget.setLayout(QVBoxLayout())
        mainWidget.layout().addWidget(buttonAdv)


        self.setWidget(mainWidget)

    def canvasChanged(self, canvas):
        pass

    def setup(self):
        pass

    def readLayer(self):
        self.activeDocument = Krita.instance().activeDocument()
        self.activeNode = self.activeDocument.activeNode()
        self.WIDTH = self.activeDocument.width()
        self.HEIGHT = self.activeDocument.height()
        self.pixelBytes = QByteArray(self.activeNode.pixelData(0, 0, self.WIDTH, self.HEIGHT))
        self.momentum = [0]*self.WIDTH*self.HEIGHT
        self.hasMovedFlags = [False]*self.WIDTH*self.HEIGHT

    def advance(self):
        for ind in range(len(self.pixelBytes)//4):
            self.hasMovedFlags[ind] = False

        #for pix in range(0, len(self.pixelBytes)//4, -1):
        for y in reversed(range(0,self.HEIGHT)):
            tx = list(range(0,self.WIDTH))
            shuffle(tx)
            for x in tx:
                if self.hasMovedFlags[self.imgind(x,y)]: continue

                pix = self.imgind(x,y)
                # whole pixel values, not individuals
                x = pix % self.WIDTH
                y = int(pix / self.WIDTH)

                #x = pix/4 % WIDTH
                #y = int(pix/4 / WIDTH)

                thisPixel = getRGBA(self.pixelBytes, pix)
                ## print(getType(thisPixel))
                if (thisPixel[3] == 0): continue
                if (thisPixel == AIR or thisPixel == ROCK): continue

                if (self.canMove(self.pixelBytes, thisPixel, x, y+1)):
                    print("CAN MOVE:", getType(thisPixel))
                    ## Ideally, we want to move down
                    self.move(self.pixelBytes, x, y, x, y+1)
                
                    ## If we have momentum, prefer moving in the same direction we previously moved.
                ## Otherwise, pick left/right randomly, so there is no bias
                checkLeftFirst = False

                if (self.momentum[pix] == -1): 
                    checkLeftFirst = True
                elif (self.momentum[pix] == 1): 
                    checkLeftFirst = False
                else:
                    checkLeftFirst = (random() < 0.5)
                

                if (checkLeftFirst):
                    if (self.canMove(self.pixelBytes, thisPixel, x-1, y+1)):
                    ##
                    #Next, try to move down+left
                        self.move(self.pixelBytes, x, y, x-1, y+1)
                    
                    elif (self.canMove(self.pixelBytes, thisPixel, x+1, y+1)):
                        ## Next, try to move down+right
                        self.move(self.pixelBytes, x, y, x+1, y+1)
                    
                else:
                    if (self.canMove(self.pixelBytes, thisPixel, x+1, y+1)):
                        ## Next, try to move down+right
                        self.move(self.pixelBytes, x, y, x+1, y+1)
                    
                    elif (self.canMove(self.pixelBytes, thisPixel, x-1, y+1)):
                        ## Next, try to move down+left
                        self.move(self.pixelBytes, x, y, x-1, y+1)
                    
                
                
                if (thisPixel == WATER or thisPixel == OIL) and (y<self.HEIGHT-1): # and (getRGBA(self.pixelBytes, self.imgind(x,y+1)) == thisPixel)):
                    ## If we're above a layer of water, spread out to left and right
                    if (checkLeftFirst): 
                        if (self.canMove(self.pixelBytes, thisPixel, x-1, y)):
                            ##Next, try to move left
                            self.move(self.pixelBytes, x, y, x-1, y)
                        elif (self.canMove(self.pixelBytes, thisPixel, x+1, y)): 
                            ##Next, try to move right
                            self.move(self.pixelBytes, x, y, x+1, y)
                    else: 
                        if (self.canMove(self.pixelBytes, thisPixel, x+1, y)): 
                            ##Next, try to move right
                            self.move(self.pixelBytes, x, y, x+1, y)
                        elif (self.canMove(self.pixelBytes, thisPixel, x-1, y)): 
                            ## Next, try to move left
                            self.move(self.pixelBytes, x, y, x-1, y)

        imageData = QImage(self.pixelBytes, self.WIDTH, self.HEIGHT, QImage.Format_RGBA8888)
        img = imageData.constBits() # sip.voidptr
        img.setsize(self.pixelBytes.count())
        imgBytes = QByteArray(img.asstring())

        # print("og img bytes: " + str(imgBytes))
        # print(pixelBytes == imgBytes)

        self.activeNode.setPixelData(imgBytes, 0, 0, self.WIDTH, self.HEIGHT)

        self.activeDocument.refreshProjection()

    def putRGBA(self, img: QByteArray, x,y, rgba):
        img.replace(int(self.imgind(x,y)*4), 4, bytearray([rgba[2],rgba[1],rgba[0],rgba[3]]))



    def imgind(self, x, y): 
        return int(x + y*self.WIDTH)

    def canMove(self, img: QByteArray, substance, xTo, yTo):
        if (xTo<0 or xTo>=self.WIDTH or yTo<0 or yTo>=self.HEIGHT): return False
        if getType(substance) == "INVALID": return False
        otherSubstance = getRGBA(img,self.imgind(xTo,yTo)) ####img[ind(xTo, yTo)]
        # if (substance == FIRE): return (otherSubstance == OIL)
        if (otherSubstance == AIR): return True
        if (substance == SAND and otherSubstance == WATER and random() < 0.5): return True
        return False

    def move(self, img, fromX, fromY, toX, toY):
        fromInd = self.imgind(fromX, fromY)
        toInd = self.imgind(toX, toY)

        otherSubstance = getRGBA(img, toInd)

        self.putRGBA(img,toX,toY,getRGBA(img, fromInd))  # getRGBA(img,)
        # img[toInd] = img[fromInd]
        self.putRGBA(img,fromX,fromY,otherSubstance)
        # img[fromInd] = otherSubstance

        self.hasMovedFlags[toInd] = True
        self.hasMovedFlags[fromInd] = True

        self.momentum[fromInd] = 0

        if (toX > fromX): self.momentum[toInd] = 1
        elif (toX < fromX): self.momentum[toInd] = -1
        else: self.momentum[toInd] = 0

    def testPass(self):
        self.readLayer()
        self.advance()