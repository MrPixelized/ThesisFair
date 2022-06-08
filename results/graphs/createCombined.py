from io import TextIOWrapper
import os
import requests
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np
from typing import List

prometheus_server = 'http://localhost:8001/api/v1/namespaces/monitoring/services/prometheus-server:80/proxy/api/v1'
service = 'default-service-api-gateway-80@kubernetes'
node = '192.168.1.120:9100'

def getRange(query: str, start: datetime, end: datetime, step: str = '20s'):
  result = requests.get(f'{prometheus_server}/query_range', {
    'query': query,
    'start': start.timestamp(),
    'end': end.timestamp(),
    'step': step,
  }).json()

  if result['status'] != 'success':
    print(result)
    raise BaseException(f'Prometheus status was not succes but was {result["status"]}')

  return result['data']

def makeGraph(query, experiments, output_dir: str= 'out', filename: str = 'out.jpg', ylabel: str = '', xlabel: str = '', process_data: callable = None, process_value: callable = None):
  averages_file = open(os.path.join(output_dir, 'averages.txt'), 'w')
  plt.figure()

  for experiment_name in experiments:
    start = experiments[experiment_name]['start']
    end = experiments[experiment_name]['end']
    name = experiments[experiment_name]['name']

    data = getRange(query, start, end)
    result = data['result']
    if process_data:
      result = process_data(result)

    datapoint_values = []
    for i, result in enumerate(result):
      datapoints = np.array(result['values'], object)
      timestamps = datapoints[:, 0].astype(int) - start.timestamp()
      values = datapoints[:, 1].astype(float)

      if process_value:
        values = process_value(values)

      datapoint_values.append(values)

    datapoint_values = np.array(datapoint_values).sum(axis=0)
    plt.plot(timestamps, datapoint_values, label=name)
    print(f'{name} average value for {name}: {datapoint_values.mean()}', file=averages_file)

  plt.legend()
  plt.ylabel(ylabel)
  plt.xlabel(xlabel)
  plt.savefig(os.path.join(output_dir, filename))
  plt.close()
  averages_file.close()

def makeResults(experiments, output_dir: str = 'out'):
  if not os.path.isdir(f'./{output_dir}'):
    os.mkdir(f'./{output_dir}')

  # Traefik
  makeGraph('sum(rate(traefik_service_requests_total{ code="200" }[20s]))', experiments,
    ylabel = 'Requests per second',
    xlabel='Time since experiment start (seconds)',
    filename = 'requests_per_second.jpg',
    output_dir= output_dir
  )

  makeGraph('sum(rate(traefik_service_requests_total{ code!="200" }[20s]))', experiments,
    ylabel = 'Errors per second',
    xlabel='Time since experiment start (seconds)',
    filename = 'errors_per_second.jpg',
    output_dir= output_dir
  )

  # makeGraph(f'sum(traefik_service_request_duration_seconds_bucket{{service="{service}"}}) by (le) / scalar(sum(traefik_service_request_duration_seconds_count{{service="{service}"}}) by (service))', experiments,
  #   ylabel = 'Percentage of requests',
  #   xlabel='Time since experiment start (seconds)',
  #   filename = 'response_time.jpg',
  #   process_data= lambda data: [datapoints for datapoints in data if datapoints['metric']['le'] != '+Inf'],
  #   process_value= lambda values: values * 100,
  # )

  makeGraph(f'sum(traefik_service_request_duration_seconds_sum{{service="{service}"}}) / sum(traefik_service_requests_total{{service="{service}"}}) * 1000', experiments,
    ylabel = 'API Response time (ms)',
    xlabel='Time since experiment start (seconds)',
    filename = 'API_response_time.jpg',
    output_dir= output_dir
  )


  # # Kubernetes
  makeGraph('count(kube_pod_container_status_ready{ namespace="default", container=~"api-gateway|.+-service" }) by (container)', experiments,
    ylabel = 'Service instances',
    xlabel='Time since experiment start (seconds)',
    filename = 'service_instences_per_service.jpg',
    output_dir= output_dir
  )


  # # Node
  makeGraph(f'sum by (instance)(rate(node_cpu_seconds_total{{ mode="idle", instance="{node}"}}[20s])) * 100', experiments,
    ylabel = 'CPU usage percentage',
    xlabel='Time since experiment start (seconds)',
    filename = 'CPU_usage.jpg',
    process_value= lambda values: 100 - values / 8,
    output_dir= output_dir
  ) # Calculate average performance gain per extra CPU

  makeGraph(f'node_memory_MemTotal_bytes{{instance="{node}"}} - node_memory_MemFree_bytes{{instance="{node}"}}', experiments,
    ylabel = 'Memory usage (GiB)',
    xlabel='Time since experiment start (seconds)',
    filename = 'RAM_usage.jpg',
    process_value= lambda values: values * 9.31322575e-10,
    output_dir= output_dir
  )

  # # RabbitMQ
  rabbitmq_experiments = {}
  for exp in experiments:
    if experiments[exp]['rabbitmq']:
      rabbitmq_experiments[exp] = experiments[exp]
  makeGraph('sum(rabbitmq_queue_messages_ready * on(instance) group_left(rabbitmq_cluster, rabbitmq_node) rabbitmq_identity_info{rabbitmq_cluster="rabbitmq", namespace="default"}) by(rabbitmq_node)',
    rabbitmq_experiments,
    ylabel = 'Queued messages',
    xlabel='Time since experiment start (seconds)',
    filename = 'RabbitMQ_queue.jpg',
    output_dir= output_dir
  )

if __name__ == '__main__':
  baseLoad = {
    'ThesisFair BaseArchitectureScalabilityImproved - 1 4 50 2 2 8': {
      'start': datetime(2022, 6, 7, 10, 26, 00),
      'end': datetime(2022, 6, 7, 10, 56, 00),
      'rabbitmq': True,
      'name': 'base 1x'
    },
    'ThesisFair httpCommunication1x - 1 4 50 2 2 8': {
      'start': datetime(2022, 6, 7, 13, 36, 00),
      'end': datetime(2022, 6, 7, 14, 6, 00),
      'rabbitmq': False,
      'name': 'http 1x'
    },

  }

  twoLoad = {
    'ThesisFair BaseArchitectureScalabilityImproved2x - 1 4 100 4 2 8': {
      'start': datetime(2022, 6, 7, 11, 28, 00),
      'end': datetime(2022, 6, 7, 11, 58, 00),
      'rabbitmq': True,
      'name': 'base 2x'
    },
    'ThesisFair httpCommunication2x - 1 4 100 4 2 8': {
      'start': datetime(2022, 6, 7, 14, 30, 00),
      'end': datetime(2022, 6, 7, 15, 00, 00),
      'rabbitmq': False,
      'name': 'http 2x'
    },
  }

  threeLoad = {
    'ThesisFair BaseArchitectureScalabilityImproved3x - 1 4 150 6 2 8': {
      'start': datetime(2022, 6, 7, 12, 25, 00),
      'end': datetime(2022, 6, 7, 12, 55, 00),
      'rabbitmq': True,
      'name': 'base 3x'
    },
    'ThesisFair httpCommunication3x - 1 4 150 6 2 8': {
      'start': datetime(2022, 6, 7, 15, 5, 00),
      'end': datetime(2022, 6, 7, 15, 35, 00),
      'rabbitmq': False,
      'name': 'http 3x'
    },
  }

  makeResults(baseLoad, '1xLoad')
  makeResults(twoLoad, '2xLoad')
  makeResults(threeLoad, '3xLoad')
