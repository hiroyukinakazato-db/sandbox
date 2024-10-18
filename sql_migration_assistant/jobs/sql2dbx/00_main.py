# Databricks notebook source
# MAGIC %md
# MAGIC # sql2dbx
# MAGIC sql2dbx is an automation tool designed to convert SQL files into Databricks notebooks. It leverages Large Language Models (LLMs) to perform the conversion based on system prompts tailored for various SQL dialects. sql2dbx consists of a series of Databricks notebooks.
# MAGIC
# MAGIC While the Databricks notebooks generated by sql2dbx may require manual adjustments, they serve as a valuable starting point for migrating SQL-based workflows to the Databricks environment.
# MAGIC
# MAGIC This main notebook functions as the entry point for sql2dbx's series of processes that convert SQL files into Databricks notebooks.

# COMMAND ----------

# MAGIC
# MAGIC %md-sandbox
# MAGIC ## 💫 Conversion Flow Diagram
# MAGIC The diagram below illustrates the flow of the SQL to Databricks notebooks conversion process.
# MAGIC
# MAGIC     <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
# MAGIC     <script>
# MAGIC         mermaid.initialize({startOnLoad:true});
# MAGIC     </script>
# MAGIC     <div class="mermaid">
# MAGIC       flowchart TD
# MAGIC           input[Input SQL Files] -->|Input| analyze[[01_analyze_input_files]]
# MAGIC           analyze <-->|Read & Write| conversionTable[Conversion Result Table]
# MAGIC
# MAGIC           conversionTable <-->|Read & Write| convert[[02_convert_sql_to_databricks]]
# MAGIC           convert -.->|Use| endpoint[LLM Endpoint]
# MAGIC           convert -.->|Refer| prompts["System Prompts\n(SQL Dialect Specific)"]
# MAGIC
# MAGIC           conversionTable <-->|Read & Write| validate[[03_01_static_syntax_check]]
# MAGIC
# MAGIC           conversionTable <-->|Read & Write| fixErrors[[03_02_fix_syntax_error]]
# MAGIC           fixErrors -.->|Use| endpoint
# MAGIC
# MAGIC           conversionTable -->|Input| export[[04_export_to_databricks_notebooks]]
# MAGIC           export -->|Output| notebooks[Converted Databricks Notebooks]
# MAGIC
# MAGIC           conversionTable <-->|Read & Write| adjust[[05_adjust_conversion_targets]]
# MAGIC
# MAGIC           %% Layout control with invisible lines
# MAGIC           convert --- validate --- fixErrors --- export
# MAGIC
# MAGIC           %% Styling
# MAGIC           classDef process fill:#E6E6FA,stroke:#333,stroke-width:2px;
# MAGIC           class analyze,convert,validate,fixErrors,adjust,export process;
# MAGIC           classDef data fill:#E0F0E0,stroke:#333,stroke-width:2px;
# MAGIC           class input,conversionTable,notebooks data;
# MAGIC           classDef external fill:#FFF0DB,stroke:#333,stroke-width:2px;
# MAGIC           class endpoint,prompts external;
# MAGIC
# MAGIC           %% Make layout control lines invisible
# MAGIC           linkStyle 11 stroke-width:0px;
# MAGIC           linkStyle 12 stroke-width:0px;
# MAGIC           linkStyle 13 stroke-width:0px;
# MAGIC     </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## 📝 Conversion Steps
# MAGIC This main notebook executes the following notebooks in sequence:
# MAGIC
# MAGIC | Notebook Name | Description |
# MAGIC |---|---|
# MAGIC | <a href="$./01_analyze_input_files" target="_blank">01_analyze_input_files</a> | Analyzes the input SQL files, calculates token counts, and saves the results to a Delta table. |
# MAGIC | <a href="$./02_convert_sql_to_databricks" target="_blank">02_convert_sql_to_databricks</a> | Converts the SQL code to a Python function that runs in a Databricks notebook using an LLM and updates the result table. |
# MAGIC | <a href="$./03_01_static_syntax_check" target="_blank">03_01_static_syntax_check</a> | Performs static syntax checks on Python functions and the Spark SQL contained within them, updating the result table with any errors found. |
# MAGIC | <a href="$./03_02_fix_syntax_error" target="_blank">03_02_fix_syntax_error</a> | Fixes syntax errors in Python functions and SQL statements identified in the previous step using an LLM and updates the result table. |
# MAGIC | <a href="$./04_export_to_databricks_notebooks" target="_blank">04_export_to_databricks_notebooks</a> | Exports the converted code to Databricks notebooks. |
# MAGIC | <a href="$./05_adjust_conversion_targets" target="_blank">05_adjust_conversion_targets</a> | (Optional) Adjusts the conversion targets by setting the `is_conversion_target` field to `True` for specific files that need to be re-converted. This can be used to reprocess files that did not convert satisfactorily. |
# MAGIC
# MAGIC ## 🎯 Conversion Sources
# MAGIC sql2dbx currently supports the conversion of **T-SQL** (Transact-SQL) code to Databricks notebooks. The architecture of sql2dbx allows for the addition of system prompts for other SQL dialects, expanding its capabilities to handle various SQL variants.
# MAGIC
# MAGIC While we plan to add support for more SQL dialects in the future, you have the flexibility to provide your own system prompt for your specific SQL dialect, in addition to the existing one. Please note that this requires slight modifications to the <a href="$./02_convert_sql_to_databricks" target="_blank">02_convert_sql_to_databricks</a> notebook.
# MAGIC
# MAGIC ## 📢 Prerequisites
# MAGIC Before running the main notebook, ensure that a Databricks model serving endpoint is available, either with an external model or using the Foundation Model APIs. If you need to set up an external model serving endpoint, you can use the following automation notebooks as needed:
# MAGIC
# MAGIC - <a href="$./external_model/external_model_azure_openai" target="_blank">Notebook for Azure OpenAI Service Endpoint Setup</a>
# MAGIC - <a href="$./external_model/external_model_amazon_bedrock" target="_blank">Notebook for Amazon Bedrock Endpoint Setup</a>
# MAGIC
# MAGIC ## ❗ Important Notes
# MAGIC The following points should be considered before running the main notebook:
# MAGIC
# MAGIC ### Model Compatibility
# MAGIC sql2dbx has been verified to produce highly accurate conversions with sufficient input/output token lengths using the following state-of-the-art models. For the best results, we recommend using models with capabilities equal to or greater than these. While it is expected to function with other foundation models, it may require adjustments to the prompt, parameters, or even the notebook code itself, depending on the specific model's capabilities and limitations.
# MAGIC
# MAGIC * [Anthropic Claude 3.5 Sonnet](https://www.anthropic.com/news/claude-3-5-sonnet) (200K token context window)
# MAGIC * [OpenAI GPT-4o (Omni)](https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/models) (128K input tokens, 4K output tokens)
# MAGIC * [Meta Llama 3.1 405B Instruct](https://docs.databricks.com/en/machine-learning/foundation-models/supported-models.html#meta-llama-31-405b-instruct) (128K token context window)
# MAGIC
# MAGIC ### Token Limit for Input Files
# MAGIC The <a href="$./01_analyze_input_files" target="_blank">01_analyze_input_files</a> notebook measures the token count of each SQL file and determines whether it should be a target for conversion to a Databricks notebook. The process flow is as follows:
# MAGIC
# MAGIC 1. Measure the token count of each SQL file, excluding comments and multiple spaces, using `o200k_base`tokenizer of [openai/tiktoken](https://github.com/openai/tiktoken).
# MAGIC 2. If the measured token count is less than or equal to the `token_count_threshold` parameter, the file becomes a conversion target.
# MAGIC     - Files meeting this condition have their `is_conversion_target` field set to `True`.
# MAGIC 3. Files exceeding the `token_count_threshold` are excluded from processing.
# MAGIC
# MAGIC The default value for `token_count_threshold` is set to 20,000 tokens. This value is based on the token limits of (Azure) OpenAI's [GPT-4o](https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/models) (input token limit: 128,000 tokens, output token limit: 4,096 tokens), with a considerable safety margin. This ensures efficient file processing without exceeding the model's constraints.
# MAGIC
# MAGIC If you are using a different model or need to process larger files, adjust the `token_count_threshold` value according to your model's token length restrictions and task requirements.
# MAGIC
# MAGIC ## 🔌 Parameters
# MAGIC The main notebook requires the following parameters to be set. For more granular parameter settings, please run individual specialized notebooks instead of this main notebook. The individual notebooks allow for more detailed customization for specific tasks.
# MAGIC
# MAGIC Parameter Name | Required | Default Value | Description
# MAGIC --- | --- | --- | ---
# MAGIC `input_dir` | Yes | | The directory containing the SQL files to be converted. Supports locations accessible through Python `os` module (e.g., Unity Catalog Volume, Workspace, Repos, etc.).
# MAGIC `result_catalog` | Yes | | The existing catalog where the result table will be stored.
# MAGIC `result_schema` | Yes | | The existing schema under the specified catalog where the result table will reside.
# MAGIC `token_count_threshold` | Yes | `20000` | Specifies the maximum token count allowed without SQL comments for files to be included in the following conversion process.
# MAGIC `existing_result_table` | No | | The existing result table to use for storing the analysis results. If specified, the table will be used instead of creating a new one.
# MAGIC `endpoint_name` | Yes |  | The name of the Databricks Model Serving endpoint. You can find the endpoint name under the `Serving` tab. Example: If the endpoint URL is `https://<workspace_url>/serving-endpoints/hinak-oneenvgpt4o/invocations`, specify `hinak-oneenvgpt4o`.
# MAGIC `sql_dialect` | Yes | `tsql` | The SQL dialect to be converted. Currently, only tsql is supported.
# MAGIC `comment_lang` | Yes | `English` | The language for comments to be added to the converted Databricks notebooks. Options are English or Japanese.
# MAGIC `request_params` | Yes | `{"max_tokens": 4000, "temperature": 0}` | The extra chat HTTP request parameters in JSON format (reference: [Databricks Foundation Model APIs](https://docs.databricks.com/en/machine-learning/foundation-models/api-reference.html#chat-request)).
# MAGIC `max_fix_attempts` | Yes | `1` | The maximum number of attempts to automatically fix syntax errors in the conversion results.
# MAGIC `output_dir` | Yes | The directory where Databricks notebooks are saved. Supports the path in Workspace or Repos.
# MAGIC
# MAGIC ## 📂 Input and Output
# MAGIC Main input and output of the conversion process are as follows:
# MAGIC
# MAGIC ### Input SQL Files
# MAGIC You should store the input SQL files in the `input_files_path` directory. <a href="$./01_analyze_input_files" target="_blank">01_analyze_input_files</a> notebook processes all files in the directory and its subdirectories. Supports locations accessible through Python `os` module (e.g., Unity Catalog Volume, Workspace, Repos, etc.).
# MAGIC
# MAGIC ### Convertion Result Notebook (Final Output)
# MAGIC The conversion result Databricks notebooks are created by the <a href="$./04_export_to_databricks_notebooks" target="_blank">04_export_to_databricks_notebooks</a> notebook and serves as the final output of the conversion process. Supports a path in Workspace or Repos.
# MAGIC
# MAGIC ### Conversion Result Table (Intermediate Output)
# MAGIC The conversion result table is created by the <a href="$./01_analyze_input_files" target="_blank">01_analyze_input_files</a> notebook and serves as both an input and output for subsequent notebooks in the conversion process. It is a Delta Lake table that stores the analysis results of input SQL files, including token counts, file metadata, and conversion status.
# MAGIC
# MAGIC #### Table Naming
# MAGIC The table name is constructed using parameters specified in the notebooks, following the format below:
# MAGIC
# MAGIC `{result_catalog}.{result_schema}.{result_table_prefix}_{YYYYMMDDHHmm}`
# MAGIC
# MAGIC For example, if the `result_catalog` is "my_catalog", the `result_schema` is "my_schema", the `result_table_prefix` is "conversion_targets", and the current time (UTC) is 2024-06-14 11:39, the table name will be:
# MAGIC
# MAGIC `my_catalog.my_schema.conversion_targets_202406141139`
# MAGIC
# MAGIC #### Table Schema
# MAGIC The table schema is as follows:
# MAGIC
# MAGIC | Column Name | Data Type | Description |
# MAGIC |---|---|---|
# MAGIC | `input_file_number` | int | A unique integer identifier for each input file. The numbering starts from `1`. |
# MAGIC | `input_file_path` | string | The full path to the input file. |
# MAGIC | `input_file_encoding` | string | The detected encoding of the input file (e.g., `UTF-8`). |
# MAGIC | `tiktoken_encoding` | string | The encoding used for tokenization in LLMs (e.g., `o200k_base`). |
# MAGIC | `input_file_token_count` | int | The total number of tokens in the input file. |
# MAGIC | `input_file_token_count_without_sql_comments` | int | The number of tokens in the input file excluding SQL comments. |
# MAGIC | `input_file_content` | string | The entire content of the input file. |
# MAGIC | `input_file_content_without_sql_comments` | string | The content of the input file excluding SQL comments. |
# MAGIC | `is_conversion_target` | boolean | Indicates whether the file is a conversion target (True or False). This is determined in `01_analyze_input_files` based on a comparison between the token count of the input file (excluding SQL comments) and the `token_count_threshold`. It is automatically updated from `True` to `False` once the conversion process is successfully completed. |
# MAGIC | `model_serving_endpoint_for_conversion` | string | The model serving endpoint for the conversion process. |
# MAGIC | `model_serving_endpoint_for_fix` | string | The model serving endpoint for syntax error fixing. |
# MAGIC | `result_content` | string | The converted content of the file after processing. (Initially `null`) |
# MAGIC | `result_token_count` | int | The token count of the converted content. (Initially `null`) |
# MAGIC | `result_error` | string | Any errors encountered during the conversion process. (Initially `null`) |
# MAGIC | `result_timestamp` | string | The timestamp (UTC) when the `result_content` was generated or updated. (Initially `null`) |
# MAGIC | `result_python_parse_error` | string | Any errors encountered during the Python function syntax check using `ast.parse`. |
# MAGIC | `result_extracted_sqls` | array<string> | The list of SQL statements extracted from the Python function.  (Initially `null`) |
# MAGIC | `result_sql_parse_errors` | array<string> | Any errors encountered during the SQL syntax check using `spark._jsparkSession.sessionState().sqlParser().parsePlan()`. (Initially `null`) |
# MAGIC
# MAGIC ## 🔄 How to Re-convert Specific Files
# MAGIC If the conversion result is not satisfactory, you can re-convert specific files by following these steps:
# MAGIC
# MAGIC 1.  Use the <a href="$./05_adjust_conversion_targets" target="_blank">05_adjust_conversion_targets</a> notebook to set the `is_conversion_target` field to `True` for the files you want to re-convert.
# MAGIC 2.  Rerun the <a href="$./02_convert_sql_to_databricks" target="_blank">02_convert_sql_to_databricks</a> notebook. Only the files marked as `is_conversion_target` is `True` will be re-converted.
# MAGIC     - To introduce more randomness in the LLM's conversion process and obtain different results on each run, it is recommended to set the `temperature` in `request_params` to above 0.5.
# MAGIC
# MAGIC ## 💻 Verified Environments
# MAGIC This notebook has been verified to work in the following environments:
# MAGIC
# MAGIC - Databricks Runtime (DBR)
# MAGIC     - 14.3 LTS
# MAGIC     - 15.3
# MAGIC - Single-node cluster
# MAGIC     - Note: This notebook does not work on serverless clusters.

