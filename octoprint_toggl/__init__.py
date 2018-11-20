# coding=utf-8
from __future__ import absolute_import
import octoprint.plugin
import octoprint.events

import os

from toggl.TogglPy import Toggl


toggl = Toggl()

class TogglPlugin(octoprint.plugin.SettingsPlugin,
                  octoprint.plugin.TemplatePlugin,
                  octoprint.plugin.EventHandlerPlugin,
                  octoprint.plugin.WizardPlugin):

    def __init__(self):

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
        toggl.setAPIKey(self._settings.get(["token"]))

        toggl.startTimeEntry(description)


    def stopTimer(self):

        toggl.setAPIKey(self._settings.get(["token"]))
        currentTimer = toggl.currentRunningTimeEntry()
        if currentTimer != None:
            toggl.stopTimeEntry(currentTimer['data']['id'])


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
