# InControl2
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

This custom component adds entities for PepLink routers that are connected to their InControl cloud service.

The following entities will be created for detected routers:
* Signal strength for detected radios (Celluar, Wifi WAN, etc.)
* Device tracker with GPS location
* Overall status of the integration

# Quick and Dirty Instructions
1. Install the InControl2 integration however you see fit (HACS, manul, etc)
2. Restart Home Assistant
3. Within your home assistant, browse to Configuration->Integrations
4. Select "Add Integration" and search for InControl2
5. Note the URL provided as this will be used when adding the Client Application on the InControl2 site
6. In another tab or window login to https://incontrol2.peplink.com
7. Select your username/email in the upper right corner to edit your user
8. Under Client Applications click the button for "New Client"
9. Enter any name for "Application Name"
10. Check "Enabled"
11. Enter any url for "Website"
7. Enter the Redirect URI noted in step 5. This should be something like http://192.168.0.12:8123/api/incontrol2 but will depend on your environment.  See the [internal_url](https://www.home-assistant.io/docs/configuration/basic/#internal_url) configuration for home assistant.
8. Leave Website Restrictions blank
9. Set Token Type to Bearer
10. Select Save
11. Take note of the Client ID and Secret
12. Back within your home assistant, enter the Client ID and Secret in the Integration Setup and select Next
13. Click the link in the next config flow step.  This should take you to the InControl2 site to login if you are not already and then redirect back to your home assistant instance.  You should be greeted with a message "Authentication was successful. You can close this window"
14. Back in the home assistant window where the configuration is occuring, click "Submit" to complete the ConfigFlow. 
15. After some time you should be greeted with a Success message and the option to add the detected device to an area after which you can then click "Finish"
