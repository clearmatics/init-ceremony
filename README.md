# Autonity initial ceremony
Autonity initial ceremony

## External Dependencies
- kube-apiserver v1.14.6

## Usage:
```
usage: main.py [-h] [-k {pod,remote,non_k8s}]
               [--genesis-template PATH_GENESIS_TEMPLATE]
               [--genesis-cm CM_GENESIS] [--dns DNS_RESOLVERS]
               [--namespace NAMESPACE]

Resolve by fqdn:// records from genesis-template.json and write enode:// to genesis.json

optional arguments:
  -h, --help                               show this help message and exit
  -k {pod,remote,non_k8s}                  Type of connection to kube-apiserver: pod or remote (default: non_k8s)
  --genesis-template PATH_GENESIS_TEMPLATE Path to genesis template json file (default: /autonity/genesis-template.json)
  --genesis-cm CM_GENESIS                  Name for genesis ConfigMap (default: genesis)
  --dns DNS_RESOLVERS                      List of DNS resolvers (default: 1.1.1.1,8.8.8.8)
  --namespace NAMESPACE                    Kubernetes namespace.
```