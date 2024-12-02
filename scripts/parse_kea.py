#!/bin/env python3
import ipaddress,json,yaml;

def read_config(config):
    with open(config, "r") as f:
        data = json.load(f);
    f.close();
    return data

def read_yml(file):
    with open(file, "r") as f:
        data = yaml.safe_load(f);
    f.close();
    return data;

def get_reservations(config):
    data = read_config(config);
    reservations = data["reservations"];
    return reservations;

# generate the next "hostname"/client-id for dhcp based on prefix.
def next_hostname(prefix,hostname):
    prefix_end = len(prefix);
    serial = int(hostname[prefix_end:]);
    return prefix+f"{serial + 1:02d}";

# Return the vlan, for example "vlan 42", that has a matching CIDR network
# definition. Assume we are looking at a single "dhcp4"."subnet" object in the
# json configuring file.
def subnet_to_vlan(config):
    networks = read_yml("input_files/networks.yml");
    subnet = read_config(config)["subnet"];
    for network in networks.keys():
        if (networks[network]["network"] == subnet ):
            return network;

def write_updated_config(config,vlanf=""):
    networks = read_yml("input_files/networks.yml");
    existing = get_reservations(config);
    existing_ips = [];
    existing_names = [];
    for host in existing:
        existing_ips.append(ipaddress.IPv4Address(host["ip-address"]));
    for host in existing:
        existing_names.append(host["hostname"]);
    stickies = read_yml("output_files/stickies.yml");
    vlan = subnet_to_vlan(config);
    prefix = networks[vlan]["prefix"];
    try_ip = ipaddress.IPv4Address(networks[vlan]["start_ip"]);
    for host in stickies[vlan]:
        try_name = host["name"];
        while (try_ip in existing_ips):
            try_ip += 1;
        while (try_name in existing_names):
            try_name = next_hostname(prefix,try_name);
        reservation = {"hostname":try_name,"hw-address":host["mac"],"ip-address":str(try_ip)};
        existing_ips.append(try_ip);
        existing_names.append(try_name);
        existing.append(reservation);
    with open(config,"r") as f:
        data = json.load(f);
    f.close()
    data["reservations"] = existing;
    output_file = "output_files/"+config.split("/")[1];
    with open(output_file,"w") as f:
        json.dump(data,f,indent=2);
    f.close();
    return output_file;
