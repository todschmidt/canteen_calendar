# canteen_calendar



## Installation

### Install the wordpress plugin
``` zip custom-event-exporter.php ```

Install plugin in wordpress admin panel

This will allow events to be exported and viewed at this url:
https://cedarmountaincanteen.com/wp-json/custom/v1/custom-event-exporter

### Script installation
Install latest python version from here: https://www.python.org/downloads/
Install latest git version from here: https://git-scm.com/downloads

```
git clone https://github.com/tschmidty69/canteen_calendar.git
cd canteen_calendar
python -m venv ./venv
source venv/Scripts/activate
pip install -r requirements.txt
# To run the script
python main.py
```

### Generating the image

Running the script will then just be a case of running these commands

1. Start power shell. Normally Start Menu -> Powershell but I am not familiar with Windows 11. I might have pinned the icon to your taskbar.
2. ```cd canteen_calendar```
3. ```git pull``` # just to make sure you have the latest version
4. ```python main.py``` # This will automatically generate the file canteenmonthlyposter.jpg and open an image viewer to preview it.


This generates a canteenmonthlyposter.jpg in 1080x1920 format, suitable for a TV in portrait mode.

Will probably need to tweak that since TVs tend to overscan, ie cut off edges.