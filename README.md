# canteen_calendar



## Installation

### Install the wordpress plugin
``` zip custom-event-exporter.php

Install plugin

This will allow events exported to be viewed here. Lists 50 events starting from now
so that will need to be modified for the calendar I would think

https://cedarmountaincanteen.com/wp-json/custom/v1/custom-event-exporter

### Script installation
```
python -m venv ./venv
source venv/Scripts/activate
pip install -r requirements.txt
python main.py
```
This generates a canteenmonthlyposter.jpg in 1080x1920 format, suitable for a TV in portrait mode.

Will probably need to tweak that since TVs tend to overscan, ie cut off edges.