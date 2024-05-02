import kopf
from kubernetes import client, config
import logging 
import traceback
import time
import random

config.load_kube_config()
api = client.AppsV1Api()
v1 = client.CoreV1Api()
custom_api = client.CustomObjectsApi()
batch_api = client.BatchV1Api()

def create_pvcs(pv_name,pvc_name, volume_path, namespace):
    print('Creating volumes with function')
    persisten_volume_body = {
        "apiVersion": "v1",
        "kind": "PersistentVolume",
        "metadata": {
            "name": pv_name
        },
        "spec": {
            "storageClassName": "manual",
            "capacity": {
                "storage": "3Gi"
            },
            "accessModes": [
                "ReadWriteOnce"
            ],
            "hostPath": {
                "path": volume_path
            }
        }
    }
    persisten_volume_claim_body = {
        "apiVersion": "v1",
        "kind": "PersistentVolumeClaim",
        "metadata": {
            "name": pvc_name,
            "namespace": namespace
        },
        "spec": {
            "storageClassName": "manual",
            "resources": {
                "requests": {
                    "storage": "3Gi"
                }
            },
            "accessModes": [
                "ReadWriteOnce"
            ]
        }
    }
    # Create Persistent volume for flower client
    try:
        v1.create_persistent_volume(body=persisten_volume_body)
    except Exception as e:
        logging.error(f"Error creating persistent volume. Reason: {e}")
        pass

    # Create Persistent volume claim for flower client
    try:
        v1.create_namespaced_persistent_volume_claim(
            namespace=namespace,
            body=persisten_volume_claim_body
        )
    except Exception as e:
        logging.error(f"Error creating persistent volume claim. Reason: {e}")
        pass


