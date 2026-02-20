import os, time
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.agents.models import FunctionTool
import json
import requests
from dotenv import load_dotenv

load_dotenv()

# Function to Get Weather Information
def get_weather(latitude: float, longitude: float) -> str:
    """
    Retrieves the weather condition for a given location using latitude and longitude.

    :param latitude (float): Latitude of the location.
    :param longitude (float): Longitude of the location.
    :return: Weather details as a JSON string.

    """

    # Validate latitude and longitude
    if latitude is None or longitude is None:
        return json.dumps({"error": "Latitude and longitude are required."})
    if latitude > 90 or latitude < -90:
        return json.dumps({"error": "Invalid latitude value. It must be between -90 and 90."})
    if longitude > 180 or longitude < -180:
        return json.dumps({"error": "Invalid longitude value. It must be between -180 and 180."})

    # Get API key from environment variable
    api_key = os.getenv("OPENWEATHER_MAP_API_KEY")
    print(api_key)

    # OpenWeather API Endpoint
    base_url = "https://api.openweathermap.org/data/3.0/onecall?"
    complete_url = f"{base_url}lat={latitude}&lon={longitude}&appid={api_key}&units=metric"

    try:
        # Make the API request
        response = requests.get(complete_url)
        weather_data = response.json()  # Parse JSON response

        # Check for API errors
        if response.status_code != 200:
            return json.dumps({"error": weather_data.get("message", "Failed to fetch weather data.")})

        # Extract weather details
        weather_condition = weather_data["current"]["weather"][0]["description"]
        temperature =weather_data["current"]["temp"]

        return json.dumps({
            "latitude": latitude,
            "longitude": longitude,
            "weather_condition": weather_condition,
            "temperature": temperature
        }, indent=4)

    except Exception as e:
        return json.dumps({"error": str(e)})

# Define user functions
user_functions = {get_weather}

# Retrieve the project endpoint from environment variables
project_endpoint = os.environ["PROJECT_ENDPOINT"]
model_name = os.environ["AZURE_AI_FOUNDRY_MODEL_DEPLOYMENT_NAME"]
# Initialize the AIProjectClient
project_client = AIProjectClient(
    endpoint=project_endpoint,
    credential=DefaultAzureCredential()
)

# Initialize the FunctionTool with user-defined functions
functions = FunctionTool(functions=user_functions)

with project_client:
    # Create an agent with custom functions
    agent = project_client.agents.create_agent(
        model=model_name,
        name="my-agent",
        instructions="You are a helpful agent to provide weather information using latitude and longitude coordinates. Use your knowledge to get latitude and Longitude and then provide weather data using get_weather function. Always return Latitude and Longitude in the response.",
        tools=functions.definitions,
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

        # Send a message to the thread
        message = project_client.agents.messages.create(
            thread_id=thread.id,
            role="user",
            content=question,
        )
        print(f"Created message, ID: {message['id']}")

        # Create and process a run for the agent to handle the message
        run = project_client.agents.runs.create(thread_id=thread.id, agent_id=agent.id)
        print(f"Created run, ID: {run.id}")

        # Poll the run status until it is completed or requires action
        while run.status in ["queued", "in_progress", "requires_action"]:
            time.sleep(1)
            run = project_client.agents.runs.get(thread_id=thread.id, run_id=run.id)

            if run.status == "requires_action":
                tool_calls = run.required_action.submit_tool_outputs.tool_calls
                tool_outputs = []
                for tool_call in tool_calls:
                    if tool_call.function.name == "get_weather":
                        # Parse arguments from the tool call
                        args = json.loads(tool_call.function.arguments)
                        latitude = args.get("latitude")
                        longitude = args.get("longitude")
                        output = get_weather(latitude, longitude)
                        tool_outputs.append({"tool_call_id": tool_call.id, "output": output})
                project_client.agents.runs.submit_tool_outputs(thread_id=thread.id, run_id=run.id, tool_outputs=tool_outputs)

        print(f"Run finished with status: {run.status}")

        # Check if the run failed
        if run.status == "failed":
            print(f"Run failed: {run.last_error}")
            continue

        # Fetch and log all messages from the thread
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