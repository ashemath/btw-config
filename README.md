# btw-config
It started with wanting a script to collate the sticky'd MACs in a given VLAN,
and devolved into trying to make DHCP configuration. Gathering sticky's was
fun. Automating DHCP configuration has been a fun thought experiment.

Staus: Need to make a btw-config script and write the kea-dhcp parser.
I am excited about Kea's JSON data format. Hopefully, I can be more precise
than I was with ISC (Which will work iff there is a blank line ahead of existing
host reservations, as is customary, not necessarily convention).

## Idea
Let's generate DHCP configuration file based on a simple variable file.
Reservations based on the MAC address I see sticky'd with Cisco's 
`switchport port-security mac-address sticky`. 

The reservations match the order that they are plugged into the switch, 
on a per VLAN basis. So, the first access port configured in that VLAN will be given the 
first address, the next access port gets the second IP, and so on.

Let's consider an existing configuration file, and add reservations as appropriate.
Sending to console ourput a modified file that duplicates existing configuration,
adds reservations to the specified dhcp file, but preserving existing data.

I deploy large computer labs by setting up wall ports on a given lab on a single switch stack.
When connecting the computers, we connect them in a pattern, so our work group can easily find 
a machine if it's misbehaving. 
Imagine computers being addressed and placed in a room consecutively. It's beautiful when it's
done right, and you see hostnames increment "PC1, PC2, oh look PC3!".

## Packet Tracer Setup
To process a Cisco config, I will be utilizing a config that I'll generate with Cisco Packet Tracer.

The setup that I export the config from involves 8 PC's plugged into 8 ports of the 24 port
2960-PT switch. I have `switchport port-security` enabled to catch the sticky'd mac-address.
My example vlans are configured in `networks.yml`:

```yaml
vlan 6:
  prefix: "BB8"
  name: other
  network: 192.168.200.0/24
  start_ip: 192.168.200.3
  end_ip: 192.168.200.20
vlan 16:
  prefix: "R2D2"
  name: new
  network: 172.16.0.0/24
  start_ip: 172.16.0.3
  end_ip: 172.16.0.20
vlan 42:
  prefix: "C3PO"
  name: test
  network: 192.168.100.0/24
  start_ip: 192.168.100.3
  end_ip: 192.168.100.20
```

Gateways for vlan6, vlan16, and vlan42 live on a "distribution" switch, and our our "access" 
switch connects traffic from our PCS to the gateways on Distribution through it's "GigabitEthernet0/1"
port.

The file `running-config` is an artifact of me setting up the 8 PCs and three servers on the
three vlans. The ports configured with `switchport port-security` are the "lab" machines that I want configured with the DHCP automation.

The process was initially deploying all 8 PCs in vlan42. Next,  I configured half the machines
in Vlan6, and lastly, I stole a machine from both vlan6 and vlan42 for the "new" vlan16.

The result is an example of what you might have when going about assembling new networks from open ethernet ports. I find ports for my physical worstation locations, and I change the ports
`access vlan` id to join the newww network..

I'll already have dhcp zone files for isc-dhcp-server and kea-dhcp, ending in .conf and .json
respectively. I want to load the dhcp config file, load the reservations into Python, and fill
in DHCP reservations for MAC addresses that are not present in the DHCP configuration.

## btw-config usage

We can run:

```sh
btw-config --kea --config other.json --rc running-config
```

to update other.json.

or for isc-dhcp-server:

```sh
btw-config --isc --config other.conf --rc running-config
```
to update other.conf

## Design goals
The goals are to produce:
- Both kea-dhcp and isc-dhcp subnet configuration.
- single .yml variable output file, for automating other tasks.

We'll only read files from `input_files`, and we'll write files to `output_files/`, for safety's sake. Always inspect, lint, and test your config files before deploying into production!

## scripts/parse_interaces.py
This script reads the running-config and outputs to `output_files/vlan_dict.yml`. By setting
`prefix`, we can name whatever room/building/etc we want added to the
hostname. For example, prefix="JK867" for Room 867 of the Joseph Kibbles facility.

## scripts/parse_isc.py
This script works off of isc-dhcp-server dhcpd.conf file to add host reservations based on the
stickies.yml output file from `parse_interfaces.py`. The script parses the existing IPv4 host
reservations, stores them in a dictionary, and compiles new groups of host reservations into
a new file under `output_files/`.

## scripts/parse_kea.py
This script also works between dhcp configuration file and the stickies.yml output from
parse_interfaces.py

