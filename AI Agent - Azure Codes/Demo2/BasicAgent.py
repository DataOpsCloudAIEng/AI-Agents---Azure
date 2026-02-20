import os
import time
from pathlib import Path
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv()

# Create an AIProjectClient instance
project_client = AIProjectClient(
    endpoint=os.getenv("PROJECT_ENDPOINT"),
    credential=DefaultAzureCredential(),  
    # Use Azure Default Credential for authentication
)

with project_client:

    agent = project_client.agents.create_agent(
        model=os.getenv("AZURE_AI_FOUNDRY_MODEL_DEPLOYMENT_NAME"),  # Model deployment name
        name="my-agent",  # Name of the agent
        instructions="You are helpful assistant",  # Instructions for the agent
    )
    print(f"Created agent, ID: {agent.id}")

    # Create a thread for communication
    thread = project_client.agents.threads.create()
    print(f"Created thread, ID: {thread.id}")

    # Loop to ask questions until user stops
    while True:
        # Get question from user
        question = input("\nEnter your question (type 'exit', 'quit', or 'stop' to end): ")
        
        # Check if user wants to exit
        if question.lower() in ['exit', 'quit', 'stop']:
            print("Exiting conversation...")
            break

        # Add a message to the thread
        message = project_client.agents.messages.create(
            thread_id=thread.id,
            role="user",  # Role of the message sender
            content=question,  # Message content
        )
        print(f"Created message, ID: {message['id']}")

        # Create and process an agent run
        run = project_client.agents.runs.create_and_process(
            thread_id=thread.id,
            agent_id=agent.id,
            additional_instructions="""Please address the user as Deena nath""",
        )

        print(f"Run finished with status: {run.status}")

        # Check if the run failed
        if run.status == "failed":
            print(f"Run failed: {run.last_error}")
            continue

        # Fetch and log all messages
        messages = project_client.agents.messages.list(thread_id=thread.id)
        print("\n--- Agent Response ---")
        # Get the most recent assistant message
        for msg in messages:
            if msg.role == "assistant":
                if msg.text_messages:
                    last_text = msg.text_messages[-1]
                    print(f"{last_text.text.value}")
                break
        print("--- End Response ---\n")

    # Delete the agent after use
    project_client.agents.delete_agent(agent.id)
    print("Deleted agent")