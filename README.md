# Venus OS Driver for polling http on OpenDTU Fusion

This program regularly polls a OpenDTU Fusion device on the
local network and creates a dbus device for an PV Inverter.

There is no control logic part of this driver. This is just
providing the data on the dbus.

## Installation (Supervise)

If you want to run the script on the GX device, proceed like
this 
```
cd /data/
git clone http://github.com/trixing/venus.dbus-trixing-lib
git clone http://github.com/trixing/venus.dbus-opendtu-http
chmod +x /data/venus.dbus-opendtu-http/service/run
chmod +x /data/venus.dbus-opendtu-http/service/log/run
```

### Configuration

To configure the service (e.g. provide a fixed IP or change
the phase configuration) edit `/data/venus.dbus-opendtu-http/service/run`.

Phase configuration has the format
```
--phase <default-phase>,<sn>:phase,<sn2>:phase
```

Example
```
--phase 3,342343243:1,964994:2
```


### Start the service

Finally activate the service
```
ln -sf /data/venus.dbus-opendtu-http/service /service/venus.dbus-opendtu-http
```

This line needs to be added to
[/data/rc.local](see https://www.victronenergy.com/live/ccgx:root_access)
as well for the service to start up automatically.

Create the file if it does not exist.


## Possible improvements

- [ ] Only do one HTTP request to get all the data
- [ ] Use web sockets instead of polling
- [ ] Get more device data
