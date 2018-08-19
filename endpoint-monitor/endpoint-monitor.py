import requests
import os
from time import sleep
import json

# We get the host:port of the Sensu and Consul APIs via environment variables
SENSU_API = os.environ['SENSU_API']
CONSUL_API = os.environ['CONSUL_API'] 


def get_clients_with_consul_checks():
    """
    Return a list of clients from Sensu, filtering on check_source == consul, which is a k/v pair we add as
    part of this monitoring script. It is important that we only deal with clients that have this k/v pair,
    because we don't want to delete clients from Sensu that we didn't create.
    """
    consul_clients = [ ]
    r = requests.get('{}/results'.format(SENSU_API))
    client_list = r.json()
    for client in client_list:
        if client['check']['check_source'] == 'consul':
            consul_clients.append(client['client'])
    return consul_clients

def get_consul_nodes():
    """
    Return a list of nodes registered in Consul.
    """
    consul_nodes = [ ]
    r = requests.get('{}/v1/catalog/nodes'.format(CONSUL_API))
    for node in r.json():
        consul_nodes.append(node['Node'])
    return consul_nodes

def delete_sensu_client(client):
    """
    Delete a client from Sensu. This would be invoked if the node was deregistered from Consul.
    """
    try:
        delete_client = requests.delete('{}/clients/{}'.format(SENSU_API, client))
    except Exception as e:
        if delete_client.status == 404:
            print('Client {} does not exist in Sensu'.format(client))
        else:
            print('Encountered an issue deleting client: {}'.format(client))
            print(str(e))
    print('Successfully deleted stale client {}'.format(client))

def delete_stale_endpoints():
    """
    If a client exists in Sensu, but was deregistered in Consul, we want to remove it from Sensu.
    In highly-dynamic environments (e.g.: where auto-scaling is implemented), we expect hosts to
    come and go. There's no point keeping a host in Sensu if that host is gone.

    Note: A Sensu client will only be removed if the node no longer exists in Consul. If the host
          is down, we will still monitor - and alert - on that host.
    """
    sensu_clients = get_clients_with_consul_checks()
    consul_nodes = set(get_consul_nodes())
    for client in sensu_clients:
        if client not in consul_nodes:
            delete_sensu_client(client)

def get_consul_services_list():
    """
    Gets a list of services currently registered with Consul.  This list will be used to get a list
    of nodes names, which in turn are used as the client names in Sensu
    """
    r = requests.get('{}/v1/catalog/services'.format(CONSUL_API))
    services = r.json()
    # Consul keeps itself in the list of services. We don't want that service, so we will 'pop' it
    # out of the dictionary, leaving all other services intact.
    services.pop('consul')
    return list(services.keys())

def check_endpoint(endpoint):
    """
    Performs the actual monitoring of the endpoint discovered from Consul. In this example, the
    monitor is intentionally a very simple HTTP check, but you can implement anything you wish,
    including borrowing code and/or ideas from the existing Sensu plugins repos.
    """
    result = { }
    try:
        check_endpoint = requests.get(endpoint)
        if check_endpoint.status_code < 399:
            result['output'] = 'Success! Got HTTP status code {} error trying to connect to endpoint {}'.format(str(check_endpoint.status_code), endpoint)
            result['status'] = 0
    except requests.exceptions.ConnectionError as e:
        result['output'] = 'Problem connecting to {}.\nException details:\n{}'.format(endpoint, str(e))
        result['status'] = 2
    except Exception as e:
        result['output'] = 'Got HTTP status code {} trying to connect to endpoint {}.\nException details:\n{}'.format(str(check_endpoint.status_code), endpoint,str(e))
        result['status'] = 1
    return result

def format_endpoint(data):
    """
    Builds the URL that check_endpoint will check.
    """
    endpoint = 'http://{}:{}'.format(data['Node'], str(data['ServicePort']))
    try:
        if len(data['ServiceMeta']['uri']) > 1:
            # If a URI is specified, let's tack that onto the endpoint
            endpoint = '{}/{}'.format(payload['endpoint'],node['uri'])
    except KeyError:
        # URI not specified, so we'll just stick with http://node:port
        pass
    return endpoint

def check_consul_services():
    """
    This is the main portion of this script. It gets the list of services from Consul, then for each service
    it iterates the list of nodes, gathering the node name, the service port, and other bits needed to do the
    actual monitoring.
    """
    consul_services_list = get_consul_services_list()
    endpointList = [ ]
    for service in consul_services_list:
        # For each of the nodes in this service, assemble a JSON check result payload to ship to Sensu's
        # results API (e.g.: each webserver in the "web-hello-world" Service).
        nodes = requests.get('{}/v1/catalog/service/{}'.format(CONSUL_API, service))
        for node in nodes.json():
            payload = { }
            payload['source'] = node['Node']
            payload['name'] = 'check_http'
            payload['endpoint'] = format_endpoint(node)
            payload['check_source'] = 'consul'
            for k,v in check_endpoint(payload['endpoint']).items():
                # check_endpoint passes back a dict like so: {} "output": "Meaningful text here", "status": [0-3] }.
                # We will map these directly into the output and result fields in JSON payload we'll ship to Sensu.
                payload[k] = v
            try:
                # Teams can optionally specify key/value pairs in the 'meta' section of their service definition.
                # If present, we will map those k/v pairs into the JSON check result payload we'll ship to Sensu.
                # This would allow teams to self-service specifications like a PagerDuty key, handler, etc.
                for k,v in node['ServiceMeta'].items():
                    payload[k] = v
            except Exception as e:
                # The ServiceMeta section is empty. No worries. We just keep on truckin'!
                pass
            # We've now assembled the JSON payload, so send that to Sensu. As an added bonus, if Sensu has
            # never seen this client and/or check before, Sensu will auto-add it for us!
            post_to_sensu(payload)

def post_to_sensu(payload):
    """
    Ships a JSON payload to Sensu's /results API, similarly to how a client would ship to the results queue
    in RMQ. Reference: https://docs.sensu.io/sensu-core/1.1/api/results/#reference-documentation
    """
    headers = { 'Content-Type': 'application/json' }
    try:
        data = json.dumps(payload)
        r = requests.post('{}/results'.format(SENSU_API), headers=headers, data=data, timeout=15, verify=False)
        print('Shipped result to Sensu for client {}'.format(payload['source']))
    except Exception as e:
        if r.status_code > 400:
            print('Problem sending check results to Sensu. HTTP status code {} received from sensu-api with response: {}'.format(str(r.status_code),r.text))
        if len(r.text) < 1:
            print('Nothing returned from POST to Sensu for this payload: {}'.format(payload))

if __name__ == "__main__":
    """
    For demo purposes, we're running this in an infinite loop, but the optimal target use case is a FaaS platform
    such as AWS Lambda. That said, I have run monitors like this as PaaS app (in PCF, specifically) for well over
    a year using this exact same concept.
    """
    while True:
        # We want to remove any Sensu clients that are no longer registered in Consul
        delete_stale_endpoints()
        # Now, we can pull the list of Consul services to determine what to monitor, and finish by shooting
        # the results to Sensu.
        check_consul_services()
        # Aggressive timing for demo purposes. Ideally this would be something more sane like 60 seconds IRL.
        sleep(10)



