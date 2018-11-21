# coding=utf-8
from __future__ import absolute_import
import octoprint.plugin
import octoprint.events

import json
import math
import sys
import time
from base64 import b64encode
from datetime import datetime

# for making requests
# backward compatibility with python2
cafile = None
if sys.version[0] == "2":
    from urllib import urlencode
    from urllib2 import urlopen, Request
else:
    from urllib.parse import urlencode
    from urllib.request import urlopen, Request
    try:
        import certifi
        cafile = certifi.where()
    except ImportError:
        pass

# --------------------------------------------
# Class containing the endpoint URLs for Toggl
# --------------------------------------------
class Endpoints():
    WORKSPACES = "https://www.toggl.com/api/v8/workspaces"
    CLIENTS = "https://www.toggl.com/api/v8/clients"
    PROJECTS = "https://www.toggl.com/api/v8/projects"
    TASKS = "https://www.toggl.com/api/v8/tasks"
    REPORT_WEEKLY = "https://toggl.com/reports/api/v2/weekly"
    REPORT_DETAILED = "https://toggl.com/reports/api/v2/details"
    REPORT_SUMMARY = "https://toggl.com/reports/api/v2/summary"
    START_TIME = "https://www.toggl.com/api/v8/time_entries/start"
    TIME_ENTRIES = "https://www.toggl.com/api/v8/time_entries"
    CURRENT_RUNNING_TIME = "https://www.toggl.com/api/v8/time_entries/current"

    @staticmethod
    def STOP_TIME(pid):
        return "https://www.toggl.com/api/v8/time_entries/" + str(pid) + "/stop"


# ------------------------------------------------------
# Class containing the necessities for Toggl interaction
# ------------------------------------------------------
class Toggl():
    # template of headers for our request
    headers = {
        "Authorization": "",
        "Content-Type": "application/json",
        "Accept": "*/*",
        "User-Agent": "python/urllib",
    }

    # default API user agent value
    user_agent = "OctoPrint-Toggl"

    # ------------------------------------------------------------
    # Auxiliary methods
    # ------------------------------------------------------------

    def decodeJSON(self, jsonString):
        return json.JSONDecoder().decode(jsonString)

    # ------------------------------------------------------------
    # Methods that modify the headers to control our HTTP requests
    # ------------------------------------------------------------
    def setAPIKey(self, APIKey):
        '''set the API key in the request header'''
        # craft the Authorization
        authHeader = APIKey + ":" + "api_token"
        authHeader = "Basic " + b64encode(authHeader.encode()).decode('ascii').rstrip()

        # add it into the header
        self.headers['Authorization'] = authHeader

    def setAuthCredentials(self, email, password):
        authHeader = '{0}:{1}'.format(email, password)
        authHeader = "Basic " + b64encode(authHeader.encode()).decode('ascii').rstrip()

        # add it into the header
        self.headers['Authorization'] = authHeader

    def setUserAgent(self, agent):
        '''set the User-Agent setting, by default it's set to TogglPy'''
        self.user_agent = agent

    # -----------------------------------------------------
    # Methods for directly requesting data from an endpoint
    # -----------------------------------------------------

    def requestRaw(self, endpoint, parameters=None):
        '''make a request to the toggle api at a certain endpoint and return the RAW page data (usually JSON)'''
        if parameters is None:
            return urlopen(Request(endpoint, headers=self.headers), cafile=cafile).read()
        else:
            if 'user_agent' not in parameters:
                parameters.update({'user_agent': self.user_agent})  # add our class-level user agent in there
            # encode all of our data for a get request & modify the URL
            endpoint = endpoint + "?" + urlencode(parameters)
            # make request and read the response
            return urlopen(Request(endpoint, headers=self.headers), cafile=cafile).read()

    def request(self, endpoint, parameters=None):
        '''make a request to the toggle api at a certain endpoint and return the page data as a parsed JSON dict'''
        return json.loads(self.requestRaw(endpoint, parameters).decode('utf-8'))

    def postRequest(self, endpoint, parameters=None):
        '''make a POST request to the toggle api at a certain endpoint and return the RAW page data (usually JSON)'''
        if parameters is None:
            return urlopen(Request(endpoint, headers=self.headers), cafile=cafile).read().decode('utf-8')
        else:
            data = json.JSONEncoder().encode(parameters)
            binary_data = data.encode('utf-8')
            # make request and read the response
            return urlopen(
                Request(endpoint, data=binary_data, headers=self.headers), cafile=cafile
            ).read().decode('utf-8')

    # ---------------------------------
    # Methods for managing Time Entries
    # ---------------------------------

    def startTimeEntry(self, description, pid=None, tid=None):
        '''starts a new Time Entry'''

        data = {
            "time_entry": {
                "created_with": self.user_agent,
                "description": description
            }
        }
        if pid:
            data["time_entry"]["pid"] = pid

        if tid:
            data["time_entry"]["tid"] = tid

        response = self.postRequest(Endpoints.START_TIME, parameters=data)
        return self.decodeJSON(response)

    def currentRunningTimeEntry(self):
        '''Gets the Current Time Entry'''
        response = self.postRequest(Endpoints.CURRENT_RUNNING_TIME)
        return self.decodeJSON(response)

    def stopTimeEntry(self, entryid):
        '''Stop the time entry'''
        response = self.postRequest(Endpoints.STOP_TIME(entryid))
        return self.decodeJSON(response)

    def createTimeEntry(self, hourduration, description=None, projectid=None, projectname=None,
                        taskid=None, clientname=None, year=None, month=None, day=None, hour=None):
        """
        Creating a custom time entry, minimum must is hour duration and project param
        :param hourduration:
        :param description: Sets a descripton for the newly created time entry
        :param projectid: Not required if projectname given
        :param projectname: Not required if projectid was given
        :param taskid: Adds a task to the time entry (Requirement: Toggl Starter or higher)
        :param clientname: Can speed up project query process
        :param year: Taken from now() if not provided
        :param month: Taken from now() if not provided
        :param day: Taken from now() if not provided
        :param hour: Taken from now() if not provided
        :return: response object from post call
        """
        data = {
            "time_entry": {}
        }

        if not projectid:
            if projectname and clientname:
                projectid = (self.getClientProject(clientname, projectname))['data']['id']
            elif projectname:
                projectid = (self.searchClientProject(projectname))['data']['id']
            else:
                print('Too many missing parameters for query')
                exit(1)

        if description:
            data['time_entry']['description'] = description

        if taskid:
            data['time_entry']['tid'] = taskid

        year = datetime.now().year if not year else year
        month = datetime.now().month if not month else month
        day = datetime.now().day if not day else day
        hour = datetime.now().hour if not hour else hour

        timestruct = datetime(year, month, day, hour - 2).isoformat() + '.000Z'
        data['time_entry']['start'] = timestruct
        data['time_entry']['duration'] = hourduration * 3600
        data['time_entry']['pid'] = projectid
        data['time_entry']['created_with'] = 'NAME'

        response = self.postRequest(Endpoints.TIME_ENTRIES, parameters=data)
        return self.decodeJSON(response)

    def putTimeEntry(self, parameters):
        if 'id' not in parameters:
            raise Exception("An id must be provided in order to put a time entry")
        id = parameters['id']
        if type(id) is not int:
            raise Exception("Invalid id %s provided " % (id))
        endpoint = Endpoints.TIME_ENTRIES + "/" + str(id)  # encode all of our data for a put request & modify the URL
        data = json.JSONEncoder().encode({'time_entry': parameters})
        request = Request(endpoint, data=data, headers=self.headers)
        request.get_method = lambda: "PUT"

        return json.loads(urlopen(request).read())








