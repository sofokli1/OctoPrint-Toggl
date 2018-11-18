# Plugin for OctoPrint that tracks automatically all printing times in Toggl

![TogglTemp](image.png?raw=true) 

## Setup

- Go to [Toggl website](https://toggl.com) and signup for a free basic account.

- After signing up just be ready to grab the API Token at the bottom of your [Toggl Profile settings](https://toggl.com/app/profile)

- Install the plugin via the bundled [Plugin Manager](http://docs.octoprint.org/en/master/bundledplugins/pluginmanager.html)

- After restarting OctoPrint the setup wizard will ask for the Toggl API Token

- Hit finish and you are good to go.

## Configuration

By default the file name and the printer model will be used for the time entries description. This can be customised in the Toggl plugin settings.


This plugin is using [TogglPy](https://github.com/matthewdowney/TogglPy) developed by Matthew Downey