# COMMAND ----------

# MAGIC %md
# MAGIC ## 0. Set Up Configuration Parameters
# MAGIC Major configuration parameters are set up in this section. If you need to change other parameters, change then in the respective notebooks.

# COMMAND ----------

# DBTITLE 1,Configurations
# Params for 01_analyze_input_files
dbutils.widgets.text("input_dir", "", "Input Directory")
dbutils.widgets.text("result_catalog", "", "Result Catalog")
dbutils.widgets.text("result_schema", "", "Result Schema")
dbutils.widgets.text("token_count_threshold", "20000", "Token Count Threshold")
dbutils.widgets.text("existing_result_table", "", "Existing Result Table (Optional)")

# Params for 02_convert_sql_to_databricks
dbutils.widgets.text("endpoint_name", "", "Serving Endpoint Name")
dbutils.widgets.dropdown("sql_dialect", "tsql", ["tsql"], "SQL Dialect")
dbutils.widgets.dropdown("comment_lang", "English", ["English", "Japanese"], "Comment Language")
dbutils.widgets.text("request_params", '{"max_tokens": 4000, "temperature": 0}', "Chat Request Params")

# Params for 03_syntax_check_and_fix
dbutils.widgets.text("max_fix_attempts", "1", "Maximum Fix Attempts")

