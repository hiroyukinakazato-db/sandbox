from databricks.sdk import WorkspaceClient
from databricks.sdk.errors.platform import BadRequest
from databricks.labs.blueprint.tui import Prompts
from databricks.labs.lsql.core import StatementExecutionExt
from databricks.sdk.service.compute import DataSecurityMode
from databricks.sdk.service.jobs import (
    Task,
    NotebookTask,
    TaskDependency,
    ForEachTask,
    JobCluster,
    JobParameterDefinition,
)
from databricks.sdk.service import jobs, compute
import os

"""
Approach

User first sets all configuration options
validate options
validate user permissions
then create infra
upload app file to databricks

"""


class JobsInfra:
    def __init__(
        self,
        config,
        workspace_client: WorkspaceClient,
    ):
        self.w = workspace_client
        self.config = config

        self.spark_version = "15.4.x-scala2.12"
        self.node_types = {
            "azure": "Standard_DS3_v2",
            "aws": "m5d.xlarge",
        }
        self.cloud = self._get_cloud()
        self.job_clusters = [
            JobCluster(
                job_cluster_key="sql_migration_job_cluster",
                new_cluster=compute.ClusterSpec(
                    spark_version=self.spark_version,
                    data_security_mode=DataSecurityMode.SINGLE_USER,
                    # spark_conf = {
                    #     "spark.databricks.cluster.profile": "singleNode",
                    #     "spark.master": "local[*]",
                    # },
                    num_workers=1,
                    node_type_id=self.node_types[self.cloud],
                ),
            )
        ]

        self.job_name = "sql_migration_code_transformation"
        self.notebook_root_path = f"/Workspace/Users/{self.w.current_user.me().user_name}/.sql_migration_assistant/jobs/"
        self.job_parameters = [
            JobParameterDefinition("agent_configs", ""),
            JobParameterDefinition("app_configs", ""),
        ]
        self.job_tasks = [
            Task(
                task_key="legion_sql2dbx_runner",
                notebook_task=NotebookTask(
                    notebook_path=self.notebook_root_path + "legion_sql2dbx_runner"
                ),
                job_cluster_key="sql_migration_job_cluster",
            ),
        ]

    def create_transformation_job(self):
        job_id = self.w.jobs.create(
            name=self.job_name,
            tasks=self.job_tasks,
            job_clusters=self.job_clusters,
            parameters=self.job_parameters,
        )
        self.config["TRANSFORMATION_JOB_ID"] = job_id.job_id

    def _get_cloud(self):
        host = self.w.config.host
        if "https://adb" in host:
            return "azure"
        elif ".gcp.databricks" in host:
            return "gcp"
        else:
            return "aws"
