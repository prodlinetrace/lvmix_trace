#!/usr/bin/env python
import wx.xrc
from wx.lib.delayedresult import startWorker
import os
import time
import datetime
import logging
import sys
from pygtail import Pygtail
import traceback

from traceability import helpers
from traceability import __version__ as version
from traceability.models import __version__ as dbmodel_version
from traceability.prodline import ProdLine
from traceability.util import file_name_with_size

logger = logging.getLogger(__name__.ljust(12)[:12])

class MainWindow(wx.App):
    ID_UPDATE_CTRL_STATUS = wx.NewId()
    ID_UPDATE_LOG = wx.NewId()

    def OnInit(self):
        res = wx.xrc.XmlResource("prodLineTrace.xrc")
        frame = res.LoadFrame(None, 'MainFrame')
        frame.Show()

        self.valueMainStatus = wx.xrc.XRCCTRL(frame, "valueMainStatus")
        self.valueMainConfigFile = wx.xrc.XRCCTRL(frame, "valueMainConfigFile")
        self.valueMainLogFile = wx.xrc.XRCCTRL(frame, "valueMainLogFile")
        self.valueMainVerbosity = wx.xrc.XRCCTRL(frame, "valueMainVerbosity")
        self.valueMainPopups = wx.xrc.XRCCTRL(frame, "valueMainPopups")
        self.valueMainVersion = wx.xrc.XRCCTRL(frame, "valueMainVersion")
        self.valueMainDBModelVersion = wx.xrc.XRCCTRL(frame, "valueMainDBModelVersion")
        self.valueMainDBURI = wx.xrc.XRCCTRL(frame, "valueMainDBURI")
        self.valueMainUptime = wx.xrc.XRCCTRL(frame, "valueMainUptime")
        self.valueMainDBSize = wx.xrc.XRCCTRL(frame, "valueMainDBSize")
        self.valueMainBaseUrl = wx.xrc.XRCCTRL(frame, "valueMainBaseUrl")
        self.valueMainPollSleep = wx.xrc.XRCCTRL(frame, "valueMainPollSleep")
        self.valueMainPollDBSleep = wx.xrc.XRCCTRL(frame, "valueMainPollDBSleep")
        self.valueMainPCReadyResetOnPoll = wx.xrc.XRCCTRL(frame, "valueMainPCReadyResetOnPoll")
        self.valueMainNewerGreaterStatusCheck = wx.xrc.XRCCTRL(frame, "valueMainNewerGreaterStatusCheck")


        self.valueMainControllerCount = wx.xrc.XRCCTRL(frame, "valueMainControllerCount")
        self.valueMainMsgRead = wx.xrc.XRCCTRL(frame, "valueMainMsgRead")
        self.valueMainMsgWrite = wx.xrc.XRCCTRL(frame, "valueMainMsgWrite")
        self.valueMainOperWrite = wx.xrc.XRCCTRL(frame, "valueMainOperWrite")
        self.valueMainDetailsDisplay = wx.xrc.XRCCTRL(frame, "valueMainDetailsDisplay")
        self.valueMainUserRead = wx.xrc.XRCCTRL(frame, "valueMainUserRead")

        self.valueMainDBProdCount = wx.xrc.XRCCTRL(frame, "valueMainDBProdCount")
        self.valueMainDBStationCount = wx.xrc.XRCCTRL(frame, "valueMainDBStationCount")
        self.valueMainDBStatusCount = wx.xrc.XRCCTRL(frame, "valueMainDBStatusCount")
        self.valueMainDBOperationCount = wx.xrc.XRCCTRL(frame, "valueMainDBOperationCount")
        self.valueMainDBOperationTypeCount = wx.xrc.XRCCTRL(frame, "valueMainDBOperationTypeCount")
        self.valueMainDBStatusTypeCount = wx.xrc.XRCCTRL(frame, "valueMainDBStatusTypeCount")
        self.valueMainDBCommentCount = wx.xrc.XRCCTRL(frame, "valueMainDBCommentCount")

        self.operatorActionButton = wx.xrc.XRCCTRL(frame, "actionButton")
        self.valueOperatorUsername = wx.xrc.XRCCTRL(frame, "valueUsername")
        self.valueOperatorPassword = wx.xrc.XRCCTRL(frame, "valuePassword")

        self.valueLogTextArea = wx.xrc.XRCCTRL(frame, "valueLogTextArea")
        textAreaFont = wx.Font(10, wx.MODERN, wx.NORMAL, wx.NORMAL, False, u'Consolas')
        self.valueLogTextArea .SetFont(textAreaFont)
        self.application = ProdLine(sys.argv)
        self._opts = self.application._opts
        self._config = helpers.parse_config(self._opts.config)
