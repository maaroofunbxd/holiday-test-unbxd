#!/usr/bin/env python3
"""
Common pre-test setup script for Kubernetes deployments.
Copies configuration from prod deployment to demo deployment.
"""

import argparse
import copy
import json
import os
import subprocess
import sys


def parse_args():
    parser = argparse.ArgumentParser(description="Sync prod deployment onto demo for holiday tests")
    parser.add_argument("--service", help="Catalog service id (qcs, ner, reranker, ...)")
    parser.add_argument("--deployment", help="Prod deployment name")
    parser.add_argument("--demo-deployment", help="Demo deployment name")
    parser.add_argument("--container", help="Container to copy (default: all catalog containers)")
    parser.add_argument("--namespace")
    parser.add_argument("--replicas", type=int, default=1)
    return parser.parse_args()


def load_from_catalog(service_id):
    try:
        from services import get_service
        return get_service(service_id)
    except Exception as exc:
        print(f"WARNING: catalog lookup failed for {service_id}: {exc}")
        return {}


def run_command(cmd, capture_output=True, check=True, input_data=None):
    """Execute a shell command and return the result."""
    print(f"Running: {cmd}")
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=capture_output,
            text=True,
            check=check,
            input=input_data
        )
        if result.stderr and result.stderr.strip():
            print(f"STDERR: {result.stderr}")
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Command failed with exit code {e.returncode}")
        if e.stderr:
            print(f"STDERR: {e.stderr}")
        if e.stdout:
            print(f"STDOUT: {e.stdout}")
        raise

    if capture_output:
        return result.stdout.strip()
    return None


def get_jsonpath(deploy, ns, container, path):
    """Get a value from deployment using jsonpath."""
    jsonpath = f"{{.spec.template.spec.containers[?(@.name=='{container}')].{path}}}"
    cmd = f'kubectl get deploy {deploy} -n {ns} -o jsonpath="{jsonpath}"'
    return run_command(cmd)


def kubectl_patch(deploy, ns, patch_dict):
    """Apply a patch to a deployment using stdin to avoid quoting issues."""
    patch_json = json.dumps(patch_dict)
    cmd = f"kubectl patch deploy {deploy} -n {ns} --type strategic --patch-file /dev/stdin"
    return run_command(cmd, input_data=patch_json)


def clean_probe(probe):
    """Clean probe config to have only one handler type.
    Kubernetes allows only one of: exec, httpGet, tcpSocket, grpc
    Sets unused handlers to None for strategic merge to remove them."""
    if not probe:
        return probe
    
    # Make a deep copy to avoid modifying original
    import copy
    cleaned = copy.deepcopy(probe)
    
    # Handler types in priority order
    handler_types = ['httpGet', 'tcpSocket', 'exec', 'grpc']
    
    # Find which handler types are present
    present_handlers = [h for h in handler_types if h in cleaned and cleaned[h]]
    
    if len(present_handlers) > 1:
        # Keep only the first one (highest priority)
        keeper = present_handlers[0]
        print(f"  Multiple handlers detected: {present_handlers}")
        print(f"  Keeping '{keeper}' and removing others")
        for handler in present_handlers[1:]:
            del cleaned[handler]
    
    # Set all other handler types to None to explicitly remove them during merge
    if present_handlers:
        keeper = present_handlers[0]
        for handler in handler_types:
            if handler != keeper:
                cleaned[handler] = None
    
    return cleaned


