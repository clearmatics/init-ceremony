#!/usr/bin/env python

import json
import argparse
import logging
import validators
import dns.resolver
import time
from kubernetes import client, config


def get_genesis_template(path_genesis_template):
    with open(path_genesis_template) as f:
        genesis = json.load(f)
    return genesis


def parse_peer_list(genesis):
    users = genesis['config']['autonityContract']['users']
    fqdn_peers = {}
    for user in users:
        if 'enode' in user:
            if user['enode'][:7] == 'fqdn://':
                if not validators.domain(user['enode'][7:]):
                    logging.error('ERROR: Domain is not valid FQDN: ' + user['enode'][7:])
                    exit(1)
                logging.debug('Add fqdn to resolving: ' + user['enode'][7:])
                fqdn_peers[user['enode'][7:]] = {}
    return fqdn_peers


def parse_txt_rec(record):
    # Looking for string like:
    # "p=30303; k=ad840ab412c026b098291f5ab56f923214469c61d4a8be41334c9a00e2dc84a8ff9a5035b3683184ea79902436454a7a00e966de45ff46dbd118e426edd4b2d0"
    # is else: return False
    port = 0
    pub_key = ''
    if record.split("; ").__len__() < 2:
        return False
    for key in record.split("; "):
        if key.split("=")[0] == 'p':
            if key.split("=")[1].isdigit() and key.split("=")[1].__len__() <= 5:
                int(key.split("=")[1])
                if int(key.split("=")[1]) < 65535:
                    port = int(key.split("=")[1])
        elif key.split("=")[0] == 'k':
            pub_key = key.split("=")[1]
    if port == 0\
            or pub_key.__len__() != 128\
            or not pub_key.isalnum():
        return False
    return port, pub_key


def resolving(fqdn_peers, nameservers):
    resolver = dns.resolver.Resolver(configure=False)
    resolver.nameservers = nameservers

    resolved_peers = {}
    for peer in fqdn_peers:
        resolved_peer = {}
        try:
            answer = resolver.query(peer, 'A')
            if answer.__len__() == 1:
                resolved_peer['ip'] = answer[0].address
            else:
                logging.error('for ' + peer + ' must be only one A record')
        except Exception as e:
            logging.warning('A record: ' + str(e))

        try:
            answer = resolver.query(peer, 'TXT')
            for data in answer:
                for txt_string in data.strings:
                    rec = parse_txt_rec(str(txt_string, 'utf-8'))
                    if rec:
                        resolved_peer['port'] = rec[0]
                        resolved_peer['pub_key'] = rec[1]
        except Exception as e:
            logging.warning('TXT record: ' + str(e))
        if len(resolved_peer) > 0:
            logging.info('fqdn://' + peer + ' resolved to ' + str(resolved_peer))
        if len(resolved_peer) == 3:
            resolved_peers[peer] = resolved_peer
    return resolved_peers


def patch_genesis(genesis, resolved_peers):
    genesis = genesis
    for i, user in enumerate(genesis['config']['autonityContract']['users']):
        if 'enode' in user:
            if user['enode'][:7] == 'fqdn://':
                fqdn=user['enode'][7:]
                enode_string = 'enode://{pub_key}@{ip}:{port}'.format(
                    pub_key=resolved_peers[fqdn]['pub_key'],
                    ip=resolved_peers[fqdn]['ip'],
                    port=resolved_peers[fqdn]['port'],
                )
                genesis['config']['autonityContract']['users'][i]['enode'] = enode_string
    return genesis


def write_genesis(genesis, namespace, cm_name):
    api_instance = client.CoreV1Api()
    cmap = client.V1ConfigMap()
    cmap.data = {'genesis.json': json.dumps(genesis, indent=2)}
    api_instance.patch_namespaced_config_map(cm_name, namespace, cmap)


def main():
    logging.basicConfig(
        format='%(asctime)s %(levelname)-8s %(message)s',
        level=logging.INFO,
        datefmt='%Y-%m-%d %H:%M:%S')

    parser = argparse.ArgumentParser(description='Resolve by fqdn:// records from genesis-template.json and write '
                                                 'enode:// to genesis.json')
    parser.add_argument('-k',
                        dest='kubeconf_type',
                        default='non_k8s',
                        choices=['pod', 'remote', 'non_k8s'],
                        help='Type of connection to kube-apiserver: pod or remote (default: %(default)s)'
                        )
    parser.add_argument('--genesis-template',
                        dest='path_genesis_template',
                        default="/autonity/genesis-template.json",
                        type=str,
                        help='Path to genesis template json file (default: %(default)s)'
                        )
    parser.add_argument('--genesis-cm',
                        dest='cm_genesis',
                        default='genesis',
                        type=str,
                        help='Name for genesis ConfigMap (default: %(default)s)'
                        )
    parser.add_argument('--dns',
                        dest='dns_resolvers',
                        default='1.1.1.1,8.8.8.8',
                        type=str,
                        help='List of DNS resolvers (default: %(default)s)'
                        )
    parser.add_argument('--namespace',
                        dest='namespace',
                        default='default',
                        help='Kubernetes namespace.'
                        )
    args = parser.parse_args()
    nameservers = args.dns_resolvers.split(',')
    for ip in nameservers:
        if not validators.ip_address.ipv4(ip):
            logging.error('ERROR: Wrong value for argument --dns '
                          + ip + '. Should be a list of IPv4 separated by comma')
            exit(1)

    if args.kubeconf_type == 'pod':
        config.load_incluster_config()
        f = open("/var/run/secrets/kubernetes.io/serviceaccount/namespace", "r")
        namespace = f.readline()
        f.close()
    elif args.kubeconf_type == 'remote':
        config.load_kube_config()
        namespace = args.namespace
    else:
        logging.info('Starting without kubernetes connection')

    genesis_template = get_genesis_template(args.path_genesis_template)
    fqdn_peers = parse_peer_list(genesis_template)
    logging.info('Trying to resolv peers: ' + str([*fqdn_peers]))

    logging.info('Use Name Servers to resolve records: ' + str(nameservers))
    resolved_peers = {}
    while len(resolved_peers) != len(fqdn_peers):
        resolved_peers = resolving(fqdn_peers, nameservers)
        logging.info('Fully resolved ' + str(len(resolved_peers)) + ' fqdn records from ' + str(len(fqdn_peers)))
        if len(resolved_peers) != len(fqdn_peers):
            time.sleep(10)
    else:
        logging.info('All fqdn records was resolved successfully')

    genesis = patch_genesis(genesis_template, resolved_peers)
    time.sleep(0.5)
    print(str(json.dumps(genesis, indent=2)))

    if args.kubeconf_type != 'non_k8s':
        write_genesis(genesis, namespace, args.cm_genesis)
        logging.info('Generated genesis was written successfully to ConfigMap ' + str(args.cm_genesis))


if __name__ == '__main__':
    main()