class TogglPlugin(octoprint.plugin.SettingsPlugin,
                  octoprint.plugin.TemplatePlugin,
                  octoprint.plugin.EventHandlerPlugin,
                  octoprint.plugin.WizardPlugin):

    def __init__(self):
        self.toggl = Toggl()
        self.firmware = ""


    ##~~ WizardPlugin mixin

    def is_wizard_required(self):
        return self._settings.get(["token"]) is ""

    def get_wizard_version(self):
        return 1


    ##~~ SettingsPlugin mixin

    def get_settings_defaults(self):

        return dict(
            token="",
            show_printer_model=True,
            show_printer_firmware=False,
        )


    ##~~ TemplatePlugin mixin

    def get_template_configs(self):

        return [
            dict(type="settings", custom_bindings=False),
            dict(type="wizard", custom_bindings=False)
        ]


    ##~~ EventHandlerPlugin mixin

    def on_event(self, event, payload, **kwargs):

        title = description = None

        if event == octoprint.events.Events.PRINT_STARTED or \
           event == octoprint.events.Events.PRINT_RESUMED:

            name = payload["name"]
            description = "File: {name}".format(name=name)
            if self._settings.get(["show_printer_model"]) is True:
                description += "\nPrinter Model: {printerModel}".format(printerModel=self._printer_profile_manager.get_default()["model"])
            if self._settings.get(["show_printer_firmware"]) is True:
                description += "\nFirmaware: {firmware}".format(firmware=self.firmware)

            self.startTimer(description)

        elif event == octoprint.events.Events.PRINT_DONE or \
             event == octoprint.events.Events.PRINT_PAUSED or \
             event == octoprint.events.Events.PRINT_FAILED:

            self.stopTimer()

        elif event == octoprint.events.Events.FIRMWARE_DATA:

            self.firmware = payload["name"]


    ##~~ Toggl API

    def startTimer(self, description):

        #Consecutive time entries with same description will be grouped in toggl UI automatically
        self.toggl.setAPIKey(self._settings.get(["token"]))

        self.toggl.startTimeEntry(description)


    def stopTimer(self):

        self.toggl.setAPIKey(self._settings.get(["token"]))
        currentTimer = self.toggl.currentRunningTimeEntry()
        if currentTimer != None:
            self.toggl.stopTimeEntry(currentTimer['data']['id'])


    ##~~ Softwareupdate hook

    def get_update_information(self):
        # Define the configuration for your plugin to use with the Software Update
        # Plugin here. See https://github.com/foosel/OctoPrint/wiki/Plugin:-Software-Update
        # for details.
        return dict(
            toggl=dict(
                displayName="Toggl Plugin",
                displayVersion=self._plugin_version,

                # version check: github repository
                type="github_release",
                user="sofokli1",
                repo="OctoPrint-Toggl",
                current=self._plugin_version,

                # update method: pip
                pip="https://github.com/sofokli1/OctoPrint-Toggl/archive/{target_version}.zip"
            )
        )


__plugin_name__ = "Toggl"

def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = TogglPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
    }