def main():
    args = parse_args()
    catalog = load_from_catalog(args.service) if args.service else {}

    deployment_name = args.deployment or catalog.get("prod_deployment") or "qcs"
    demo_deployment = args.demo_deployment or catalog.get("demo_deployment") or f"{deployment_name}-demo"
    namespace = args.namespace or catalog.get("namespace") or "ai"
    replica_count = args.replicas if args.replicas is not None else int(catalog.get("demo_replicas") or 1)

    if args.container:
        containers = [args.container]
    elif catalog.get("containers"):
        containers = list(catalog["containers"])
    else:
        containers = [deployment_name]

    print("=" * 80)
    print("Pre-Test Setup: Syncing prod to demo deployment")
    print(f"  prod={deployment_name} demo={demo_deployment} ns={namespace} containers={containers}")
    print("=" * 80)

    try:
        run_command(f"kubectl get deploy {demo_deployment} -n{namespace} -oyaml > demo.yaml")
        run_command(f"kubectl get deploy {deployment_name} -n{namespace} -oyaml > prod.yaml")
        run_command("diff demo.yaml prod.yaml", check=False)
    except Exception:
        pass

    for container_name in containers:
        sync_container(deployment_name, demo_deployment, namespace, container_name)

    print("\n--- Step 4: Scaling Replicas ---")
    replicas_jsonpath = "{.spec.replicas}"
    cmd = f"kubectl get deploy {deployment_name} -n {namespace} -o jsonpath='{replicas_jsonpath}'"
    replicas = run_command(cmd)
    print(f"Source replicas: {replicas}; demo target: {replica_count}")

    cmd = f"kubectl scale deploy {demo_deployment} -n {namespace} --replicas={replica_count}"
    run_command(cmd)

    cmd = f'kubectl annotate deploy {demo_deployment} -n {namespace} kubernetes.io/change-cause="holiday pre-test sync from {deployment_name}" --overwrite'
    run_command(cmd)

    print("\n--- Step 5: Rolling Restart ---")
    cmd = f"kubectl rollout restart deployment {demo_deployment} -n {namespace}"
    run_command(cmd)

    print("\nWaiting for rollout to complete...")
    cmd = f"kubectl rollout status deployment {demo_deployment} -n {namespace}"
    run_command(cmd)

    print("\nRollout history:")
    cmd = f"kubectl rollout history deployment {demo_deployment} -n {namespace}"
    run_command(cmd, capture_output=False)

    print("\n--- Final Comparison ---")
    try:
        run_command("diff demo.yaml prod.yaml", check=False)
    except Exception:
        pass

    print("\n" + "=" * 80)
    print("Pre-Test Setup Complete!")
    print("=" * 80)


def sync_container(deployment_name, demo_deployment, namespace, container_name):
    print(f"\n=== Container: {container_name} ===")
    print("\n--- Step 1: Syncing Image ---")
    source_image = get_jsonpath(deployment_name, namespace, container_name, "image")
    print(f"SOURCE_IMAGE: {source_image}")

    current_image = get_jsonpath(demo_deployment, namespace, container_name, "image")
    print(f"CURRENT_IMAGE: {current_image}")

    cmd = f"kubectl set image deployment/{demo_deployment} -n {namespace} {container_name}={source_image}"
    run_command(cmd)

    print("\n--- Step 2: Syncing ImagePullPolicy ---")
    policy = get_jsonpath(deployment_name, namespace, container_name, "imagePullPolicy")
    print(f"ImagePullPolicy: {policy}")

    patch = {
        "spec": {
            "template": {
                "spec": {
                    "containers": [{
                        "name": container_name,
                        "imagePullPolicy": policy
                    }]
                }
            }
        }
    }
    kubectl_patch(demo_deployment, namespace, patch)

    new_policy = get_jsonpath(demo_deployment, namespace, container_name, "imagePullPolicy")
    print(f"Updated ImagePullPolicy: {new_policy}")

    print("\n--- Step 3: Syncing Resources and Probes ---")
    cmd = f"kubectl get deploy {deployment_name} -n {namespace} -o json"
    source_json = run_command(cmd)
    source_data = json.loads(source_json)

    container_config = None
    for container in source_data['spec']['template']['spec']['containers']:
        if container['name'] == container_name:
            liveness = container.get('livenessProbe', {})
            readiness = container.get('readinessProbe', {})
            if liveness:
                print("Cleaning livenessProbe...")
                liveness = clean_probe(liveness)
            if readiness:
                print("Cleaning readinessProbe...")
                readiness = clean_probe(readiness)
            container_config = {
                'name': container['name'],
                'resources': container.get('resources', {}),
                'livenessProbe': liveness,
                'readinessProbe': readiness
            }
            break

    if not container_config:
        print(f"ERROR: Container {container_name} not found in source deployment")
        sys.exit(1)

    print("\n---- Current target values ----")
    cmd = f"kubectl get deploy {demo_deployment} -n {namespace} -o json"
    target_json = run_command(cmd)
    target_data = json.loads(target_json)

    for container in target_data['spec']['template']['spec']['containers']:
        if container['name'] == container_name:
            print(json.dumps({
                'name': container['name'],
                'resources': container.get('resources', {}),
                'livenessProbe': container.get('livenessProbe', {}),
                'readinessProbe': container.get('readinessProbe', {})
            }, indent=2))
            break

    patch = {
        "spec": {
            "template": {
                "spec": {
                    "containers": [container_config]
                }
            }
        }
    }
    kubectl_patch(demo_deployment, namespace, patch)

    print("\n---- Updated target values ----")
    for probe in ['livenessProbe', 'readinessProbe', 'resources']:
        value = get_jsonpath(demo_deployment, namespace, container_name, probe)
        print(f"{probe}: {value}")


if __name__ == "__main__":
    main()