# Params for 04_export_to_databricks_notebooks
dbutils.widgets.text("output_dir", "", "Output Directory")

# COMMAND ----------

# DBTITLE 1,Load Configurations
input_dir = dbutils.widgets.get("input_dir")
result_catalog = dbutils.widgets.get("result_catalog")
result_schema = dbutils.widgets.get("result_schema")
token_count_threshold = int(dbutils.widgets.get("token_count_threshold"))
existing_result_table = dbutils.widgets.get("existing_result_table")
endpoint_name = dbutils.widgets.get("endpoint_name")
sql_dialect = dbutils.widgets.get("sql_dialect")
comment_lang = dbutils.widgets.get("comment_lang")
request_params = dbutils.widgets.get("request_params")
max_fix_attempts = int(dbutils.widgets.get("max_fix_attempts"))
output_dir = dbutils.widgets.get("output_dir")

input_dir, result_catalog, result_schema, token_count_threshold, existing_result_table, endpoint_name, sql_dialect, comment_lang, request_params, max_fix_attempts, output_dir

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Analyze Input Files
# MAGIC Analyzes the input SQL files, calculates token counts, and saves the results to a Delta table.

# COMMAND ----------

# DBTITLE 1,Analyze Input Files
result_table = dbutils.notebook.run("01_analyze_input_files", 0, {
    "input_dir": input_dir,
    "result_catalog": result_catalog,
    "result_schema": result_schema,
    "token_count_threshold": token_count_threshold,
    "existing_result_table": existing_result_table,
})
print(f"Conversion result table: {result_table}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Convert SQL to Databricks
# MAGIC Converts the SQL code to a Python function that runs in a Databricks notebook using an LLM and updates the result table.

# COMMAND ----------

# DBTITLE 1,Convert SQL to Databricks Notebooks
dbutils.notebook.run("02_convert_sql_to_databricks", 0, {
    "endpoint_name": endpoint_name,
    "result_table": result_table,
    "sql_dialect": sql_dialect,
    "comment_lang": comment_lang,
    "request_params": request_params,
})

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Syntax Check and Fix
# MAGIC Performs static syntax checks on Python functions and the Spark SQL contained within them, and attempts to fix any errors found.

# COMMAND ----------

# DBTITLE 1,Function for Syntax Error File Count
def get_error_file_count(result_table: str) -> int:
    """Get the count of files with syntax errors."""
    error_count = spark.sql(f"""
        SELECT COUNT(*) as error_count
        FROM {result_table}
        WHERE result_python_parse_error IS NOT NULL
        OR (result_sql_parse_errors IS NOT NULL AND size(result_sql_parse_errors) > 0)
    """).collect()[0]['error_count']
    return error_count

# COMMAND ----------

# DBTITLE 1,Check and Fix Syntax Errors
for attempt in range(max_fix_attempts):
    # Run static syntax check
    print(f"Attempt {attempt + 1} of {max_fix_attempts}")
    dbutils.notebook.run("03_01_static_syntax_check", 0, {
        "result_table": result_table,
    })

    # Check if there are any errors
    error_count = get_error_file_count(result_table)
    if error_count == 0:
        print("No syntax errors found. Exiting fix loop.")
        break

    # Run fix syntax error
    print(f"Found {error_count} files with syntax errors. Attempting to fix...")
    dbutils.notebook.run("03_02_fix_syntax_error", 0, {
        "endpoint_name": endpoint_name,
        "result_table": result_table,
        "request_params": request_params,
    })

# COMMAND ----------

# MAGIC %md
# MAGIC ### Final Syntax Check
# MAGIC Performs a final static syntax check after all fix attempts.

# COMMAND ----------

# DBTITLE 1,Run Final Syntax Check
dbutils.notebook.run("03_01_static_syntax_check", 0, {
    "result_table": result_table,
})
error_count = get_error_file_count(result_table)
print(f"Found {error_count} files with syntax errors.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Export to Databricks Notebooks
# MAGIC Exports the converted code to Databricks notebooks.

# COMMAND ----------

# DBTITLE 1,Export to Databricks Notebooks
export_results_json = dbutils.notebook.run("04_export_to_databricks_notebooks", 0, {
    "result_table": result_table,
    "output_dir": output_dir
})

# COMMAND ----------

# MAGIC %md
# MAGIC ### Display and Return Export Results
# MAGIC The following cell displays the notebook export results and returns them to the caller. The results include the following important information.
# MAGIC
# MAGIC - `export_succeeded`: A boolean indicating whether the export was successful
# MAGIC - `parse_error_count`: The number of notebooks with parse errors
# MAGIC
# MAGIC Pay special attention to notebooks where `parse_error_count` is greater equal to `1`. These notebooks may require manual corrections.

# COMMAND ----------

# DBTITLE 1,Display Export Results
import json
import pandas as pd

export_results = json.loads(export_results_json)
export_results_df = pd.DataFrame(export_results)
display(export_results_df)