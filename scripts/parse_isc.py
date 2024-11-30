#!/bin/env python3
import argparse,yaml,ipaddress,re;

# isc-dhcp-server configuration files have curly brackets to group configuration items
# a semi-colon sands in for a line break, and one configuration is assumed per line.
# I like to do one-line dhcp reservations, but I must be able to handle source reservations
# that appear over multiple lines, making parsing the config tricky.

# Read the file and store each token\value\etc onto our list
def read_config(config):
    with open(config,"r") as f:
        lines = f.readlines();
    f.close;
    explode = [];
    for line in lines:
        words = line.split();
        for word in words:
            if "{" in word:
                splitted = word.split("{")
                explode.append("{");
                for item in splitted:
                    explode.append(item);
            elif "}" in word:
                splitted = word.split("}")
                for item in splitted:
                    explode.append(item);
                explode.append("}");
            else:
                explode.append(word);
    return explode;

def get_prefixes():
    networks = get_vlans();
    prefixes = [];
    for network in networks.keys():
        prefixes.append(networks[network]["prefix"])
    return prefixes;

def get_vlans():
    with open("input_files/networks.yml", "r") as f:
        networks = yaml.safe_load(f);
    f.close();
    return networks;

def get_stickies():
    with open("output_files/vlan_dict.yml","r") as f:
        stickies = yaml.safe_load(f);
    f.close()
    return stickies;

# Read the contents of input_files/networks.yml and the .conf to
# to coorelate host groups to vlans via prefix in the networks.yml.
def id_vlan_by_ip(word):
    networks = get_vlans();
    nets = [];
    for network in networks.keys():
        subnet = ipaddress.IPv4Network(networks[network]["network"]);
        nets.append(dict(name=network,network=subnet));
    ip_pattern = re.compile("\d{1,4}.\d{1,4}.\d{1,4}.\d{1,4};?");
    if (ip_pattern.match(word)):
        hostip=ipaddress.IPv4Network(word);
    for net in nets:
        if (hostip.overlaps(net["network"])):
            return net["name"]

# Produce single-line dhcp reservation string
def make_reservation(hostname,hostmac,ip):
    reservation = "host " + hostname + " { hardware ethernet " + hostmac + "; fixed-address " + ip + ";}";
    return reservation;

def get_existing_reservations(explode):
    prefixes = get_prefixes();
    vlans = get_vlans();
    vlan = "";
    group = []
    host = []
    vlan_dict={};
    for vlanid in vlans.keys():
        vlan_dict[vlanid] = [];
    prefix_patterns=[];
    for prefix in prefixes:
        prefix_patterns.append(re.compile(prefix+".*"));
    mac_pattern = re.compile("\w\w:\w\w:\w\w:\w\w:\w\w:\w\w");
    ip_pattern = re.compile("\d{1,4}.\d{1,4}.\d{1,4}.\d{1,4};?");
    id_check = False;
    for stripped in explode:
        word = stripped.strip();
        index = 0;
        for prefix in prefix_patterns:
            if (prefix.match(word)):
                id_check = True
        if ( word == "}" and vlan != "" and len(host) > 5):
            host_dict = dict(hostname=host[1],hostmac=host[4],ip=host[-1])
            vlan_dict[vlan].append(host_dict);
            vlan = "";
            host = []
        elif (word in ["host"," host", "host ","hardware","ethernet","fixed-address"]):
            host.append(word);
        elif (mac_pattern.match(word) and "ethernet" in host):
            host.append(word.strip(";"));
        elif (ip_pattern.match(word) and "fixed-address" in host):
            ip = word.strip(";")
            vlan = id_vlan_by_ip(ip);
            host.append(ip);
        elif (id_check):
            host.append(word);
            id_check = False;
    return vlan_dict;

def make_reservations(existing):
    networks = get_vlans();
    taken = [];

    stickies = get_stickies();
    new_dict = {};
    used_ips = [];
    used_hostnames = []
    for vlan in existing:
        for host in existing[vlan]:
            used_ips.append(ipaddress.IPv4Address(host["ip"]));
            used_hostnames.append(host["hostname"]);
    for network in networks.keys():
        new_dict[network] = []
        new_ip = ipaddress.IPv4Address(networks[network]["start_ip"])
        for host in stickies[network]:
            while (new_ip in used_ips and
                   new_ip < ipaddress.IPv4Address(networks[network]["stop_ip"])):
                new_ip +=1;
            hn = host["name"];
            while(hn in used_hostnames):
                hn = next_hostname(networks[network]["prefix"],hn);
            new_dict[network].append(make_reservation(hn,host["mac"],str(new_ip)));
            used_hostnames.append(hn);
            new_ip +=1;
    #print(new_dict)
    return new_dict;

# generate the next "hostname"/client-id for dhcp based on prefix.
def next_hostname(prefix,hostname):
    prefix_end = len(prefix);
    serial = int(hostname[prefix_end:]);
    return prefix+str(serial + 1);

# combine "existing" reservations from the file with reservations we would
# like from the sticky'd acess ports.
def all_reservations(explode):
    existing = get_existing_reservations(explode);
    new_reservations = make_reservations(existing);
    merged = {};
    for vlan in existing.keys():
        merged[vlan] = [];
        for reservation in new_reservations[vlan]:
            merged[vlan].append(reservation);
        for reservation in existing[vlan]:
            merged[vlan].append(make_reservation(reservation["hostname"],reservation["hostmac"],reservation["ip"]));
    return merged;

# Remove the dhcp host reservations in a given dhcpd.conf file. We
# assume a blank line before the host reservations. ymmv
def remove_reservations(config):
    with open(config,"r") as f:
        data = f.read();
    f.close();

    index = 0;
    group_indexes = [];
    host_indexes = [];
    end_indexes = [];
    res = False;
    for ch in data:
        if (ch=="h" and data[index:index+4]=="host"):
            res = True;
            host_indexes.append(index);
            group_index = index;
            while (data[group_index] != "\n"):
                group_index -= 1;
            group_indexes.append(group_index);
        elif (ch=="}" and res == True):
            end_indexes.append(index)
            res = False;
        index += 1;
    cleared = "";
    if (len(host_indexes)==len(end_indexes)):
        group_index = group_indexes[0];
        while(data[group_index-1] != "\n"):
            group_index -= 1;
        cleared += data[0:group_index];
    index = 0;
    clear = True;
    for ch in cleared:
        if (ch=="h" and cleared[index:index+4]=="host"):
            clear = False;
    if (clear):
        return cleared;

# Add reservations to a dhcpd.conf file. Assumes reservations are absent
def append_reservations(cleared, reservations):
    for vlan in reservations.keys():
        cleared += "group" + vlan.split()[1] + " {\n";
        for res in reservations[vlan]:
            cleared += "  " + res + "\n";
        cleared += " }\n\n";
    return cleared;

# write_updated_conf
# write a modified configuration file to output_files/
def write_updated_conf(config, cleared, reservations):
    output = append_reservations(cleared, reservations);
    with open("output_files/" + config.split("/")[-1],"w") as f:
        f.write(output);
    f.close

def update_isc(config):
    explode = read_config(config);
    reservations = all_reservations(explode);
    cleared = remove_reservations(config);
    write_updated_conf(config, cleared, reservations);