@kopf.on.create('flwr.dev', 'v1', 'fldeployments')
def create_fldeployment(spec, **kwargs):
    start_time = time.time()
    server_spec = spec.get('server', {})
    server_data = {
        "server_default_ip_nw1": "10.18.1.3",
        "server_default_ip_nw2": "10.18.1.21",
        "server_default_ip_nw3": "10.18.1.34",
        "server_default_ip_nw4": "10.18.1.50",
        "server_default_ip_nw5": "10.18.1.67",
        "server_default_ip_nw6": "10.18.1.83",
        "server_default_ip_nw7": "10.18.1.99",
        "server_default_ip_nw8": "10.18.1.115",
        "server_default_ip_nw9": "10.18.1.131",
        "server_default_ip_nw10": "10.18.1.147",
    }   
    server_image = server_spec.get('image', 'juanmarcelouob/kubeflower:dp')
    server_image_pull_policy = server_spec.get('imagePullPolicy', 'IfNotPresent')
    server_port = server_spec.get('port', 8080)
    server_replicas = server_spec.get('replicas', 1)
    server_node_name = server_spec.get('nodeName', 'worker3')
    server_min_clients = server_spec.get('minClients', 2)
    server_rounds = server_spec.get('rounds', 5)
    #########POTENTIALLY MAKE THE SERVER TO ORCHESTRATE THE PRIVACY BUDGET- FA TO KEEP TRACK OF THE BUDGET
    client_spec = spec.get('client', {})
    client_image = client_spec.get('image', 'juanmarcelouob/kubeflower:dp')
    client_image_pull_policy = client_spec.get('imagePullPolicy', 'IfNotPresent')
    print("image policy:::::::::",server_image_pull_policy)
    client_port = client_spec.get('port', 30050)
    client_node_name = server_spec.get('nodeName', 'worker2')
    client_num_clients= client_spec.get('num_clients', 2)
    client_isolation = client_spec.get('isolation', True)
    client_args = client_spec.get('args', [])
    client_dataset = client_spec.get('dataset', {})
    client_dataset_path = client_dataset.get('path', '/home/ubuntu/kubeFlower-Operator/data')
    client_dataset_download = client_dataset.get('download', True)
    client_privacy = client_spec.get('privacy', {})
    if len(client_privacy) == 0:
        print("You haven't add privacy values")
        dp_process = False
    else:
        client_privacy_budget = client_privacy.get('budget', 1.0)
        client_privacy_rate = client_privacy.get('rate',1.0)
        print(f"You have add privacy values budget is {client_privacy_budget}")
        dp_process = True
    
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~Server deployment 
    server_deployment_body = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": f"{kwargs['body']['metadata']['name']}-server",
            "namespace": kwargs['body']['metadata']['namespace'],
            "finalizers":[],
        },
        "spec": {
            "replicas": server_replicas,
            "selector": {
                "matchLabels": {
                    "app": f"{kwargs['body']['metadata']['name']}-server"
                }
            },
            "template": {
                "metadata": {
                    "labels": {
                        "app": f"{kwargs['body']['metadata']['name']}-server"
                    },
                    "annotations": {
                        "k8s.v1.cni.cncf.io/networks": "default/nw2, default/nw3, default/nw4, default/nw5, default/nw6, default/nw7, default/nw8, default/nw9, default/nw10",
                        "ovn.kubernetes.io/logical_switch": "nw1",
                        "ovn.kubernetes.io/ip_address": server_data.get("server_default_ip_nw1"),
                        "nw2.default.ovn.kubernetes.io/logical_switch": "nw2",
                        "nw2.default.ovn.kubernetes.io/ip_address": server_data.get("server_default_ip_nw2"),
                        "nw3.default.ovn.kubernetes.io/logical_switch": "nw3",
                        "nw3.default.ovn.kubernetes.io/ip_address": server_data.get("server_default_ip_nw3"),
                        "nw4.default.ovn.kubernetes.io/logical_switch": "nw4",
                        "nw4.default.ovn.kubernetes.io/ip_address": server_data.get("server_default_ip_nw4"),
                        "nw5.default.ovn.kubernetes.io/logical_switch": "nw5",
                        "nw5.default.ovn.kubernetes.io/ip_address": server_data.get("server_default_ip_nw5"),
                        "nw6.default.ovn.kubernetes.io/logical_switch": "nw6",
                        "nw6.default.ovn.kubernetes.io/ip_address": server_data.get("server_default_ip_nw6"),
                        "nw7.default.ovn.kubernetes.io/logical_switch": "nw7",
                        "nw7.default.ovn.kubernetes.io/ip_address": server_data.get("server_default_ip_nw7"),
                        "nw8.default.ovn.kubernetes.io/logical_switch": "nw8",
                        "nw8.default.ovn.kubernetes.io/ip_address": server_data.get("server_default_ip_nw8"),
                        "nw9.default.ovn.kubernetes.io/logical_switch": "nw9",
                        "nw9.default.ovn.kubernetes.io/ip_address": server_data.get("server_default_ip_nw9"),
                        "nw10.default.ovn.kubernetes.io/logical_switch": "nw10",
                        "nw10.default.ovn.kubernetes.io/ip_address": server_data.get("server_default_ip_nw10"),                    
                    }
                },
                "spec": {
                    #"nodeName": server_node_name,
                    "containers": [
                        {
                            "name": "fl-server",
                            "image": server_image,
                            "imagePullPolicy": server_image_pull_policy,
                            "command": ["/bin/sh", "-c"],
                            "args": [f"ls; python ./src/server.py --min {server_min_clients} --rounds {server_rounds}"],
                            "ports": [
                                {
                                    "containerPort": server_port
                                }
                            ]
                        }
                    ]
                }
            }
        }
    }
    #Create Flower server
    try:        
        api.create_namespaced_deployment(
            namespace=kwargs['body']['metadata']['namespace'],
            body=server_deployment_body
        )
    except Exception as e:
        logging.error(f"Error creating {kwargs['body']['metadata']['name']}-server. Reason: {e}")
        pass
    logging.info("Waiting for server to be deployed...")
    time.sleep(1)
    label_selector = f"app={kwargs['body']['metadata']['name']}-server"
    server_pods = v1.list_namespaced_pod(namespace=kwargs['body']['metadata']['namespace'], label_selector=label_selector)
    server_pod_name = ''
    for pod in server_pods.items:
        pod_name = pod.metadata.name
        server_pod_name = pod_name
        print(pod_name)
        print(f"Pod Status: {pod.status.phase}")
    #time.sleep(40)
    while True:
        try:
            # Get the pod status
            pod = v1.read_namespaced_pod(server_pod_name, kwargs['body']['metadata']['namespace'])
            pod_status = pod.status.phase
            # Check if the Pod is running
            if  pod_status == "Running":
                print(f"Server running {pod.metadata.name}")
                break  # Exit the loop since the server pod has run
            else:
                #print(f"Job {job_name} is still running. Waiting...")
                pass
        except client.exceptions.ApiException as e:
            print(f"Exception when calling read_namespaced_pob_status: {e}")
                # Wait for a few seconds before checking the status again
        time.sleep(1)
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~Client deployment
    logging.info(f"Deploying {client_num_clients} number of FL clients")
    client_dataset_path_run = "./data/normal/"
    custom_dataset = True
    dp_dataset = False
    for i in range(client_num_clients):
        i = i+1
        server_ip_label = f"server_default_ip_nw{i}"
        server_ip = server_data.get(server_ip_label)
        client_namespace = kwargs['body']['metadata']['namespace']
        client_network = f"nw{i}" if client_isolation else "default"
        ##Add differential privacy if required 
        if dp_process:
            logging.info(f"Deploying job {i}")
            job_name = f"diffpriv-job-{i}"
            job_deployment_body = {
                "apiVersion": "batch/v1",
                "kind": "Job",
                "metadata": {
                    "name": job_name,
                },
                "spec": {
                    "backoffLimit": 0,
                    "template": {
                        "spec": {
                            "containers": [
                                {
                                "name": "dp-claimer",
                                "image": client_image,
                                "imagePullPolicy": client_image_pull_policy,
                                "resources": {
                                    "requests": {
                                        "memory": "3Gi",
                                        "cpu": "3"
                                    },
                                    "limits": {
                                        "memory": "7Gi",
                                        "cpu": "6"
                                    }
                                },
                                "command": ["/bin/sh", "-c"],
                                "args": [f"ls; cd data; ls normal/; cd ..; python ./src/dp_vol_claimer.py"],
                                "volumeMounts": [
                                    {
                                        "name": f"diffpriv-job-pv-{i}",  # Volume name
                                        "mountPath": "/app/data/",  # Mount path in the container
                                    }
                                    ]
                                }
                            ],
                            "volumes": [
                                {
                                    "name": f"diffpriv-job-pv-{i}",  # Volume name
                                    "persistentVolumeClaim": {
                                        "claimName": f"diffpriv-job-pvc-{i}",  # Name of the PVC
                                    }
                                }
                            ],
                            "restartPolicy": "Never"
                            }
                        }
                    }
                }
            #Create PV and PVC for the job
            try:
                create_pvcs(f"diffpriv-job-pv-{i}", f"diffpriv-job-pvc-{i}", client_dataset_path, client_namespace)
            except Exception as e:
                logging.error(f"Error creating diffpriv-job-pv and pvc-{i}. Reason: {e}")
                pass
            #Create DP job
            try:
                batch_api.create_namespaced_job(
                    namespace=client_namespace,
                    body=job_deployment_body
                )
            except Exception as e:
                logging.error(f"Error creating {kwargs['body']['metadata']['name']}-job {i}. Reason: {e}")
                pass

            while True:
                try:
                    # Get the Job status
                    job_status = batch_api.read_namespaced_job_status(name=job_name, namespace=client_namespace)
                    # Check if the Job has finished
                    if job_status.status.succeeded is not None:
                        print(f"Job {job_name} has succesfully finished with exit code {job_status.status.succeeded}")
                        break  # Exit the loop since the Job has finished
                    elif job_status.status.failed is not None:
                        print(f"Job {job_name} has failed with exit code {job_status.status.failed}")
                        break  # Exit the loop since the Job has failed
                    else:
                        #print(f"Job {job_name} is still running. Waiting...")
                        pass
                except client.exceptions.ApiException as e:
                    print(f"Exception when calling BatchV1Api->read_namespaced_job_status: {e}")
                # Wait for a few seconds before checking the status again
                time.sleep(1)
            client_dataset_path_run = "./data/dp/"
            dp_dataset = True
        logging.info(f"Deploying client {i} with dataset {client_dataset_path_run}, custom {custom_dataset} and dp: {dp_dataset}")        
        client_deployment_body = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "finalizers":{},
            "metadata": {
                "name": f"{kwargs['body']['metadata']['name']}-client-{i}",
                "namespace": kwargs['body']['metadata']['namespace'],
                "finalizers":[]
            },
            "spec": {
                "replicas": 1,
                "selector": {
                    "matchLabels": {
                        "app": f"{kwargs['body']['metadata']['name']}-client-{i}"
                    }    
                },
                "template": {
                    "metadata": {
                        "labels": {
                            "app": f"{kwargs['body']['metadata']['name']}-client-{i}"
                        },
                        "annotations": {
                            "ovn.kubernetes.io/logical_switch": client_network                      
                        }           
                    },
                    "spec": {
                        #"nodeName": f'worker{random.randint(1, 3)}',
                        "containers": [
                            {
                                "name": "fl-client",
                                "image": client_image,
                                "imagePullPolicy": client_image_pull_policy,
                                "command": ["/bin/sh", "-c"],
                                "args": [f"ls; cd data; ls; cd ..; python ./src/client.py --server {server_ip} --port {server_port} --download {client_dataset_download} --data {client_dataset_path_run} --custom {custom_dataset} --dp {dp_dataset}"],
                                "ports": [
                                    {
                                        "containerPort": server_port
                                    }
                                ],
                            }
                        ],
                    }
                }
            }
        }
        #Create PV and PVCs if the user wants to load data from dataset.path. They have to be created before the deployment/pod that is going to consume them
        if not client_dataset_download:
            logging.info(f'Creating PV and PVC for {i}')
            #Configuring the client descriptor to add the volume claims info. 
            valuesVolumeMounts = [
                                    {
                                        "name": f"my-volume-{i}",
                                        "mountPath": "/app/data/"
                                    }
                                ]
            valuesVolumes = [
                            {
                                "name": f"my-volume-{i}",
                                "persistentVolumeClaim": {
                                    "claimName": f"{kwargs['body']['metadata']['name']}-client-pvc-{i}"
                                }
                            }
                        ]
            client_deployment_body.get('spec').get('template').get('spec').get('containers')[0]['volumeMounts'] = valuesVolumeMounts
            client_deployment_body.get('spec').get('template').get('spec')['volumes'] = valuesVolumes    
            #Create PV and PVC for the job
            try:
                create_pvcs(f"{kwargs['body']['metadata']['name']}-client-pv-{i}", f"{kwargs['body']['metadata']['name']}-client-pvc-{i}", client_dataset_path, client_namespace)
            except Exception as e:
                logging.error(f"{kwargs['body']['metadata']['name']}-client-pv and pvc-{i}. Reason: {e}")
                pass
        #Create Flower client
        try:
            api.create_namespaced_deployment(
                namespace=kwargs['body']['metadata']['namespace'],
                body=client_deployment_body
            )
        except Exception as e:
            logging.error(f"Error creating {kwargs['body']['metadata']['name']}-client. Reason: {e}")
            pass
    end_time = time.time()
    elapsed_time = end_time - start_time
    logging.info(f"Total deployment time {elapsed_time}")