#        self.webapp = webapp
        self.dburi = self._config['main']['dburi'][0]
        self.logfile = self._config['main']['logfile'][0]
        self.starttime = datetime.datetime.now()
        self.baseUrl = 'http://localhost:5000/'
        if 'baseurl' in self._config['main']:
            self.baseUrl = self._config['main']['baseurl'][0]
        self.pollSleep = self.pollDbSleep = self.pcReadyFlagOnPoll = 0  # set to zero by default
        if 'poll_sleep' in self._config['main']:
            self.pollSleep = self._config['main']['poll_sleep'][0]
        if 'poll_db_sleep' in self._config['main']:
            self.pollDbSleep = self._config['main']['poll_db_sleep'][0]
        if 'pc_ready_flag_on_poll' in self._config['main']:
            self.pcReadyFlagOnPoll = self._config['main']['pc_ready_flag_on_poll'][0]
        self.newerGreaterStatusCheck = 1
        if 'newer_greater_status_check' in self._config['main']:
            self.newerGreaterStatusCheck = self._config['main']['newer_greater_status_check'][0]


        # bind verbosity choice box with selector function
        self.Bind(wx.EVT_CHOICE, self.OnVerbositySelect, self.valueMainVerbosity)

        # bind popups selectbox with selector function
        self.Bind(wx.EVT_CHOICE, self.OnPopupSelect, self.valueMainPopups)
        self.application.set_popups(True)
        self.application.set_baseurl(self.baseUrl)
        self.application.set_pollsleep(self.pollSleep)
        self.application.set_polldbsleep(self.pollDbSleep)
        self.application.set_pc_ready_flag_on_poll(self.pcReadyFlagOnPoll)
        self.application.set_newer_greater_status_check(self.newerGreaterStatusCheck)
        
        self.logged_operator = None  # enforce operator logout on startup 
        
        return True

    def OnVerbositySelect(self, event):
        level = self.valueMainVerbosity.GetStringSelection()
        logger.info("Changing log level to: {level}".format(level=level))
        logger.root.setLevel(level)
        logging.root.setLevel(level)
        tw.PushStatusText(tw.PushStatusText(str("Changing log level to: {level}".format(level=level))))

    def OnPopupSelect(self, event):
        _popup = self.valueMainPopups.GetStringSelection()
        popup = False
        if _popup == "Yes":
            popup = True
        logger.info("Changing Product Details Popup to: {popup}".format(popup=popup))
        self.application.set_popups(popup)
        tw.PushStatusText(str("Popups set to: {popup}".format(popup=popup)))
        

    def updateLogWindow(self):
        self._mode = self.ID_UPDATE_LOG
        offset_file = "{logfile}.offset".format(logfile=self.logfile)
        if os.path.exists(offset_file) and os.path.isfile(offset_file):
            content = file(offset_file, "r").read()
            if len(content.split()) < 2:  # less then two lines in a offset file - broken - remove
                logger.info("offset file is empty: {offset_file}. Trying to remove it. ".format(offset_file=offset_file))
                time.sleep(1)
                os.remove(offset_file)

        my_tail = Pygtail(self.logfile)
        while True:
            time.sleep(0.3)
            try:
                content = "".join(my_tail.readlines())
                if content:
                    self.valueLogTextArea.write(content)
            except ValueError as e:
                if os.path.exists(offset_file):
                    logger.error("Problem with reading offset file: {offset_file}. Trying to remove it. ".format(offset_file=offset_file))
                    time.sleep(1)
                    os.remove(offset_file)
                    if not os.path.exists(offset_file):
                        logger.info("offset file: {offset_file} removal successful. Restarting update log thread.".format(offset_file=offset_file))
                        self.updateLogWindow()
                    else:
                        logger.fatal("Failed to remove offset file: {offset_file}.".format(offset_file=offset_file))

    def updateOperatorWindow(self):
        self.Bind(wx.EVT_BUTTON, self.OperatorActionButton_Handler, self.operatorActionButton)
        tw.PushStatusText(str("Logged operator: {0}".format(self.logged_operator)))

        while True:
            time.sleep(0.334)
            pass
            """
            #disable remote logout check - not implemented on PLC side
            
            if self.application.stamp_logout_check():
                self.logged_operator = None
                tw.PushStatusText(str("Operator logout on remote request successful.")) 
                self.operatorActionButton.SetLabel("Login")
                self.application.stamp_logout_finished()
            """
            """
            # set operator_login_flag to true if operator is logged in. Otherwise set it to false.
            if self.logged_operator is not None:
                self.application.set_stamp_login_flag(True)
                #self.application.stamp_login(self.logged_operator)
            else:
                self.application.set_stamp_login_flag(False)
                #self.application.set_stamp_login_name("")
            """
            
    def OperatorActionButton_Handler(self, event) :
        btn = event.GetEventObject()
        logger.info("OperatorActionButton_Handler() for: {btn}".format(btn=btn.GetLabelText()))
        
        username = self.valueOperatorUsername.GetValue()
        password = self.valueOperatorPassword.GetValue()
        
        if self.logged_operator is None:
            """
                try to make operator login
            """
            result, message = self.application.stamp_login_attempt(username, password)
            logger.info("{0} - operator login successful. {1}".format(result, message))
            if result is True:
                self.logged_operator = username    
                tw.PushStatusText(str("{0} - operator login successful.".format(self.logged_operator)))
                logger.info("{0} - operator login successful.".format(self.logged_operator))
                self.operatorActionButton.SetLabel("Logout")
                self.valueOperatorUsername.SetEditable(False)
                self.valueOperatorPassword.SetEditable(False)
                self.valueOperatorPassword.SetValue("")  # reset password field
            else:
                tw.PushStatusText(str("{0} - operator login failed. Error: {1}".format(username, message)))
                logger.info("{0} - operator login failed. Error: {1}".format(username, message))
                self.valueOperatorPassword.SetValue("")  # reset password field
        else:
            """
                make operator logout
            """
            self.logged_operator = None
            tw.PushStatusText(str("Operator logout successful.")) 
            self.operatorActionButton.SetLabel("Login")
            self.valueOperatorUsername.SetEditable(True)
            self.valueOperatorPassword.SetEditable(True)
            self.application.stamp_logout_finished()
            logger.info("Operator logout successful.")
            
    def updateControllersStatus(self):
        self._mode = self.ID_UPDATE_CTRL_STATUS
        # push some initial data
        self.valueMainVersion.SetLabelText(version)
        self.valueMainDBModelVersion.SetLabelText(dbmodel_version)
        self.valueMainBaseUrl.SetLabelText(str(self.baseUrl))
        self.valueMainPollSleep.SetLabelText(str(self.pollSleep))
        self.valueMainPollDBSleep.SetLabelText(str(self.pollDbSleep))
        self.valueMainPCReadyResetOnPoll.SetLabelText(str(self.pcReadyFlagOnPoll))
        self.valueMainNewerGreaterStatusCheck.SetLabelText(str(self.newerGreaterStatusCheck))

        while True:
            self.valueMainLogFile.SetLabelText(file_name_with_size(self.logfile))
            self.valueMainConfigFile.SetLabelText(file_name_with_size(self._opts.config))
            self.valueMainDBURI.SetLabelText(file_name_with_size(self.dburi))
            self.valueMainStatus.SetLabelText(str(self.application.get_status()))
            self.valueMainUptime.SetLabelText(str(datetime.datetime.now() - self.starttime))

            # message statistics
            self.valueMainControllerCount.SetLabelText(str(len(self.application.plcs)))
            self.valueMainMsgRead.SetLabelText(str(self.application.get_counter_status_message_read()))
            self.valueMainMsgWrite.SetLabelText(str(self.application.get_counter_status_message_write()))
            self.valueMainOperWrite.SetLabelText(str(self.application.get_counter_saved_operations()))
            self.valueMainDetailsDisplay.SetLabelText(str(self.application.get_counter_product_details_display()))
            self.valueMainUserRead.SetLabelText(str(self.application.get_counter_operator_status_read()))

            # update block statistics
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
            logging.critical("Exception: {exc}".format(exc=e))
            logging.critical("Traceback: {tb}".format(tb=traceback.format_exc()))

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

        logger.critical("GUI Thread failed: ID: {id} JID: {jid}".format(id=repr(str(delayedResult)), jid=delayedResult.getJobID()))
        # log real exception
        try:
            result = delayedResult.get()
            logger.critical("Unexpected result. One of the threads just returned with result: {result}".format(result=result))
        except Exception, e:
            logger.critical("GUI Thread failed with following exception: {exc}".format(exc=e))
            logger.critical("Traceback: {tb}".format(tb=traceback.format_exc()))
            #logger.critical("Traceback (stack): {tb}".format(tb=traceback.print_stack()))

    def OnClose(self):
        self.Destroy()
        self.Close(True)

if __name__ == "__main__":
    _opts, _args = helpers.parse_args()
    app = MainWindow(redirect=True, filename=os.devnull)

    # update status bar
    tw = app.GetTopWindow()
    tw.PushStatusText('Starting...')

    # start the threads
    startWorker(app._ResultNotifier, app.updateLogWindow)
    startWorker(app._ResultNotifier, app.updateControllersStatus)
    startWorker(app._ResultNotifier, app.mainThread)
    startWorker(app._ResultNotifier, app.updateOperatorWindow)

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
                logger.error("Thread: {thread} could not be terminated. Exception: {exc} ".format(thread=str(thread.getName()), exc=e.__str__()))
                logger.error("Traceback: {tb}".format(tb=traceback.format_exc()))

    #logger.info("final thread active count {count}".format(count=threading.active_count()))
