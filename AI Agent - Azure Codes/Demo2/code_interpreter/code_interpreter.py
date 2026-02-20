import os
from azure.ai.projects import AIProjectClient
from azure.ai.agents.models import CodeInterpreterTool
from azure.ai.agents.models import FilePurpose, MessageRole
from azure.identity import DefaultAzureCredential
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# <client_initialization>
endpoint = os.environ["PROJECT_ENDPOINT"]
model_deployment_name = os.environ["AZURE_AI_FOUNDRY_MODEL_DEPLOYMENT_NAME"]

with AIProjectClient(
    endpoint=endpoint,
    credential=DefaultAzureCredential(),
) as project_client:
# </client_initialization>

    # Upload a file and wait for it to be processed
    # [START upload_file_and_create_agent_with_code_interpreter]
    # <file_upload>
    file = project_client.agents.files.upload_and_poll(
        file_path=str(Path(__file__).parent / "nifty_500_quarterly_results.csv"), purpose=FilePurpose.AGENTS
    )
    print(f"Uploaded file, file ID: {file.id}")
    # </file_upload>

    # <code_interpreter_setup>
    code_interpreter = CodeInterpreterTool(file_ids=[file.id])
    # </code_interpreter_setup>

    # <agent_creation>
    # Create agent with code interpreter tool and tools_resources
    agent = project_client.agents.create_agent(
        model=os.environ["AZURE_AI_FOUNDRY_MODEL_DEPLOYMENT_NAME"],
        name="my-assistant",
        instructions="You are a helpful agent that perform Data Analysis and Visualiation. You creates different charts based on user request. You only use the file provided to you for analysis and visualization. If the user ask for a chart, you create the chart and provide the file to user.",
        tools=code_interpreter.definitions,
        tool_resources=code_interpreter.resources,
    )
    # [END upload_file_and_create_agent_with_code_interpreter]
    print(f"Created agent, agent ID: {agent.id}")
    # </agent_creation>

    # <thread_management>
    thread = project_client.agents.threads.create()
    print(f"Created thread, thread ID: {thread.id}")

    # Create a message
    message = project_client.agents.messages.create(
        thread_id=thread.id,
        role="user",
        content="Could you please create bar chart in TRANSPORTATION sector for the operating profit from the uploaded csv file and provide file to me?",
    )
    print(f"Created message, message ID: {message.id}")
    # </thread_management>

    # <message_processing>
    run = project_client.agents.runs.create_and_process(thread_id=thread.id, agent_id=agent.id)
    print(f"Run finished with status: {run.status}")

    if run.status == "failed":
        # Check if you got "Rate limit is exceeded.", then you want to get more quota
        print(f"Run failed: {run.last_error}")
    # </message_processing>

    # <file_handling>
    project_client.agents.files.delete(file.id)
    print("Deleted file")

    # [START get_messages_and_save_files]
    messages = project_client.agents.messages.list(thread_id=thread.id)
    print(f"Messages: {messages}")

    # Iterate through all messages to find image contents and file path annotations
    for message in messages:
        if hasattr(message, 'content') and message.content:
            for content_item in message.content:
                # Check for image files
                if hasattr(content_item, 'image_file') and content_item.image_file:
                    file_id = content_item.image_file.file_id
                    print(f"Image File ID: {file_id}")
                    file_name = f"{file_id}_image_file.png"
                    project_client.agents.files.save(file_id=file_id, file_name=file_name)
                    print(f"Saved image file to: {Path.cwd() / file_name}")
                
                # # Check for file path annotations in text content
                # if hasattr(content_item, 'text') and content_item.text:
                #     if hasattr(content_item.text, 'annotations') and content_item.text.annotations:
                #         for annotation in content_item.text.annotations:
                #             if hasattr(annotation, 'file_path') and annotation.file_path:
                #                 file_id = annotation.file_path.file_id
                #                 print(f"File Paths:")
                #                 print(f"Type: {annotation.type}")
                #                 print(f"Text: {annotation.text}")
                #                 print(f"File ID: {file_id}")
                #                 print(f"Start Index: {annotation.start_index}")
                #                 print(f"End Index: {annotation.end_index}")
                #                 # Save the file
                #                 file_name = f"{file_id}_chart.png"
                #                 project_client.agents.files.save(file_id=file_id, file_name=file_name)
                #                 print(f"Saved file to: {Path.cwd() / file_name}")
    # [END get_messages_and_save_files]
    # </file_handling>

    # Get the last message from the agent
    print("\n=== Extracting Agent's Text Response ===")
    last_msg_text = None
    
    # Messages are typically in reverse chronological order (newest first)
    for message in messages:
        print(f"Message Role: {message.role}")
        if message.role == MessageRole.AGENT and message.content:
            for content_item in message.content:
                print(f"Content Item Type: {type(content_item)}")
                if hasattr(content_item, 'text') and content_item.text:
                    # Handle text with annotations
                    text_value = content_item.text.value if hasattr(content_item.text, 'value') else str(content_item.text)
                    print(f"Found text content: {text_value[:100]}...")  # Print first 100 chars
                    if not last_msg_text:  # Get the first agent message (most recent)
                        last_msg_text = text_value
                        break
            if last_msg_text:
                break
    
    if last_msg_text:
        print(f"\n=== Last Agent Message ===\n{last_msg_text}")
    else:
        print("No text message found from agent")

    # <cleanup>
    project_client.agents.delete_agent(agent.id)
    print("Deleted agent")
    # </cleanup>