@kopf.on.delete('flwr.dev', 'v1', 'fldeployments')    
def delete_fldeployment(body, **kwargs):
    namespace = body['metadata']['namespace']
    server_deployment_name = f"{body['metadata']['name']}-server"
    client_deployment_name = f"{body['metadata']['name']}-client"
    number_of_clients = body['spec']['client']['num_clients']
    persisten_volume_name = f"{body['metadata']['name']}-client-pv"
    persisten_volume_claim_name = f"{body['metadata']['name']}-client-pvc"
    try:
        api.delete_namespaced_deployment(
            name=server_deployment_name,
            namespace=namespace,
            body=client.V1DeleteOptions(),
        )
    except Exception as e:
        logging.error(f"Error deleting server. Reason: {e}")
        pass
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~Delete Clients
    for i in range(number_of_clients):
        i = i+1
        try: 
            api.delete_namespaced_deployment(
                name=f'{client_deployment_name}-{i}',
                namespace=namespace,
                body=client.V1DeleteOptions(),
            )
        except Exception as e:
            logging.error(f"Error deleting client. Reason: {e}")
            pass


        try:        
            v1.delete_namespaced_persistent_volume_claim(
                name=f'{persisten_volume_claim_name}-{i}',
                namespace=namespace,
                body=client.V1DeleteOptions()
            )
        except Exception as e:
            logging.error(f"Error deleting pvc. Reason: {e}")
            pass

        try:
            v1.delete_persistent_volume(
                name=f'{persisten_volume_name}-{i}',
                body=client.V1DeleteOptions()
            )
        except Exception as e:
            logging.error(f"Error deleting pv. Reason: {e}")
            pass
        try:
            job_name = f"diffpriv-job-{i}"
            batch_api.delete_namespaced_job(
                name=job_name,
                namespace=namespace,
                body=client.V1DeleteOptions(),
            )
        except Exception as e:
            logging.error(f"Error deleting job {i}. Reason: {e}")
            pass

    # Define the field selector for Pods with status.phase==Succeeded
    field_selector = "job"
    try:
    # List Pods in the specified namespace matching the field selector
        pods = v1.list_namespaced_pod(namespace)
        # Iterate through the matching Pods and delete them
        for pod in pods.items:
            pod_name = pod.metadata.name
            if field_selector in str(pod_name):
                v1.delete_namespaced_pod(name=pod_name, namespace=namespace)
                print(f"Deleted Job: {pod_name}")
    except client.exceptions.ApiException as e:
        print(f"Exception when calling CoreV1Api->list_namespaced_pod: {e}") 
    ##Delete PVCs       
    try:
    # List all Persistent Volumes Claims
        pvc_list = v1.list_persistent_volume_claim_for_all_namespaces()
        for pvc in pvc_list.items:
            print(f"Deleting PVC: {pvc.metadata.name}")
            try:
            # Delete the Persistent Volume Claims
                v1.delete_namespaced_persistent_volume_claim(
                name=pvc.metadata.name,
                namespace=pvc.metadata.namespace
            )
            except client.exceptions.ApiException as e:
                print(f"Error deleting PVC {pvc.metadata.name}: {e}")
    except client.exceptions.ApiException as e:
        print(f"Error listing PVCs: {e}")
    ##Delete PVs       
    try:
    # List all Persistent Volumes
        pv_list = v1.list_persistent_volume()
        for pv in pv_list.items:
            print(f"Deleting PV: {pv.metadata.name}")
            try:
            # Delete the Persistent Volume
                v1.delete_persistent_volume(name=pv.metadata.name)
            except client.exceptions.ApiException as e:
                print(f"Error deleting PV {pv.metadata.name}: {e}")
    except client.exceptions.ApiException as e:
        print(f"Error listing PVs: {e}")
    ##Delete the CRD object
    try:    
        custom_api.delete_namespaced_custom_object(
            group="flwr.dev",
            version="v1",
            namespace=namespace,
            plural="fldeployments",
            name=body['metadata']['name'],
            body=client.V1DeleteOptions(),
        )
    except Exception as e:
        logging.error(traceback)
        pass
    