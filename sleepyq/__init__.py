import requests
import inflection

from collections import namedtuple

class APIobject(object):
    def __init__(self, data):
        self.data = data

    def __getattr__(self, name):
        adjusted_name = inflection.camelize(name, False)
        return self.data[adjusted_name]

class Bed(APIobject):
    def __init__(self, data):
        super(Bed, self).__init__(data)
        self.left = None
        self.right = None

class FamilyStatus(APIobject):
    def __init__(self, data):
        super(FamilyStatus, self).__init__(data)
        self.bed = None

        self.left = SideStatus(data['leftSide'])
        self.right = SideStatus(data['rightSide'])

class SideStatus(APIobject):
    def __init__(self, data):
        super(SideStatus, self).__init__(data)
        self.bed = None
        self.sleeper = None

class Sleeper(APIobject):
    def __init__(self, data):
        super(Sleeper, self).__init__(data)
        self.bed = None

class Sleepyq:
    def __init__(self, login, password):
        self._login = login
        self._password = password
        self._session = requests.Session()

    def login(self):
        if '_k' in self._session.params:
            del self._session.params['_k']

        data = {'login': self._login, 'password': self._password}
        r = self._session.put('https://api.sleepiq.sleepnumber.com/rest/login', json=data)
        if r.status_code == 401:
            return False

        self._session.params['_k'] = r.json()['key']

        return True

    def sleepers(self):
        url = 'https://api.sleepiq.sleepnumber.com/rest/sleeper'
        r = self._session.get(url)
        if r.status_code == 401:
            self.login()
            r = self._session.get(url)
            r.raise_for_status()

        sleepers = [Sleeper(sleeper) for sleeper in r.json()['sleepers']]
        return sleepers

    def beds(self):
        url = 'https://api.sleepiq.sleepnumber.com/rest/bed'
        r = self._session.get(url)
        if r.status_code == 401:
            self.login()
            r = self._session.get(url)
            r.raise_for_status()

        beds = [Bed(bed) for bed in r.json()['beds']]
        return beds

    def beds_with_sleeper_status(self):
        beds = self.beds()
        sleepers = self.sleepers()
        family_statuses = self.bed_family_status()

        sleepers_by_id = {sleeper.sleeper_id: sleeper for sleeper in sleepers}
        bed_family_statuses_by_bed_id = {family_status.bed_id: family_status for family_status in family_statuses}

        for bed in beds:
            family_status = bed_family_statuses_by_bed_id[bed.bed_id]

            for side in ['left', 'right']:
                sleeper_key = 'sleeper_' + side + '_id'
                sleeper_id = getattr(bed, sleeper_key)
                sleeper = sleepers_by_id[sleeper_id]

                status = getattr(family_status, side)
                status.sleeper = sleeper

                setattr(bed, side, status)
        return beds

    def bed_family_status(self):
        url = 'https://api.sleepiq.sleepnumber.com/rest/bed/familyStatus'
        r = self._session.get(url)
        if r.status_code == 401:
            self.login()
            r = self._session.get(url)
            r.raise_for_status()

        statuses = [FamilyStatus(status) for status in r.json()['beds']]
        return statuses

    def set_lights(self, bednum, light, setting):
        #
        # light 1-4
        # setting 0=off, 1=on
        #
        url = 'https://api.sleepiq.sleepnumber.com/rest/bed/'+self.beds()[bednum].data['bedId']+'/foundation/outlet'
        data = {'outletId': light, 'setting': setting}
        r = self._session.put(url, json=data)
        if r.status_code == 401:
            self.login()
            r = self._session.put(url, json=data)
            r.raise_for_status()

        return True

    def preset(self, bednum, preset, side, speed):
        #
        # preset 1-6
        ### 1=fav?
        ### 2=read
        ### 3=watch tv
        ### 4=flat
        ### 5=zero g
        ### 6=snore
        # side "R" or "L"
        # Speed 0=fast, 1=slow
        #
        url = 'https://api.sleepiq.sleepnumber.com/rest/bed/'+self.beds()[bednum].data['bedId']+'/foundation/preset'
        data = {'preset':preset,'side':side,'speed':speed}
        r = self._session.put(url, json=data)
        if r.status_code == 401:
            self.login()
            r = self._session.put(url, json=data)
            r.raise_for_status()

        return True

    def set_sleepnumber(self, bednum, side, setting):
        #
        # side "R" or "L"
        # setting 0-100 (increments of 5)
        #
        url = 'https://api.sleepiq.sleepnumber.com/rest/bed/'+self.beds()[bednum].data['bedId']+'/sleepNumber'
        data = {'bed': self.beds()[bednum].data['bedId'], 'side': side, "sleepNumber":setting}
        self._session.params['side']=side
        r = self._session.put(url, json=data)
        if r.status_code == 401:
            self.login()
            r = self._session.put(url, json=data)
            r.raise_for_status()

        del self._session.params['side']

        return True

