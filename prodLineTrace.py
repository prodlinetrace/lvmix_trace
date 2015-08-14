#!/usr/bin/env python
import wx
from wx import xrc
from wx.lib.delayedresult import startWorker
import time
import datetime
import logging
import sys
import tailer
import traceback

from plc import helpers
from plc import __version__ as version
from plc.db_models import __version__ as dbmodel_version
from plc.prodline import ProdLine
from plc.util import file_name_with_size

logger = logging.getLogger(__name__)


class MainWindow(wx.App):
    ID_UPDATE_CTRL_STATUS = wx.NewId()
    ID_UPDATE_LOG = wx.NewId()

    def OnInit(self):
        res = xrc.XmlResource("prodLineTrace.xrc")
        frame = res.LoadFrame(None, 'MainFrame')
        frame.Show()

        self.valueMainStatus = xrc.XRCCTRL(frame, "valueMainStatus")
        self.valueMainConfigFile = xrc.XRCCTRL(frame, "valueMainConfigFile")
        self.valueMainLogFile = xrc.XRCCTRL(frame, "valueMainLogFile")
        self.valueMainErrorLogFile = xrc.XRCCTRL(frame, "valueMainErrorLogFile")
        self.valueMainVerbosity = xrc.XRCCTRL(frame, "valueMainVerbosity")
        self.valueMainPopups = xrc.XRCCTRL(frame, "valueMainPopups")
        self.valueMainVersion = xrc.XRCCTRL(frame, "valueMainVersion")
        self.valueMainDBModelVersion = xrc.XRCCTRL(frame, "valueMainDBModelVersion")
        self.valueMainDBFile = xrc.XRCCTRL(frame, "valueMainDBFile")
        self.valueMainUptime = xrc.XRCCTRL(frame, "valueMainUptime")
        self.valueMainDBSize = xrc.XRCCTRL(frame, "valueMainDBSize")
        self.valueMainBaseUrl = xrc.XRCCTRL(frame, "valueMainBaseUrl")

        self.valueMainControllerCount = xrc.XRCCTRL(frame, "valueMainControllerCount")
        self.valueMainMsgRead = xrc.XRCCTRL(frame, "valueMainMsgRead")
        self.valueMainMsgWrite = xrc.XRCCTRL(frame, "valueMainMsgWrite")
        self.valueMainOperWrite = xrc.XRCCTRL(frame, "valueMainOperWrite")
        self.valueMainDetailsDisplay = xrc.XRCCTRL(frame, "valueMainDetailsDisplay")

        self.valueMainDBProdCount = xrc.XRCCTRL(frame, "valueMainDBProdCount")
        self.valueMainDBStationCount = xrc.XRCCTRL(frame, "valueMainDBStationCount")
        self.valueMainDBStatusCount = xrc.XRCCTRL(frame, "valueMainDBStatusCount")
        self.valueMainDBOperationCount = xrc.XRCCTRL(frame, "valueMainDBOperationCount")
        self.valueMainDBOperationTypeCount = xrc.XRCCTRL(frame, "valueMainDBOperationTypeCount")
        self.valueMainDBStatusTypeCount = xrc.XRCCTRL(frame, "valueMainDBStatusTypeCount")
        self.valueMainDBCommentCount = xrc.XRCCTRL(frame, "valueMainDBCommentCount")

        self.valueLogTextArea = xrc.XRCCTRL(frame, "valueLogTextArea")
        self.valueErrorLogTextArea = xrc.XRCCTRL(frame, "valueErrorLogTextArea")

        self.application = ProdLine(sys.argv)
        self._opts = self.application._opts
        self._config = helpers.parse_config(self._opts.config)
