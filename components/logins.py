import cuisine as c
from fog_lib import FogRequester
import logging
import pprint
import base64

from logsparser.lognormalizer import LogNormalizer as LN
 
class LoginsRequester(FogRequester):
    """Set logins data on fog server"""
    def _handler(self, text):
        """Process data from fog server and returns hostname"""
        return text

    def _user(self, user):
        return base64.b64encode("x\\" + user)
        
    def _data(self, date):
        return base64.b64encode(str(date))


    def set_login_data(self, logins):
        "Returns hostname saved on fog server"
        
        for login in logins:
            params = dict(service="usertracking.report", 
                          user=self._user(login["user"]),
                          date=self._data(login["date"])
                     )
            if login["action"] == "open":
                params["action"] = base64.b64encode("login")
                
            text = self.get_data(**params)
            aux = self._handler(text)
            print aux
        return aux


def client_hostname(fog_host, mac):
    """Main function for this module"""
    fog_server = HostnameRequester(fog_host=fog_host, mac=mac)
    action, reboot = False, False
    try:
        hostname = fog_server.get_hostname_data()
        action, reboot = ensure_hostname(hostname)
    except IOError as ex:
        logging.error(ex)
    except ValueError as ex:
        logging.error(ex)
    # except Exception as ex:
    #     logging.error(ex)
    return action, reboot
    

def client_logins(fog_host, mac):
    """Main function for this module"""
    
    normalizer = LN('/usr/local/share/logsparser/normalizers')
    auth_logs = open('/var/log/auth.log', 'r')
    
    print mac
 
    logins_logouts = []
    for l in auth_logs:
        log = {'raw' : l } # a LogNormalizer expects input as a dictionary
        normalizer.lognormalize(log)
        
        action = log.get('action')
        program = log.get('program')
        
        if (action == 'open' or action == 'close'):
            if(program != 'sudo' and program != 'cron'):
                logins_logouts.append(log)
                
        
    fog_requester = LoginsRequester(fog_host=fog_host, mac=base64.b64encode(mac))
    fog_requester.set_login_data(logins_logouts)

    pass
