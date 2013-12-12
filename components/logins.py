from fog_lib import FogRequester, obtain_logins

import logging
import base64


class LoginsRequester(FogRequester):
    """Set logins data on fog server"""
    def _handler(self, text):
        """Process data from fog server and returns hostname"""
        return text

    def _user(self, user):
        return base64.b64encode("x\\" + user)

    def _data(self, date):
        return base64.b64encode(str(date))

    def _set_login_data(self, login, last_logged_date):
            params = dict(service="usertracking.report",
                          user=self._user(login["user"]),
                          date=self._data(login["date"]))

            if login["action"] == "open":
                params["action"] = base64.b64encode("login")

            text = self.get_data(**params)

            if text == self.FOG_OK and login["date"] > last_logged_date:
                save_last_logged(login)
            print text

    def set_logins_data(self, logins, last_logged_date):
        "Returns hostname saved on fog server"

        for login in logins:
            self._set_login_data(login, last_logged_date)

        return True


def save_last_logged(login):
    date = login["date"]
    with open("/var/lib/fog_client_linux_last_log", "w") as file:
        file.write(str(date))


def load_last_logged():
    import datetime
    try:
        with open("/var/lib/fog_client_linux_last_log", "r") as file:
            date_string = file.read()
            return datetime.datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S")
    except:
        return datetime.datetime.min


def logins_to_insert(logins, last_logged_date):
    return [login for login in logins
            if login["date"] > last_logged_date]


def client_logins(fog_host, mac):
    """Main function for this module"""

    last_logged_date = load_last_logged()

    logins_logouts = obtain_logins()
    logins = logins_to_insert(logins_logouts, last_logged_date)

    if len(logins) > 0:
        fog_requester = LoginsRequester(fog_host=fog_host,
                                        mac=base64.b64encode(mac))
        fog_requester.set_logins_data(logins, last_logged_date)
    else:
        logging.info("No logins to notify server")

    return True