#        self.webapp = webapp
        self.dbfile = self._config['main']['dbfile'][0]
        self.logfile = self._config['main']['logfile'][0]
        self.errlog = helpers.parse_config(_opts.config)['main']['errorlog'][0]
        self.starttime = datetime.datetime.now()
        self.baseUrl = self._config['main']['baseurl'][0]

        # bind verbosity choice box with selector function
        self.Bind(wx.EVT_CHOICE, self.OnVerbositySelect, self.valueMainVerbosity)

        # bind popups selectbox with selector function
        self.Bind(wx.EVT_CHOICE, self.OnPopupSelect, self.valueMainPopups)
        self.application.set_baseurl(self.baseUrl)
        self.application.set_popups(True)

        return True

    def OnVerbositySelect(self, event):
        level = self.valueMainVerbosity.GetStringSelection()
        logger.info("Changing log level to: %s" % level)
        logger.root.setLevel(level)
        logging.root.setLevel(level)

    def OnPopupSelect(self, event):
        _popup = self.valueMainPopups.GetStringSelection()
        popup = False
        if _popup == "Yes":
            popup = True
        logger.info("Changing Product Details Popup to: %r" % popup)
        self.application.set_popups(popup)

    def updateLogWindow(self):
        self._mode = self.ID_UPDATE_LOG
        for line in tailer.follow(open(self.logfile)):
            self.valueLogTextArea.write(line + "\n")

    def updateErrorLogWindow(self):
        for line in tailer.follow(open(self.errlog)):
            self.valueErrorLogTextArea.write(line + "\n")

    def updateControllersStatus(self):
        self._mode = self.ID_UPDATE_CTRL_STATUS
        # push some initial data
        self.valueMainVersion.SetLabelText(version)
        self.valueMainDBModelVersion.SetLabelText(dbmodel_version)
        self.valueMainBaseUrl.SetLabelText(str(self.baseUrl))

        while True:
            self.valueMainLogFile.SetLabelText(file_name_with_size(self.logfile))
            self.valueMainErrorLogFile.SetLabelText(file_name_with_size(self.errlog))
            self.valueMainConfigFile.SetLabelText(file_name_with_size(self._opts.config))
            self.valueMainDBFile.SetLabelText(file_name_with_size(self.dbfile))

            self.valueMainStatus.SetLabelText(str(self.application.get_status()))
            self.valueMainUptime.SetLabelText(str(datetime.datetime.now() - self.starttime))

            # message statistics
            self.valueMainControllerCount.SetLabelText(str(len(self.application.controllers)))
            self.valueMainMsgRead.SetLabelText(str(self.application.get_counter_status_message_read()))
            self.valueMainMsgWrite.SetLabelText(str(self.application.get_counter_status_message_write()))
            self.valueMainOperWrite.SetLabelText(str(self.application.get_counter_saved_operations()))
            self.valueMainDetailsDisplay.SetLabelText(str(self.application.get_counter_product_details_display()))

            # update db statistics
            self.valueMainDBProdCount.SetLabelText(str(self.application.get_product_count()))
            self.valueMainDBStationCount.SetLabelText(str(self.application.get_station_count()))
            self.valueMainDBStatusCount.SetLabelText(str(self.application.get_status_count()))
            self.valueMainDBOperationCount.SetLabelText(str(self.application.get_opertation_count()))
            self.valueMainDBOperationTypeCount.SetLabelText(str(self.application.get_operation_type_count()))
            self.valueMainDBStatusTypeCount.SetLabelText(str(self.application.get_status_type_count()))
            self.valueMainDBCommentCount.SetLabelText(str(self.application.get_comment_count()))

            time.sleep(0.31234)

    def mainThread(self):
        """
        This is main application thread.
        """
        try:
            self.application.main()
        except Exception, e:
            logger.critical("exception %r" % e)
            tb = traceback.format_exc()
            logger.critical("Traceback: %s" % tb)

    def makeControllerBox(self, name, adress):
        pnl = wx.Panel(self)
        box = {}
        box['box'] = wx.StaticBox(pnl, label=name, pos=(5, 5), size=(240, 170))
        box['addressName'] = wx.StaticText(pnl, label='Address', pos=(15, 95))
        box['addressValue'] = wx.StaticText(pnl, label='Value', pos=(15, 195))
        box['portName'] = wx.StaticText(pnl, label='Port', pos=(35, 95))
        box['portValue'] = wx.StaticText(pnl, label='Value', pos=(35, 195))
        box['statusName'] = wx.StaticText(pnl, label='Status', pos=(55, 95))
        box['statusValue'] = wx.StaticText(pnl, label='Value', pos=(55, 195))

    def _ResultNotifier(self, delayedResult):
        """
        Receives the return from the result of the worker thread and
        notifies the interested party with the result.
        @param delayedResult:  value from worker thread
        """

        logger.critical("GUI Thread failed: ID: %r JID: %r" % (repr(str(delayedResult)), delayedResult.getJobID()))
        # log real exception
        try:
            e = delayedResult.get()
            logger.critical("exception %r" % e)
        except Exception, e:
            tb = traceback.extract_stack()
            logger.critical( "Traceback: %r" % tb)
            logger.critical("GUI Thread failed with following exception: %r" % e.__str__())


    def OnClose(self):
        self.Destroy()
        self.Close(True)

if __name__ == "__main__":
    _opts, _args = helpers.parse_args()
    errlog = helpers.parse_config(_opts.config)['main']['errorlog'][0]
    app = MainWindow(redirect=True, filename=errlog)

    # update status bar
    tw = app.GetTopWindow()
    tw.PushStatusText('starting')

    # start the threads
    startWorker(app._ResultNotifier, app.updateLogWindow)
    startWorker(app._ResultNotifier, app.updateErrorLogWindow)
    startWorker(app._ResultNotifier, app.updateControllersStatus)
    startWorker(app._ResultNotifier, app.mainThread)

    # start main loop
    app.MainLoop()

    # kill all remaining threads
    import threading

    for thread in threading.enumerate():
        if thread.isAlive():
            try:
                thread._Thread__stop()
                if thread.getName() != 'MainThread':
                    thread.join()
            except Exception, e:
                logger.error(str(thread.getName()) + ' could not be terminated ' + e.__str__())
    #logger.info("final thread active count %r"% threading.active_count())

