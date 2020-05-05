# kubectl-it
<p>
  <img alt="Version" src="https://img.shields.io/badge/version-0.1a-blue.svg?cacheSeconds=2592000" />
  <a href="#" target="_blank">
    <img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-yellow.svg" />
  </a>
  <a href="https://twitter.com/bpetit_" target="_blank">
    <img alt="Twitter: bpetit_" src="https://img.shields.io/twitter/follow/bpetit_.svg?style=social" />
  </a>
</p>

**Warning: this is work in progress**

kubectl it is a kubectl plugin to make kubernetes clusters fleet management easier.

## Usage

**kubectl it** manages kubernetes contexts for you, as distinct kubeconfig files (let's forget this **gigantic** and unmanageable ~/.kube/.config).

Each time you add add a context, from either an original kubeconfig file:

```sh
kubectl it add where/to/store/in/the/configuration/tree kubeconfig --path path/to/original/kubeconfig --original-name name-in-original-kubeconfig --name name-in-the-config-tree
```

or generating it with AWS EKS IAM authenticator:

```sh
kubectl it add where/to/store/in/the/configuration/tree awseks --name mycluster --profile my-iam-profile --region eu-west-2 --cluster-name mycluster --name name-in-the-config-tree
```

it will store those new kubconfig files in a configuration tree as the one below:

```
/home/bpetit/.kube/kubectlit
└── configs
    ├── foo
    │   ├── bar
    │   │   └── monitoring-clusters
    │   │       └── monitoring-clu01_kube.config
    │   └── foo
    │       └── bar
    │           └── monitoring-clusters
    │               └── monitoring-clu02_kube.config
    ├── production
    │   ├── monitoring
    │   │   └── monitoring-clusters
    │   │       └── monitoring-clu02_kube.config
    │   └── webapps
    │       └── app01
    │           ├── admin-on-app01_kube.config
    │           └── unprivileged-on-app01_kube.config
    ├── staging
    │   └── webapps
    │       └── app01
    │           └── admin-on-app01_kube.config
    └── where
        └── to
            └── store
                └── in
                    └── the
                        └── configuration
                            └── tree
                                └── mycluster_kube.config
```

Then you can select which context or multiple contexts and run arbitrary actions on it (handy for cluster components upgrades for example).

To list what's inside a category/folder:

```sh
$ kubectl it ls production/webapps/app01
app01/
    admin-on-app01_kube.config
    unprivileged-on-app01_kube.config
```

To run an action on those contexts (be careful with what you do):

```sh
kubectl it run production/webapps/app01 kubectl get po -l app=myapp
```

or:

```sh
kubectl it run production/webapps/app01 ./upgrade.sh
```

## Run tests

To validate that everything is working, you can list all kubeconfig files stores in the tree:

```sh
kubectl it ls /
```

## Author

👤 **Benoit Petit**

* Website: https://bpetit.nce.re

## 🤝 Contributing

Contributions, issues and feature requests are welcome!<br />Feel free to check [issues page](https://github.com/bpetit/kubectl-it/issues).

## Show your support

Give a ⭐️ if this project helped you!

***
_This README was generated with ❤️ by [readme-md-generator](https://github.com/kefranabg/readme-md-generator)_
