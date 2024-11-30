#!/bin/env python3
import yaml,argparse;

# First, we'll build a dictionary of interface configuration.
def parse_config(config):
    with open(config, "r") as f:
        data = f. readlines();
    f.close()

    raw = [];
    for string in data:
        stripped = string.rstrip();
        if (stripped != "!"):
            raw.append(stripped);

    configurations = {};
    for line in raw:
        if ( line != "" and line[0] != ' '):
            config = line;
            configurations[config] = [];
        else:
            configurations[config].append(line.lstrip());
    interfaces = {};
    for config in configurations.keys():
        if ( config.split()[0] == "interface" ):
            interfaces[config] = configurations[config];
    return interfaces;

# Next, we write out a .yaml variable file with our dictionary for Ansible
def write_interface_dict(interfaces,networks):
    with open(networks,"r") as f:
        networks = yaml.safe_load(f);
    f.close();
    vlan_sort = {};
    for interface in interfaces.keys():
        for line in interfaces[interface]:
            words = line.split();
            if ( len(words) > 3 and words[2] == "vlan" ):
                vlan = "vlan " + words[-1];
                if (vlan not in vlan_sort.keys()):
                    vlan_sort[vlan] = [];
            elif ( len(words) > 4 and words[3] == "sticky"):
                host_total = 0;
                for num in vlan_sort.keys():
                    if (num != vlan):
                        host_total += len(vlan_sort[num]);
                port_int = int(interface.split("/")[-1])
                host_string = networks[vlan]["prefix"];
                hostname = host_string + str(int(port_int - host_total));
                hm= "".join(words[4].split("."));
                hostmac = hm[0:2]+":"+hm[2:4]+":"+hm[4:6]+":"+hm[6:8]+":"+hm[8:10]+":"+hm[10:12];
                host = dict(name = hostname, mac = hostmac, port = interface.split(" ")[1]);
                vlan_sort[vlan].append(host);
    return vlan_sort;

parser = argparse.ArgumentParser(prog="parse_interfaces",conflict_handler='resolve');
parser.add_argument('-p','--prefix', help='host group identifier prefix. E.g. \'host\'');
parser.add_argument('-f', '--config', help='running-config to parse.');
parser.add_argument('-n', '--networks', help='networks.yml to parse.');
args=parser.parse_args();

interfaces = parse_config(args.config);
vlan_sort = write_interface_dict(interfaces, args.networks);

with open("output_files/vlan_dict.yml", "w") as f:
    f.write(yaml.dump(vlan_sort));
f.close()

