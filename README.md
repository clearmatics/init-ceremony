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

## Example records for one validator node
* FQDN in `genesis.json`:
    ```json
    {
      "enode": "fqdn://validator1.example.com",
      "type": "validator",
      "stake": 50000
    }
    ```
* DNS records

  | type | name | value | TTL |
  |------|-------------------|-------------|---|
  | A    | validator1.example.com      | 203.0.113.1 | 1 min |
  | TXT  | validator1.example.com  |p=30303\; k=ad840ab412c026b098291f5ab56f923214469c61d4a8be41334c9a00e2dc84a8ff9a5035b3683184ea79902436454a7a00e966de45ff46dbd118e426edd4b2d0| 1 min |

## Docker usage
```shell script
docker run -v $(pwd)/genesis-template.json:/autonity/genesis-template.json -ti --rm ghcr.io/clearmatics/init-ceremony \
  --genesis-template "/autonity/genesis-template.json" \
  --dns 1.1.1.1,8.8.8.8
```
