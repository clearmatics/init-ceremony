#!/usr/bin/env python

import json
import argparse
import socket
import sys
from kubernetes import client, config


def main():
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
        try:
            socket.inet_aton(ip)
        except socket.error:
            sys.exit('ERROR: Wrong value for argument --dns. Should be a list of IPv4 separated by comma')

    if args.kubeconf_type == 'pod':
        config.load_incluster_config()
        f = open("/var/run/secrets/kubernetes.io/serviceaccount/namespace", "r")
        namespace = f.readline()
        f.close()
    elif args.kubeconf_type == 'remote':
        config.load_kube_config()
        namespace = args.namespace
    else:
        print('INFO: Starting without kubernetes connection')


if __name__ == '__main__':
    main()
