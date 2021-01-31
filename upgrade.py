import urequests
from CONF import MAIN_URL, UPGRADE_FILES

def upgrade():
    for url in UPGRADE_FILES:
        r = urequests.get(url= MAIN_URL + url).text

        print(url.split('/')[-1])

        open(url.split('/')[-1], 'wb').write(r.content)
