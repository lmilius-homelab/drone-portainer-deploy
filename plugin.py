import json
import sys
import os
from .portainer_api import PortainerAPI


# class SwarmHelper:
#
#     def __init__(self, hostname, username, password, swarm_endpoint='docker-swarm-1'):
#         self.docker_swarm_endpoint = swarm_endpoint
#         self.api = PortainerAPI(hostname, username, password, self.docker_swarm_endpoint)
#         self.swarm_id = self.api.get_swarm_identity()
#         self.endpoint_id = self.api.get_endpoint_id(self.docker_swarm_endpoint)
#
#     def get_stack_contents(self, filename):
#         with open(filename, 'r') as stack_file:
#             return ''.join(str(x) for x in stack_file.readlines())
#
#     def deploy_stack(self, name, file_content):
#         stack_id = self.api.get_stack_id(name)
#         if stack_id:
#             resp = self.update_stack(stack_id, file_content)
#         else:
#             resp = self.deploy_new_stack(name, file_content)
#         return resp
#
#     def deploy_new_stack(self, name, file_content, docker_type=1, method='string'):
#         path = 'stacks'
#         payload = {
#             'Name': name,
#             'EndpointID': self.endpoint_id,
#             'SwarmID': self.swarm_id,
#             'StackFileContent': file_content
#         }
#         params = {
#             'type': docker_type,
#             'method': method,
#             'endpointId': self.endpoint_id
#         }
#         resp = self.api.post_to_api(path, payload, params=params)
#         return resp.json()
#
#     def update_stack(self, stack_id, file_content):
#         path = 'stacks/{}'.format(stack_id)
#         payload = {
#             'StackFileContent': file_content,
#             'Prune': True
#         }
#         params = {
#             'endpointId': self.endpoint_id
#         }
#         resp = self.api.put_to_api(path, payload, params=params)
#         return resp.json()
#
#     def delete_stack(self, name):
#         delete_params = {
#             'endpointId': self.endpoint_id
#         }
#         stack_id = self.api.get_stack_id(name)
#         if not stack_id:
#             print('Stack not found with name: {}'.format(name))
#             return None
#         path = 'stacks/{}'.format(stack_id)
#         resp = self.api.delete_to_api(path, params=delete_params)
#         if resp.status_code == 204:
#             return "Successful deletion of stack: {}".format(name)
#         else:
#             return "Delete failed, reason: {}".format(resp.text)

def get_stack_contents(filename):
    with open(filename, 'r') as stack_file:
        return ''.join(str(x) for x in stack_file.readlines())


def parse_environment_vars(env) -> list:
    """
    Convert json str or dict-formatted environment variables into
    portainer-formatted environment variables
    :param env: json string or dictionary of key-value env variables
    :return: list of portainer-formatted env variables
    :rtype: list
    """
    env_vars = []
    if isinstance(env, str):
        env = json.loads(env)
    if isinstance(env, dict):
        for name, value in env.items():
            env_vars.append({
                'name': name,
                'value': value
            })
    return env_vars


def get_parameters():
    params = {}
    try:
        params['url'] = os.environ['PLUGIN_URL']
        params['username'] = os.environ['PLUGIN_USERNAME']
        params['password'] = os.environ['PLUGIN_PASSWORD']
        params['stack_name'] = os.environ['PLUGIN_STACK_NAME']
    except KeyError as e:
        print(f'Missing required settings: {str(e)}')
        sys.exit(1)
    params['stack_file'] = os.environ.get('PLUGIN_STACK_FILE', 'docker-compose.yml')
    params['endpoint'] = os.environ.get('PLUGIN_ENDPOINT', 'primary')
    params['env'] = parse_environment_vars(os.environ.get('PLUGIN_ENVIRONMENT', "[]"))
    type = os.environ.get('PLUGIN_TYPE', 'compose')
    params['type'] = 1 if type == 'stack' else 2

    return params


def main():
    params = get_parameters()
    portainer = PortainerAPI(params['url'],
                             params['username'],
                             params['password'],
                             params['endpoint'])

    stack_contents = get_stack_contents(params['stack_file'])
    portainer.set_env(params['env'])
    portainer.set_docker_type(params['type'])

    resp = portainer.deploy_stack(params['stack_name'], stack_contents)
    print(json.dumps(resp, indent=2))
    if resp.status_code == 200:
        exit(0)
    else:
        print(f"Error code: {resp.status_code}")
        exit(1)


if __name__ == "__main__":
    main()
