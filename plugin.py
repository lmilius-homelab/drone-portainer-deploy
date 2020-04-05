import json
import requests
import sys
import os


class PortainerAPI:

    def __init__(self, url, username, password, endpoint_name):
        if not url.endswith('/'):
            url = url + '/'
        self.base_api_url = url + '{}'
        self.username = username
        self.password = password
        self.auth_headers = self.get_auth_headers()
        self.endpoint_name = endpoint_name
        self.env = {}
        self.docker_type = 1
        self.ssl_verify = True

    def get_from_api(self, path):
        url = self.base_api_url.format(path)
        return requests.get(url, headers=self.auth_headers, verify=self.ssl_verify)

    def post_to_api(self, path, payload, params=None):
        url = self.base_api_url.format(path)
        return requests.post(url, headers=self.auth_headers, json=payload, params=params, verify=self.ssl_verify)

    def put_to_api(self, path, paylod, params=None):
        url = self.base_api_url.format(path)
        return requests.put(url, headers=self.auth_headers, json=paylod, params=params, verify=self.ssl_verify)

    def delete_to_api(self, path, params=None):
        url = self.base_api_url.format(path)
        return requests.delete(url, params=params, headers=self.auth_headers, verify=self.ssl_verify)

    def get_auth_headers(self):
        payload = {
            'username': self.username,
            'password': self.password
        }
        resp = requests.post(self.base_api_url.format('auth'), json=payload, verify=self.ssl_verify)
        auth_token = resp.json()['jwt']
        headers = {
            'Authorization': f'Bearer {auth_token}'
        }
        return headers

    def get_endpoint_list(self):
        endpoints = self.get_from_api('endpoints')
        return endpoints.json()

    def get_registries(self):
        registries = self.get_from_api('registries')
        return registries.json()

    def get_stacks(self):
        stacks = self.get_from_api('stacks')
        return stacks.json()

    def get_stack_id(self, name):
        stacks = self.get_stacks()
        for stack in stacks:
            if stack['Name'] == name:
                return stack['Id']
        return None

    def get_endpoint(self, name):
        for endpoint in self.get_endpoint_list():
            if endpoint['Name'] == name:
                return endpoint
        return {}

    def get_endpoint_id(self, name):
        return self.get_endpoint(name)['Id']

    def get_swarm_identity(self, endpoint_name=None):
        if not endpoint_name:
            endpoint_name = self.endpoint_name
        docker_swarm_endpoint = self.get_endpoint(endpoint_name)
        if not docker_swarm_endpoint:
            return None
        endpoint_id = docker_swarm_endpoint['Id']
        url_path = 'endpoints/{}/docker/swarm'.format(endpoint_id)
        swarm_resp = self.get_from_api(url_path)
        swarm_id = swarm_resp.json()['ID']
        return swarm_id

    def set_env(self, env: dict):
        self.env = env

    def set_docker_type(self, docker_type: int):
        self.docker_type = docker_type

    def set_ssl_verify(self, ssl_verify: bool):
        self.ssl_verify = ssl_verify

    def deploy_stack(self, name, file_content):
        stack_id = self.get_stack_id(name)
        if stack_id:
            resp = self.update_stack(stack_id, file_content)
        else:
            resp = self.deploy_new_stack(name, file_content)
        return resp

    def deploy_new_stack(self, name, file_content, method='string'):
        path = 'stacks'
        payload = {
            'Name': name,
            'StackFileContent': file_content,
            'Env': self.env
        }
        if self.docker_type == 1:
            payload['SwarmID'] = self.get_swarm_identity(self.endpoint_name),
        params = {
            'type': self.docker_type,
            'method': method,
            'endpointId': self.get_endpoint_id(self.endpoint_name)
        }
        resp = self.post_to_api(path, payload, params=params)
        return resp.json()

    def update_stack(self, stack_id, file_content):
        path = 'stacks/{}'.format(stack_id)
        payload = {
            'StackFileContent': file_content,
            'Prune': True
        }
        params = {
            'endpointId': self.get_endpoint_id(self.endpoint_name)
        }
        resp = self.put_to_api(path, payload, params=params)
        return resp.json()


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
    docker_type = os.environ.get('PLUGIN_TYPE', 'compose')
    params['type'] = 1 if docker_type == 'stack' else 2
    params['ssl_verify'] = os.environ.get('PLUGIN_SSL_VERIFY', 'true') == 'true'

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
    portainer.set_ssl_verify(params['ssl_verify'])

    resp = portainer.deploy_stack(params['stack_name'], stack_contents)
    print(json.dumps(resp, indent=2))
    if resp.status_code == 200:
        exit(0)
    else:
        print(f"Error code: {resp.status_code}")
        exit(1)


if __name__ == "__main__":
    main()
