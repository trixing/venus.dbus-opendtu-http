#!/usr/bin/env python

"""
Created by Jan Dittmer <jdi@l4x.org> in 2024
"""
from gi.repository import GLib as gobject
import argparse
import platform
import json
import logging
import sys
import os
import requests # for http GET
import time
import traceback

# our own packages
sys.path.insert(1, os.path.join(os.path.dirname(__file__), '../venus.dbus-trixing-lib'))
import dbus_trixing_template as dbus_trixing

log = logging.getLogger("DbusOpenDtuHttp")

class DbusOpenDtuHttpService:

  def _get_inverters(self, url):
    url = url + '/api/livedata/status'
    r = requests.get(url = url, timeout=10)
    d = r.json() 
    return d['inverters']


  def __init__(self, url, deviceinstance, phase_map, default_phase):
    self.url = url
    self.inv = {}
    self.phase_map = phase_map
    self.default_phase = default_phase
    self.instance = deviceinstance
    self.update_inverters()
    # self.update_livedata_multi()
    # gobject.timeout_add(3600 * 1000, self.update_inverters)


  # doesn't work unfortunately
  def update_livedata_multi(self):
    serials = ','.join(self.inv.keys())
    url = self.url + '/api/livedata/status?inv=' + serials
    r = requests.get(url, timeout=10)

  def update_inverters(self):
    for inv in self._get_inverters(self.url):
      log.info('Inverter data %r' % repr(inv))
      phase = self.phase_map.get(inv['serial'], self.default_phase)
      if inv['serial'] not in self.inv:
        self.inv[inv['serial']] = DbusOpenDtuInverterService(deviceinstance=self.instance + len(self.inv)*2,
                                 url=self.url,
                                 serial=inv['serial'],
                                 name=inv['name'],
                                 phase=phase)


class DbusOpenDtuInverterService(dbus_trixing.DbusTrixingPvInverter):

  def __init__(self, deviceinstance, url, serial, name, phase):
    device_name = 'opendtu_http_%s' % serial.replace('.', '_')
    display_name = 'OpenDtu %s %s' % (serial[-4:], name)
    self._url = url + '/api/livedata/status?inv=' + serial
    self._phase = 'L' + phase
    super().__init__(devicename=device_name,
                     displayname=display_name,
                     deviceinstance=deviceinstance,
                     serial=serial,
                     connection=url)

    self._temp = DbusOpenDtuTemperatureService(deviceinstance + 1, url, serial, name)
    gobject.timeout_add(5000, self._safe_update)
# /Position              <- 0=AC input 1; 1=AC output; 2=AC input 2
# /StatusCode            <- 0=Startup 0; 1=Startup 1; 2=Startup 2; 3=Startup
#                          3; 4=Startup 4; 5=Startup 5; 6=Startup 6; 7=Running;
#                          8=Standby; 9=Boot loading; 10=Error


  def _update(self):
    r = requests.get(url = self._url, timeout=10)
    data = r.json() 
    d = data['inverters'][0]
    # print(json.dumps(d, indent=4))
    ac = d['AC']['0']
    # print(ac)
    ds = self #._dbusservice
    if not d['reachable']:
         ds['/StatusCode'] = 10 # Error
         ds['/Ac/Power'] = 0
         ds['/Ac/L1/Power'] = 0
         ds['/Ac/L2/Power'] = 0
         ds['/Ac/L3/Power'] = 0
         return True

    if not d['producing']:
         ds['/StatusCode'] = 8  # Standby
         ds['/Ac/Power'] = 0
         ds['/Ac/L1/Power'] = 0
         ds['/Ac/L2/Power'] = 0
         ds['/Ac/L3/Power'] = 0
         return True

    ds['/StatusCode'] = 7  # Running

    def _r(v):
        return round(v, 1)

    ds['/MaxPower'] = d['limit_absolute']
    for k in ('Power', 'Voltage', 'Current'):
      ds['/Ac/' + self._phase + '/' + k] = _r(ac[k]['v'])
    ds['/Ac/Power'] = _r(ac['Power']['v'])
    ds['/Ac/Frequency'] = ac['Frequency']['v']
    ds['/Ac/Energy/Forward'] = _r(d['INV']['0']['YieldTotal']['v'])
    ds['/Ac/' + self._phase + '/Energy/Forward'] = _r(d['INV']['0']['YieldTotal']['v'])

    self._temp.set_temperature(_r(d['INV']['0']['Temperature']['v']))
    return True



class DbusOpenDtuTemperatureService(dbus_trixing.DbusTrixingTemperature):

  def __init__(self, deviceinstance, url, serial, name):
    device_name = 'opendtu_http_%s_temp' % serial.replace('.', '_')
    display_name = 'HM %s %s Temperature' % (serial[-5:], name)
    super().__init__(devicename=device_name,
                     displayname=display_name,
                     deviceinstance=deviceinstance,
                     serial=serial,
                     connection=url)

  def update(self, temperature):
    self.set_temperature(temperature)



def main():
  dbus_trixing.prepare()
  parser = argparse.ArgumentParser()
  parser.add_argument('--url', default='http://127.0.0.1', help='IP Addresses of OpenDtu')
  parser.add_argument('--instance', default=130, help='Requested Instance on DBUS')
  parser.add_argument('--phases', default='2', help='Phases Inverters are connected to, format: default,serial:phase,serial:phase,...')
  args = parser.parse_args()
  instances = {}
  n = 0
  phase_map = {}
  ps = args.phases.split(',')
  default_phase = ps[0]
  for p in ps[1:]:
      a = p.split(':')
      phase_map[a[0]] = a[1]
  for url in args.url.split(','):
    try:
      DbusOpenDtuHttpService(
        deviceinstance=int(args.instance + n),
        url=url,
        phase_map=phase_map,
        default_phase=default_phase)
      log.info("Connected to OpenDtu at %s" % url)
      n += 2
    except requests.exceptions.ConnectionError as e:
        print(e)
        log.info("Failed to connect to OpenDtu at %s" % url)
        time.sleep(1)

  dbus_trixing.run()


  log.info('Connected to dbus, and switching over to gobject.MainLoop() (= event based)')
  mainloop = gobject.MainLoop()
  mainloop.run()

if __name__ == "__main__":
  main()
