import os
from typing import Set
from dotenv import load_dotenv

from azure.ai.projects import AIProjectClient
from azure.ai.agents.models import ToolSet, FunctionTool
from azure.identity import DefaultAzureCredential

# Load environment variables from .env file
load_dotenv()

# Example user function
from user_functions import fetch_current_datetime

# Import AzureLogicAppTool and the function factory from user_logic_apps
from user_logic_apps import AzureLogicAppTool, create_send_email_function
# </imports>

# <client_initialization>
# Create the project client
project_client = AIProjectClient(
    credential=DefaultAzureCredential(),
    endpoint=os.environ["PROJECT_ENDPOINT"],
)
# </client_initialization>

# <logic_app_tool_setup>
# Extract subscription and resource group from the project scope
subscription_id = "316ed70a-73d3-44e8-84aa-029c3a72408c"
resource_group = "BlendDemo"

# Logic App details
logic_app_name = "SQLConnection"
trigger_name = "When_a_HTTP_request_is_received"

# Create and initialize AzureLogicAppTool utility
logic_app_tool = AzureLogicAppTool(subscription_id, resource_group)
logic_app_tool.register_logic_app(logic_app_name, trigger_name)
print(f"Registered logic app '{logic_app_name}' with trigger '{trigger_name}'.")
# </logic_app_tool_setup>

# <function_creation>
# Create the specialized "send_email_via_logic_app" function for your agent tools
send_email_func = create_send_email_function(logic_app_tool, logic_app_name)

# Prepare the function tools for the agent
functions_to_use: Set = {
    fetch_current_datetime,
    send_email_func,  # This references the AzureLogicAppTool instance via closure
}
# </function_creation>

with project_client:
    # <auto_function_execution>
    # Enable automatic function execution for the agent runs
    project_client.agents.enable_auto_function_calls(tools=functions_to_use)
    # </auto_function_execution>

    # <agent_creation>
    # Create an agent
    functions = FunctionTool(functions=functions_to_use)
    toolset = ToolSet()
    toolset.add(functions)

    agent = project_client.agents.create_agent(
        model=os.environ["MODEL_DEPLOYMENT_NAME"],
        name="SendEmailAgent",
        instructions="You are a specialized agent for sending emails.",
        toolset=toolset,
    )
    print(f"Created agent, ID: {agent.id}")
    # </agent_creation>

    # <thread_management>
    # Create a thread for communication
    thread = project_client.agents.threads.create()
    print(f"Created thread, ID: {thread.id}")

    # Create a message in the thread
    message = project_client.agents.messages.create(
        thread_id=thread.id,
        role="user",
        content="Hello, please send an email to Deena.Nath@blend360.com with the date and time in '%Y-%m-%d %H:%M:%S' format.",
    )
    print(f"Created message, ID: {message.id}")
    # </thread_management>

    # <message_processing>
    # Create and process an agent run in the thread
    run = project_client.agents.runs.create_and_process(thread_id=thread.id, agent_id=agent.id)
    print(f"Run finished with status: {run.status}")

    if run.status == "failed":
        print(f"Run failed: {run.last_error}")
    # </message_processing>

    # <cleanup>
    # Delete the agent when done
    project_client.agents.delete_agent(agent.id)
    print("Deleted agent")

    # Fetch and log all messages
    messages = project_client.agents.messages.list(thread_id=thread.id)
    for message in messages:
        if message['role'] == 'assistant':
            # Extract just the value from the assistant's response
            content_value = message['content'][0]['text']['value']
            print(f"{content_value}")
    # </cleanup>