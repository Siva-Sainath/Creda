#!/usr/bin/env python3
"""Deploy Creda multimodal judge on SageMaker JumpStart (Qwen3.5-4B VLM)."""
from __future__ import annotations

import argparse
import os
import time

MODEL_ID = "huggingface-vlm-qwen3-5-4b"
INSTANCE_TYPE = "ml.g5.xlarge"
INFERENCE_AMI = "al2-ami-sagemaker-inference-gpu-3-1"
DEFAULT_ENDPOINT = "creda-qwen-judge"


def _resolve_role_arn(iam) -> str:
    role_name = os.environ.get("SAGEMAKER_ROLE_NAME", "SageMaker-AutoRole-Serving")
    try:
        return iam.get_role(RoleName=role_name)["Role"]["Arn"]
    except iam.exceptions.NoSuchEntityException:
        from sagemaker.core.helper import IamRoleResolver

        role_arn = IamRoleResolver().create_execution_role(role_type="serving")
        print(f"Created serving role {role_arn}")
        return role_arn


def _delete_endpoint(sm, name: str) -> None:
    try:
        sm.describe_endpoint(EndpointName=name)
    except sm.exceptions.ClientError as exc:
        if exc.response["Error"]["Code"] == "ValidationException":
            return
        raise
    print(f"Deleting failed endpoint {name}...")
    sm.delete_endpoint(EndpointName=name)
    while True:
        try:
            sm.describe_endpoint(EndpointName=name)
        except sm.exceptions.ClientError:
            break
        time.sleep(10)
    try:
        sm.delete_endpoint_config(EndpointConfigName=name)
    except sm.exceptions.ClientError:
        pass


def _deploy_v2(endpoint_name: str, instance_type: str, model_id: str, role_arn: str) -> str:
    from sagemaker.jumpstart.model import JumpStartModel

    model = JumpStartModel(model_id=model_id, role=role_arn, instance_type=instance_type)
    predictor = model.deploy(
        endpoint_name=endpoint_name,
        initial_instance_count=1,
        instance_type=instance_type,
        inference_ami_version=INFERENCE_AMI,
        wait=False,
    )
    return predictor.endpoint_name


def _wait_in_service(sm, name: str, timeout_s: int = 2400) -> str:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        desc = sm.describe_endpoint(EndpointName=name)
        status = desc["EndpointStatus"]
        print(f"  status={status}")
        if status == "InService":
            print(f"READY {name}")
            return status
        if status == "Failed":
            reason = desc.get("FailureReason", "endpoint failed")
            raise RuntimeError(reason)
        time.sleep(30)
    raise TimeoutError(f"Endpoint {name} not InService within {timeout_s}s")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint-name", default=os.environ.get("CREDA_SM_ENDPOINT", DEFAULT_ENDPOINT))
    parser.add_argument("--instance-type", default=os.environ.get("CREDA_SM_INSTANCE", INSTANCE_TYPE))
    parser.add_argument("--model-id", default=MODEL_ID)
    parser.add_argument("--force", action="store_true", help="Delete failed endpoint and redeploy")
    parser.add_argument("--no-wait", action="store_true")
    args = parser.parse_args()

    import boto3

    region = os.environ.get("AWS_REGION", "ap-south-1")
    sm = boto3.client("sagemaker", region_name=region)
    try:
        status = sm.describe_endpoint(EndpointName=args.endpoint_name)["EndpointStatus"]
        if status == "InService":
            print(f"Endpoint {args.endpoint_name} already InService")
            return
        if status in {"Creating", "Updating"}:
            if args.force:
                print(f"Force redeploy requested while {status}; waiting then cleaning up")
                try:
                    _wait_in_service(sm, args.endpoint_name, timeout_s=1800)
                    return
                except (RuntimeError, TimeoutError):
                    _delete_endpoint(sm, args.endpoint_name)
            else:
                print(f"Endpoint {args.endpoint_name} is {status}; waiting for completion")
                _wait_in_service(sm, args.endpoint_name)
                return
        if status == "Failed":
            if args.force:
                _delete_endpoint(sm, args.endpoint_name)
            else:
                raise RuntimeError(sm.describe_endpoint(EndpointName=args.endpoint_name).get("FailureReason", "failed"))
    except sm.exceptions.ClientError as exc:
        if exc.response["Error"]["Code"] != "ValidationException":
            raise

    iam = boto3.client("iam", region_name=region)
    role_arn = _resolve_role_arn(iam)
    print(
        f"Deploying JumpStart {args.model_id} -> {args.endpoint_name} "
        f"({args.instance_type}, ami={INFERENCE_AMI})"
    )
    name = _deploy_v2(args.endpoint_name, args.instance_type, args.model_id, role_arn)
    print(f"Deployment started: {name}")
    if not args.no_wait:
        _wait_in_service(sm, name)


if __name__ == "__main__":
    main()
