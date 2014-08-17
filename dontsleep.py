#!/usr/bin/env python
# -*- coding: utf-8 -*-

#***************************************************************************
#*   Copyright (C) 2014 by Sebastian Schmidt [schro.sb@gmail.com]          *
#*                                                                         *
#*                                                                         *
#*   This program is free software; you can redistribute it and/or modify  *
#*   it under the terms of the GNU General Public License as published by  *
#*   the Free Software Foundation; either version 3 of the License, or     *
#*   (at your option) any later version.                                   *
#*                                                                         *
#*   This program is distributed in the hope that it will be useful,       *
#*   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
#*   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
#*   GNU General Public License for more details.                          *
#*                                                                         *
#*   You should have received a copy of the GNU General Public License     *
#*   along with this program; if not, write to the                         *
#*   Free Software Foundation, Inc.,                                       *
#*   59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.             *
#***************************************************************************

from PyQt4.QtGui import *
from PyQt4.QtCore import *
import sys, os, psutil, subprocess, codecs

def getScriptPath():
    return os.path.dirname(os.path.realpath(sys.argv[0]))

def isScreenSaverEnabled():
    xset = subprocess.Popen("xset dpms q | grep timeout", shell=True,\
                            stdout=subprocess.PIPE)
    timeout = int(xset.stdout.read().split("  ")[2])
    if timeout == 0:
        return False
    else:
        return True

def getProcesses():
    settings = QSettings(QSettings.IniFormat, QSettings.UserScope,
                         "dontsleep", "dontsleep")
    processes = settings.value("processes", []).toStringList()
    return processes

def appendProcess(process):
    settings = QSettings(QSettings.IniFormat, QSettings.UserScope,
                         "dontsleep", "dontsleep")
    processes = settings.value("processes", []).toStringList()
    processes.append(process)
    settings.setValue("processes", processes)

def removeProcess(process):
    settings = QSettings(QSettings.IniFormat, QSettings.UserScope,
                         "dontsleep", "dontsleep")
    processes = settings.value("processes", []).toStringList()
    if process in processes:
        index = processes.indexOf(process)
        processes.removeAt(index)
        settings.setValue("processes", processes)

def getLicenseText():
    with codecs.open(getScriptPath()+"/LICENSE", "r", "Utf8") as license_file:
        license_text = license_file.read()
        license_file.close()
        return license_text

sleep_Icon = getScriptPath() + "/sleep.xpm"
awake_Icon = getScriptPath() + "/awake.xpm"

class TrayIcon(QSystemTrayIcon):
    def __init__(self, parent=None):
        if isScreenSaverEnabled():
            icon = QIcon(sleep_Icon)
        else:
            icon = QIcon(awake_Icon)
        super(TrayIcon, self).__init__(icon, parent)
        
        # overwrite status based on user input
        self.manual_PreventSleep = False
        self.configDialog = None
        self.activated.connect(self._icon_activated)
        
        menu = QMenu()
        showConfigWindowAction = QAction("Toggle Config", menu)
        showConfigWindowAction.triggered.connect(self.toggleConfigWindow)
        aboutAction = QAction("About", menu)
        aboutAction.triggered.connect(self.showAboutDialog)
        aboutQtAction = QAction("About Qt", menu)
        aboutQtAction.triggered.connect(self.showAboutQt)
        exitAction = QAction("Exit", menu)
        exitAction.triggered.connect(self._exitApp)
        
        menu.addAction(showConfigWindowAction)
        menu.addAction(aboutAction)
        menu.addAction(aboutQtAction)
        menu.addAction(exitAction)
        self.setContextMenu(menu)
        self._getTimeout()
        self.timer = QTimer(self)
        self.timer.setInterval(59000)
        self.timer.timeout.connect(self.onTimeout)
        self.timer.start()
    
    def showAboutDialog(self):
        self.aboutDialog = AboutDialog()
        self.aboutDialog.show()
    
    def showAboutQt(self):
        QMessageBox.aboutQt(None)
        
    def onTimeout(self):
        if self.manual_PreventSleep:
            return True
        if self.checkForProcesses():
            self.disableScreenSaver()
        else:
            self.enableScreenSaver()
    
    def checkForProcesses(self):
        processes = getProcesses()
        for proc in psutil.process_iter():
            if proc.name in processes:
                return True
        return False
    
    def _getTimeout(self):
        """
        Save the timeout of the screen saver function
        """
        xset = subprocess.Popen("xset dpms q | grep timeout", shell=True,\
                                stdout=subprocess.PIPE)
        timeout = xset.stdout.read().split("  ")[2]
        # Screen Saver disabled at start - how much timeout?
        if timeout == "0":
            self.initial_timeout = "on"
        else:
            self.initial_timeout = timeout
    
    def _icon_activated(self, reason):
        # Left Click
        if reason == 3:
            self.toggleScreenSaver(manual_overwrite=True)
    
    def _exitApp(self):
        self.enableScreenSaver()
        app = QApplication.instance()
        app.exit()
    
    def closeConfigDialog(self):
        self.configDialog.close()
        self.configDialog = None
    
    def positionConfigDialog(self):
        geo = self.geometry()
        x = geo.x()
        # top panel
        if geo.y() < 10:
            y = geo.y() + geo.height()
        # bottom panel
        else:
            y = geo.y() - self.configDialog.size().height()
        self.configDialog.move(x, y)
        
    def toggleConfigWindow(self):
        if not self.configDialog:
            self.configDialog = DontSleepConfigWindow()
            self.configDialog.show()
            self.positionConfigDialog()
            self.configDialog.closeBtn.clicked.connect(self.closeConfigDialog)
        else:
            self.closeConfigDialog()
            
    def toggleScreenSaver(self, manual_overwrite=False):
        if isScreenSaverEnabled():
            self.disableScreenSaver()
            # 
            if manual_overwrite:
                self.manual_PreventSleep = True
        else:
            self.enableScreenSaver()
            if manual_overwrite:
                self.manual_PreventSleep = False
    
    def enableScreenSaver(self):
        self.setIcon(QIcon(sleep_Icon))
        subprocess.Popen("xset dpms s "+ self.initial_timeout, shell=True)
        # Enable Energy saving features (monitor sleep)
        subprocess.Popen("xset +dpms", shell=True)
    
    def disableScreenSaver(self):
        self.setIcon(QIcon(awake_Icon))
        subprocess.Popen("xset dpms s off", shell=True)
        # Disable Energy saving features (monitor sleep)
        subprocess.Popen("xset -dpms", shell=True)

