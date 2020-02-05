#!/usr/bin/python3

import argparse
import sys, os
from pprint import pprint
import json, yaml 
import kubernetes
import subprocess

DEBUG = True

class KubectlIt(object):

    __config_base_path = None
    __parser = None
    __subparsers = None
    __add_parser = None
    __add_subparsers = None
    __run_parser = None
    __ls_parser = None
    __config_path = None
    __argv = None
    
    def __init__(self):
        self.__parser = argparse.ArgumentParser(
            description=''
        )

        self.__subparsers = self.__parser.add_subparsers(help="Command to execute.")

        self.__prepare_add()
        self.__prepare_ls()
        self.__prepare_run()

        self.__argv = sys.argv
        self.__args = self.__parser.parse_args(sys.argv[1:])
        self.__config_base_path = "{}/.kube/kubectlit/configs".format(os.environ.get('HOME'))
        
        if len(sys.argv) > 1:
            getattr(self, sys.argv[1])()
    
    def add(self):
        try:
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
                                # let's edit the configuration tree
                                #    'original_path': self.__args.path,
                                #    'original_name': i['name'],
                                path = self.__create_path_and_file(
                                    self.__argv[2],
                                    {
                                        'filename': "{}_kube.config".format(name),
                                        'content': self.__generate_kubeconfig(i, kcfg_data)
                                    }
                                )
                                #    'type': 'kubeconfig'
                                found_context = True
                    
                        if not found_context:
                            # if we didnt
                            print("Couldn't find requested context {} in {}.".format(
                                self.__args.original_name, self.__args.path
                                )
                            )
                            exit(2)

                elif self.__argv[3] == 'awseks':
                    profile = self.__args.profile
                    cluster_name = self.__args.cluster_name
                    region = self.__args.region    
                    name = self.__args.name

                    filename = "{}_kube.config".format(name)

                    self.__create_path_and_file(
                        self.__argv[2],
                        {
                            'filename': filename,
                            'content': {}
                        }
                    )
                    #'type': 'awseks',
                    #'profile': profile,
                    #'cluster_name': cluster_name,
                    #'region': region
                    self.__generate_kubeconfig_from_awseks(
                        "{}/{}".format(self.__argv[2], filename),
                        cluster_name, region, profile
                    )
        except json.decoder.JSONDecodeError as err:
            print("Config file syntax is not good, or file is empty.")
            print("Error: {}".format(err))
            exit(2)
    
    def ls(self):
        path = self.__argv[2]
        try:
            self.__print_tree(path)
        except KeyError as ke:
            print("Can't find context with path {}".format(path))
            print("Error: {}".format(ke))
    
    def run(self):
        path = self.__argv[2]
        cmd = self.__args.command
        self.__run_on_tree(path, cmd)
    
    def __run_on_tree(self, path, cmd, d=0):
        startpath = "{}/{}".format(self.__config_base_path, path)
        for root, dirs, files in os.walk(startpath):
            level = root.replace(startpath, '').count(os.sep)
            for f in files:
                self.__run(cmd, "{}/{}".format(root, f))
    
    def __run(self, cmd, path):
        print("KUBECONFIG is {}".format(path))
        kubernetes.config.load_kube_config(config_file=path)
        subprocess.check_call("KUBECONFIG={} {}".format(path, ' '.join(map(str, cmd))), shell=True)
        
    def __print_tree(self, path):
        startpath = "{}/{}".format(self.__config_base_path, path)
        for root, dirs, files in os.walk(startpath):
            level = root.replace(startpath, '').count(os.sep)
            indent = ' ' * 4 * (level)
            extra = ''
            if level > 0:
                extra = '└──'
            print('{}{}{}/'.format(indent, extra, os.path.basename(root)))
            subindent = ' ' * 4 * (level + 1)
            for f in files:
                print('{}└──{}'.format(subindent, f))
    
    def __generate_kubeconfig_from_awseks(self, kubeconfig_path, cluster_name, region, profile):
        path = "{}/{}".format(self.__config_base_path, kubeconfig_path)
        if os.path.exists(path):
            try:
                subprocess.check_call(
                    [
                        'aws', 'eks', 'update-kubeconfig',
                        '--region', region, '--name', cluster_name,
                        '--profile', profile, '--kubeconfig',
                        path
                    ]
                )
                return True
            except Exception:
                return False

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
        content['current-context'] = context['name']
        return content

    def __create_config_path(self, config_path, tree):
        path_in_list = config_path.split('/')
        last = tree
        for elmt in path_in_list:
            last[elmt] = {}
            last = last[elmt]
        return tree

    def __create_path_and_file(self, config_path, content):
        """
        Creates the whole path of a file, including the parent folders.
        Returns the full path of the resulting file.
        """
        path_in_list = config_path.split('/')
        path = self.__config_base_path
        newpath = path
        for elmt in path_in_list:
            newpath = "{}/{}".format(newpath, elmt)
            if not os.path.exists(newpath):
                os.makedirs(newpath)
        self.__write_yaml_file_from_dict(
            content['content'],
            "{}/{}".format(newpath, content['filename'])
        )
        
        return newpath
    
    def __prepare_add(self):
        self.__add_parser = self.__subparsers.add_parser(
            'add',
            help="Add context(s) to the configuration tree."
        )
        self.__add_parser.add_argument(
            'context_name',
            help="Name of the context to be added. \
                Either a simple name or a config path with categories like \"cat1/subcatA/contextA\"."
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
            help="Final name of the context to be added."
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
        self.__add_awseks_parser.add_argument(
            '--name',
            help="Final name of the context to be added."
        )
    
    def __prepare_ls(self):
        self.__ls_parser = self.__subparsers.add_parser(
            'ls', help="Lists all contexts in a path."
        )
        self.__ls_parser.add_argument(
            'name', help="A path to one or multiple contexts in the tree like: \"path/to/target/contexts\""
        )
    
    def __prepare_run(self):
        self.__run_parser = self.__subparsers.add_parser(
            'run', help="Runs an action on multiple contexts."
        )
        self.__run_parser.add_argument(
            'path', help="A path to one or multiple contexts in the tree like: \"path/to/target/contexts\""
        )
        self.__run_parser.add_argument(
            'command', help="Command to run on clusters selected by PATH.", nargs='+'
        )
    
    def __write_json_file_from_dict(self, source_dict, file_path):
        with open(file_path, 'w') as fd:
            json.dump(source_dict, fd, indent=4)
            fd.close()
    
    def __write_yaml_file_from_dict(self, source_dict, file_path):
        with open(file_path, 'w') as fd:
            yaml.dump(source_dict, fd, default_flow_style=False)
            fd.close()

if __name__ == '__main__':
    KubectlIt()
