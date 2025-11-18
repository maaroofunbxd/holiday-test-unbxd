#!/usr/bin/env python3
"""
Common pre-test setup script for Kubernetes deployments.
Copies configuration from prod deployment to demo deployment.
"""

import subprocess
import json
import sys


# Configuration
deployment_name = "qcs"
container_name = "qcs"
namespace = "ai"
demo_deployment = f"{deployment_name}-demo"


def run_command(cmd, capture_output=True, check=True):
    """Execute a shell command and return the result."""
    print(f"Running: {cmd}")
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=capture_output,
            text=True,
            check=check
        )
    except Exception as e:
        print(e)        

    if capture_output:
        return result.stdout.strip()
    return None


def get_jsonpath(deploy, ns, container, path):
    """Get a value from deployment using jsonpath."""
    jsonpath = f"{{.spec.template.spec.containers[?(@.name=='{container}')].{path}}}"
    cmd = f'kubectl get deploy {deploy} -n {ns} -o jsonpath="{jsonpath}"'
    return run_command(cmd)


def main():
    print("=" * 80)
    print("Pre-Test Setup: Syncing prod to demo deployment")
    print("=" * 80)
    
    # Compare demo and prod deployments (if yaml files exist)
    try:
        run_command("diff demo.yaml prod.yaml", check=False)
    except:
        pass
    
    # Get source image from prod deployment
    print("\n--- Step 1: Syncing Image ---")
    source_image = get_jsonpath(deployment_name, namespace, container_name, "image")
    print(f"SOURCE_IMAGE: {source_image}")
    
    current_image = get_jsonpath(demo_deployment, namespace, container_name, "image")
    print(f"CURRENT_IMAGE: {current_image}")
    
    # Set image on demo deployment
    cmd = f"kubectl set image deployment/{demo_deployment} -n {namespace} {container_name}={source_image}"
    run_command(cmd)
    
    # Copy imagePullPolicy
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
    with open("patch.json", "w") as f:
        json.dump(patch, f)
    cmd = f"kubectl patch deploy {demo_deployment} -n {namespace} --patch-file patch.json"
    run_command(cmd)
    
    # Verify imagePullPolicy
    new_policy = get_jsonpath(demo_deployment, namespace, container_name, "imagePullPolicy")
    print(f"Updated ImagePullPolicy: {new_policy}")
    
    # Extract and copy container config (resources, probes)
    print("\n--- Step 3: Syncing Resources and Probes ---")
    
    # Get full container config from source
    cmd = f"kubectl get deploy {deployment_name} -n {namespace} -o json"
    source_json = run_command(cmd)
    source_data = json.loads(source_json)
    
    # Find the container config
    container_config = None
    for container in source_data['spec']['template']['spec']['containers']:
        if container['name'] == container_name:
            # Extract only the fields we want to copy
            container_config = {
                'name': container['name'],
                'resources': container.get('resources', {}),
                'livenessProbe': container.get('livenessProbe', {}),
                'readinessProbe': container.get('readinessProbe', {})
            }
            break
    
    if not container_config:
        print(f"ERROR: Container {container_name} not found in source deployment")
        sys.exit(1)
    
    # Print current target values
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
    
    # Patch the target deployment
    patch = {
        "spec": {
            "template": {
                "spec": {
                    "containers": [container_config]
                }
            }
        }
    }
    with open("patch.json", "w") as f:
        json.dump(patch, f)

    cmd = f"kubectl patch deploy {demo_deployment} -n {namespace} --patch-file patch.json"
    run_command(cmd)
    
    # Verify updated values
    print("\n---- Updated target values ----")
    for probe in ['livenessProbe', 'readinessProbe', 'resources']:
        value = get_jsonpath(demo_deployment, namespace, container_name, probe)
        print(f"{probe}: {value}")
    
    # Scale replicas
    print("\n--- Step 4: Scaling Replicas ---")
    replicas_jsonpath = "{.spec.replicas}"
    cmd = f"kubectl get deploy {deployment_name} -n {namespace} -o jsonpath='{replicas_jsonpath}'"
    replicas = run_command(cmd)
    print(f"Source replicas: {replicas}")
    
    # Scale demo to 1 replica (can be changed as needed)
    cmd = f"kubectl scale deploy {demo_deployment} -n {namespace} --replicas=1"
    run_command(cmd)
    
    # Annotate the deployment
    cmd = f'kubectl annotate deploy {demo_deployment} -n {namespace} kubernetes.io/change-cause="increased replicas to {replicas}" --overwrite'
    run_command(cmd)
    
    # Restart and monitor rollout
    print("\n--- Step 5: Rolling Restart ---")
    cmd = f"kubectl rollout restart deployment {demo_deployment} -n {namespace}"
    run_command(cmd)
    
    print("\nWaiting for rollout to complete...")
    cmd = f"kubectl rollout status deployment {demo_deployment} -n {namespace}"
    run_command(cmd)
    
    print("\nRollout history:")
    cmd = f"kubectl rollout history deployment {demo_deployment} -n {namespace}"
    run_command(cmd, capture_output=False)
    
    # Final comparison
    print("\n--- Final Comparison ---")
    try:
        run_command("diff demo.yaml prod.yaml", check=False)
    except:
        pass
    
    print("\n" + "=" * 80)
    print("Pre-Test Setup Complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()

