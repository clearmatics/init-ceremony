#!/usr/bin/env python

import json
import argparse
import logging
import validators
import dns.resolver
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


def resolving(fqdn_peers):
    resolver = dns.resolver.Resolver(configure=False)
    resolver.nameservers = ['8.8.8.8', '1.1.1.1']

    # Here will loop

    resolved_peers = {}
    for peer in fqdn_peers:
        try:
            answer = resolver.query(peer, 'A')
            if answer.__len__() == 1:
                logging.debug('IP for ' + peer + ': ' + answer[0].address)
                resolved_peers = {peer: {'ip': answer[0].address}}
            else:
                logging.error('for ' + peer + ' must be only one A record')
        except Exception as e:
            logging.warning(e)

        try:
            answer = resolver.query(peer, 'TXT')
            for data in answer:
                for txt_string in data.strings:
                    logging.debug('TXT for ' + peer + ': ' + str(txt_string, 'utf-8'))
        except Exception as e:
            logging.warning(e)
    return resolved_peers


def main():
    logging.basicConfig(
        format='%(asctime)s %(levelname)-8s %(message)s',
        level=logging.DEBUG,
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
    print(fqdn_peers)
    print(resolving(fqdn_peers))


if __name__ == '__main__':
    main()
