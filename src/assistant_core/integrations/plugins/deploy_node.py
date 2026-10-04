import time

from common import encryption_service
from common.config import BASE_DIR
from ..base import BaseIntegration
from ..entity_corpus import EntityCorpus


class DeployNodeIntegration(BaseIntegration):

    @property
    def intent_name(self) -> str:
        return "deploy_node"

    @property
    def intent_corpus(self):
        return [
            "разверни новый узел",
            "создай новую ноду",
            "подними vpn сервер",
            "снизь нагрузку на сервера",
            "добавь новый vpn узел"
        ]

    @property
    def entity_corpus(self):
        return [
            EntityCorpus.region,
            EntityCorpus.number,
            EntityCorpus.provider,
            EntityCorpus.vpn_type
        ]

    @property
    def is_long_running(self) -> bool:
        return True

    @property
    def access_level(self) -> int:
        return 10

    def execute(self, entities: dict, context: dict) -> dict:

        required_entities = ["region"]
        for field in required_entities:
            if field not in entities:
                return {
                    "status": "error",
                    "message": f"Отсутствует обязательный параметр: {field}",
                    "stage": "validation"
                }

        deployment_context = {
            "region": entities["region"],
            "node_number": entities.get("number", 1),
            "provider": entities.get("provider", "hetzner"),
            "vpn_type": entities.get("vpn_type", "vless_reality"),
            "secret_key": encryption_service.generate_secret_key()
        }

        node_name = (
            f"{deployment_context['region'].lower()}-"
            f"node-{deployment_context['node_number']}"
        )

        deployment_context["node_name"] = node_name

        try:

            terraform_result = self.run_terraform(
                deployment_context
            )

            if terraform_result["status"] != "success":
                return terraform_result

            ansible_result = self.run_ansible(
                ip=terraform_result["server_ip"],
                deployment_context=deployment_context
            )

            if ansible_result["status"] != "success":
                return ansible_result

            return {
                "status": "success",
                "message": (
                    f"VPN узел {node_name} успешно развернут "
                    f"в регионе {deployment_context['region']}"
                ),
                "server_ip": terraform_result["server_ip"],
                "provider": deployment_context["provider"],
                "vpn_type": deployment_context["vpn_type"],
                "deployment_log": {
                    "terraform": terraform_result,
                    "ansible": ansible_result
                }
            }

        except Exception as e:
            return {
                "status": "error",
                "message": "Ошибка автоматического развертывания узла",
                "raw_log": str(e),
                "stage": "system"
            }

    def run_terraform(self, deployment_context: dict):

        import subprocess
        import json
        import os

        env = os.environ.copy()

        env["TF_VAR_region"] = deployment_context["region"]
        env["TF_VAR_node_name"] = deployment_context["node_name"]

        process = subprocess.run(
            [
                "terraform",
                "apply",
                "-auto-approve"
            ],
            cwd=f"{BASE_DIR}/src/assistant_core/integrations/automation/terraform",
            capture_output=True,
            text=True,
            env=env
        )

        if process.returncode != 0:
            return {
                "status": "error",
                "message": "Terraform deployment failed",
                "stage": "terraform",
                "raw_log": process.stderr
            }

        output_process = subprocess.run(
            [
                "terraform",
                "output",
                "-json"
            ],
            cwd=f"{BASE_DIR}/src/assistant_core/integrations/automation/terraform",
            capture_output=True,
            text=True
        )

        outputs = json.loads(output_process.stdout)

        return {
            "status": "success",
            "server_ip": outputs["server_ip"]["value"],
            "ssh_user": outputs["ssh_user"]["value"]
        }

    def run_ansible(self, ip: str, deployment_context: dict):

        import subprocess

        process = subprocess.run(
            [
                "ansible-playbook",
                f"{BASE_DIR}/src/assistant_core/integrations/automation/ansible/deploy_node.yml",
                "-i",
                f"{ip},",
                "--extra-vars",
                (
                    f"node_name={deployment_context['node_name']} "
                    f"vpn_type={deployment_context['vpn_type']}"
                    f"secret_key={deployment_context['secret_key']}"
                )
            ],
            capture_output=True,
            text=True
        )

        if process.returncode != 0:
            return {
                "status": "error",
                "message": "Ansible deployment failed",
                "stage": "ansible",
                "raw_log": process.stderr
            }

        return {
            "status": "success",
            "raw_log": process.stdout
        }
