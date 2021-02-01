try:
  import urequests as requests
except:
  import requests
from CONF import MAIN_URL, UPGRADE_FILES


def upgrade():
    for url in UPGRADE_FILES:
        r = None
        f = url.split('/')[-1]
        print('Download ' + str(f))
        r = requests.get(url= MAIN_URL + url).text
        print(r)
        open(f, 'wb').write(r)
        print('Save ' + str(f))
