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


def parse_peer_list(genesis: object) -> object:
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


def resolving(fqdn_peers):
    resolver = dns.resolver.Resolver(configure=False)
    resolver.nameservers = ['8.8.8.8', '1.1.1.1']

    # Here will loop

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
            logging.warning(e)

        try:
            answer = resolver.query(peer, 'TXT')
            for data in answer:
                for txt_string in data.strings:
                    rec = parse_txt_rec(str(txt_string, 'utf-8'))
                    if rec:
                        resolved_peer['port'] = rec[0]
                        resolved_peer['pub_key'] = rec[1]
        except Exception as e:
            logging.warning(e)
        logging.debug('fqdn://' + peer + ' resolved to ' + str(resolved_peer))
        if len(resolved_peer) == 3:
            resolved_peers[peer] = resolved_peer
    return resolved_peers


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
    resolvers = args.dns_resolvers.split(',')
    for ip in resolvers:
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

    genesis = get_genesis_template(args.path_genesis_template)
    fqdn_peers = parse_peer_list(genesis)
    logging.info('Trying to resolv peers: ' + str([*fqdn_peers]))

    resolved_peers = {}
    while len(resolved_peers) != len(fqdn_peers):
        resolved_peers = resolving(fqdn_peers)
        logging.info('Resolved ' + str(len(resolved_peers)) + ' fqdn records from ' + str(len(fqdn_peers)))
        time.sleep(10)
    else:
        logging.info('All fqdn records was resolved successfully')
        print('WIN!')
    #print(resolved_peers)


if __name__ == '__main__':
    main()