class DontSleepConfigWindow(QDialog):
    """
    Preferences Window
    """
    def __init__(self, parent=None):
        super(DontSleepConfigWindow, self).__init__(parent)
        self.setWindowTitle("Don't SLEEP - Config")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.applicationList = QListWidget(self)
        addBtn = QPushButton("Add", self)
        addBtn.clicked.connect(self.addToProcesses)
        removeBtn = QPushButton("Remove", self)
        removeBtn.clicked.connect(self.removeFromProcesses)
        self.closeBtn = QPushButton("Close", self)
        
        layout = QVBoxLayout(self)
        layout.addWidget(self.applicationList)
        hlayout = QHBoxLayout()
        hlayout.addWidget(addBtn)
        hlayout.addWidget(removeBtn)
        layout.addLayout(hlayout)
        layout.addWidget(self.closeBtn)
        self.setLayout(layout)
        
        processes = getProcesses()
        self.applicationList.addItems(processes)
    
    def addToProcesses(self):
        new_proc, ok = QInputDialog.getText(self, "New Process", "")
        if ok:
            self.applicationList.addItem(new_proc)
            appendProcess(new_proc)
    
    def removeFromProcesses(self):
        item = self.applicationList.currentItem()
        if item:
            process = item.text()
            flags = QMessageBox.Yes | QMessageBox.No
            result = QMessageBox.question(self, "Delete", 
                                          "Delete "+process+" from the list?",
                                          flags)
            if result == QMessageBox.Yes:
                self.applicationList.takeItem(self.applicationList.row(item))
                removeProcess(process)
    
    def sizeHint(self):
        return QSize(280, 280)
    
class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super(AboutDialog, self).__init__(parent)
        self.setWindowTitle("About")
        tabbar = QTabWidget(self)
        aboutWidget = QTextBrowser()
        aboutWidget.setText("Don't Sleep\n\nPrevent the Screensaver from "+\
                            "starting\n\nCopyright(C) 2014 by Sebastian Schmidt")
        licenseWidget = QTextBrowser()
        licenseWidget.setText(getLicenseText())
        tabbar.addTab(aboutWidget, "About")
        tabbar.addTab(licenseWidget, "License")
        
        layout = QHBoxLayout(self)
        layout.addWidget(tabbar)
        self.setLayout(layout)
        
if __name__ == "__main__":
    Main_App = QApplication(sys.argv)
    Main_App.setQuitOnLastWindowClosed(False)
    Main_App.setApplicationName("Don't SLEEP")
    trayIcon = TrayIcon()
    trayIcon.show()
    sys.exit(Main_App.exec_())
