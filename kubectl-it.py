#!/usr/bin/python3

import argparse
import sys, os
from pprint import pprint
import json, yaml 
import kubernetes

DEBUG = True

class KubectlIt(object):

    __config_base_path = None
    __parser = None
    __subparsers = None
    __add_parser = None
    __add_subparsers = None
    __config_path = None
    __argv = None
    
    def __init__(self):
        self.__parser = argparse.ArgumentParser(
            description=''
        )

        self.__subparsers = self.__parser.add_subparsers(help="Command to execute.")

        self.__prepare_add()

        self.__argv = sys.argv
        self.__args = self.__parser.parse_args(sys.argv[1:])
        self.__config_base_path = "{}/.kube/kubectlit/configs".format(os.environ.get('HOME'))

        self.__config_path = './config.json'

        if not os.path.exists(self.__config_path) or os.stat(self.__config_path).st_size == 0:
            self.__write_json_file_from_dict(dict(), self.__config_path)
        
        if len(sys.argv) > 1:
            getattr(self, sys.argv[1])()
    
    def add(self):
        try:
            with open(self.__config_path, "r") as fd:
                config = json.loads(fd.read())
                fd.close()
                print("BEFORE")
                pprint(config)
                self.__create_config_path(self.__argv[2], config)
                #print(self.__get_config_leaf("path>to>ctx", config))
                if len(self.__argv) > 3:
                    if self.__argv[3] == 'kubeconfig':
                        # we have to look at the kubeconfig file content and
                        # generate one context entry in the config or multiple
                        # if the kubeconfig containts multiple contexts
                        with open(self.__args.path, 'r') as kcfg:
                            kcfg_data = yaml.safe_load(kcfg)
                            
                            contexts_from_current_config, current_context = kubernetes.config.list_kube_config_contexts(self.__args.path)

                            found_context = False
                            # we look for the wanted context in the config file
                            for i in contexts_from_current_config:
                                # if we find it
                                if i['name'] == self.__args.original_name:
                                    # we add it to the tree
                                    name = i['name']
                                    # if the user asked for a final name
                                    if (
                                        'final_name' in self.__args
                                        and self.__args.final_name is not None
                                    ):
                                        name = self.__args.final_name
                                    # let's edit the configuration
                                    self.__get_config_leaf(self.__argv[2], config)[name] = {
                                        'original_path': self.__args.path,
                                        'original_name': i['name'],
                                        'path': self.__create_path_and_file(
                                            self.__argv[2], config,
                                            {
                                                'filename': "{}_kube.config".format(name),
                                                'content': self.__generate_kubeconfig(i, kcfg_data)
                                            }
                                        )
                                    }
                                    pprint(i)
                                    found_context = True
                        
                            if not found_context:
                                # if we didnt
                                print("Couldn't find requested context {} in {}.".format(
                                    self.__args.original_name, self.__args.path
                                    )
                                )
                                exit(2)
                
                self.__write_json_file_from_dict(config, self.__config_path)

        except json.decoder.JSONDecodeError as err:
            print("Config file syntax is not good, or file is empty.")
            print("Error: {}".format(err))
            exit(2)

    def __generate_kubeconfig(self, context, kubeconfig):
        content = {
            'apiVersion': 'v1',
            'clusters': [],
            'contexts': [],
            'users': []
        }
        for c in kubeconfig['clusters']:
            if context['context']['cluster'] == c['name']:
                content['clusters'].append(
                    {
                        'name': c['name'],
                        'cluster': c['cluster']
                    }
                )
        for u in kubeconfig['users']:
            if context['context']['user'] == u['name']:
                content['users'].append(
                    {
                        'name': u['name'],
                        'user': u['user']
                    }
                )
        content['contexts'].append(
            {
                'name': context['name'],
                'context': context['context']
            }
        )
        return content
    
    def __write_json_file_from_dict(self, source_dict, file_path):
        with open(file_path, 'w') as fd:
            json.dump(source_dict, fd, indent=4)
            fd.close()
    
    def __write_yaml_file_from_dict(self, source_dict, file_path):
        with open(file_path, 'w') as fd:
            yaml.dump(source_dict, fd, default_flow_style=False)
            fd.close()

    def __create_config_path(self, config_path, tree):
        path_in_list = config_path.split('>')
        last = tree
        for elmt in path_in_list:
            last[elmt] = {}
            last = last[elmt]
        return tree

    def __create_path_and_file(self, config_path, tree, content):
        """
        Creates the whole path of a file, including the parent folders.
        Returns the full path of the resulting file.
        """
        path_in_list = config_path.split('>')
        last = tree 
        path = self.__config_base_path
        newpath = path
        for elmt in path_in_list:
            newpath = "{}/{}".format(newpath, elmt)
            if not os.path.exists(newpath):
                os.makedirs(newpath)
        pprint(content['content'])
        self.__write_yaml_file_from_dict(
            content['content'],
            "{}/{}".format(newpath, content['filename'])
        )
        #with open("{}/{}".format(newpath, content['filename']), "w") as fd:
        #    fd.write(content['content'])
        #    fd.close()
        
        return newpath
    
    def __get_config_leaf(self, config_path, tree):
        path_in_list = config_path.split('>')
        last = tree
        for elmt in path_in_list:
            last = last[elmt]
        return last

    def __prepare_add(self):
        self.__add_parser = self.__subparsers.add_parser(
            'add',
            help="Add context(s) to the configuration tree."
        )
        self.__add_parser.add_argument(
            'context_name',
            help="Name of the context to be added. \
                Either a simple name or a config path with categories like \"cat1>subcatA>contextA\"."
        )
        self.__add_subparsers = self.__add_parser.add_subparsers(
            help="What kind of configuration to provide as context(s)."
        )
        self.__add_kubeconfig_parser = self.__add_subparsers.add_parser('kubeconfig')

        self.__add_kubeconfig_parser.add_argument(
            '--path', required=True,
            help="Path to a kubeconfig file to integrate to the tree."
        )
        self.__add_kubeconfig_parser.add_argument(
            '--original-name', required=True,
            help="Name of the context, as it is in the original kubeconfig file, to add to the tree."
        )
        self.__add_kubeconfig_parser.add_argument(
            '--name', required=False, dest='final_name',
            help="Final name of the context to add to the tree."
        )

        self.__add_awseks_parser = self.__add_subparsers.add_parser('awseks')

        self.__add_awseks_parser.add_argument(
            '--profile',
            help='AWS IAM profile to be used to connect to the cluster',
            required=True
        )
        self.__add_awseks_parser.add_argument(
            '--cluster-name',
            help='Name of the AWS EKS cluster',
            required=True
        )
        self.__add_awseks_parser.add_argument(
            '--region',
            help='AWS region where the cluster is',
            required=True
        )

if __name__ == '__main__':
    KubectlIt()
