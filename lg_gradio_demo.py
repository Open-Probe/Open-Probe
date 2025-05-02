from smolagents import CodeAgent, GradioUI, LiteLLMModel
# from opendeepsearch import OpenDeepSearchTool
from smolagents import GradioUI
import os
from dotenv import load_dotenv
import argparse
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from opendeepsearch.lg_tools import OpenDeepSearchToolLanggraph
from opendeepsearch.wolfram_lg_tool import WolframAlphaToolLanggraph
from opendeepsearch.lg_gradio_ui import LangGraphGradioUI
from opendeepsearch.prompts import REACT_PROMPT, REACT_PROMPT_CLEAN
from langchain_openai import ChatOpenAI
from openai import OpenAI
import os
import logging
from langchain import hub
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("lg_gradio_demo")

# Load environment variables
load_dotenv()

# Add command line argument parsing
parser = argparse.ArgumentParser(description='Run the Gradio demo with custom models')
parser.add_argument('--model-name',
                   default=os.getenv("OPENROUTER_SEARCH_MODEL_ID", os.getenv("OPENROUTER_MODEL_ID", "google/gemini-2.0-flash-001")),
                   help='Model name for search')
parser.add_argument('--orchestrator-model',
                   default=os.getenv("OPENROUTER_ORCHESTRATOR_MODEL_ID", os.getenv("OPENROUTER_MODEL_ID", "google/gemini-2.0-flash-001")),
                   help='Model name for orchestration')
parser.add_argument('--reranker',
                   choices=['jina', 'infinity'],
                   default='jina',
                   help='Reranker to use (jina or infinity)')
parser.add_argument('--search-provider',
                   choices=['serper', 'searxng'],
                   default='serper',
                   help='Search provider to use (serper or searxng)')
parser.add_argument('--searxng-instance',
                   help='SearXNG instance URL (required if search-provider is searxng)')
parser.add_argument('--searxng-api-key',
                   help='SearXNG API key (optional)')
parser.add_argument('--serper-api-key',
                   help='Serper API key (optional, will use SERPER_API_KEY env var if not provided)')
parser.add_argument('--openai-base-url',
                   help='OpenAI API base URL (optional, will use OPENAI_BASE_URL env var if not provided)')
parser.add_argument('--server-port',
                   type=int,
                   default=7860,
                   help='Port to run the Gradio server on')
parser.add_argument('--openrouter-api-key',
                   default=os.getenv("OPENROUTER_API_KEY"),
                   help='OpenRouter API key (optional, will use OPENROUTER_API_KEY env var if not provided)')
parser.add_argument('--share', 
                   action='store_true',
                   help='Whether to create a public link for the interface')
parser.add_argument('--debug', 
                   action='store_true',
                   help='Enable debug mode with verbose logging')


args = parser.parse_args()

# Set debug level if requested
if args.debug:
    logging.getLogger().setLevel(logging.DEBUG)
    logger.setLevel(logging.DEBUG)
    logger.debug("Debug mode enabled")

# Validate arguments
if args.search_provider == 'searxng' and not (args.searxng_instance or os.getenv('SEARXNG_INSTANCE_URL')):
    parser.error("--searxng-instance is required when using --search-provider=searxng")

# Set OpenAI base URL if provided via command line
if args.openai_base_url:
    os.environ["OPENAI_BASE_URL"] = args.openai_base_url

logger.info(f"Using model: {args.model_name}")
logger.info(f"Using search provider: {args.search_provider}")

# Use the command line arguments
search_tool = OpenDeepSearchToolLanggraph(
    model_name=args.model_name,
    reranker=args.reranker,
    search_provider=args.search_provider,
    serper_api_key=args.serper_api_key,
    searxng_instance_url=args.searxng_instance,
    searxng_api_key=args.searxng_api_key
)

wolfram_tool = WolframAlphaToolLanggraph(
    app_id=os.getenv("WOLFRAM_ALPHA_APP_ID")
)





# Create LLM with OpenRouter
llm = ChatOpenAI(
    model=args.model_name,
    temperature=0.2,
    base_url="https://openrouter.ai/api/v1",
    api_key=args.openrouter_api_key,
    verbose=args.debug,
)

# Initialize the LangGraph agent with the tools
logger.info("Initializing agent...")

# Configure tools
tools = [search_tool, wolfram_tool]

# Create a prompt that uses REACT_PROMPT_CLEAN while maintaining ChatPromptTemplate structure
prompt = ChatPromptTemplate.from_messages(
    [
        # ("system", REACT_PROMPT.system_prompt),
                ("system", """You are a helpful search assistant powered by LangGraph that provides accurate information by searching the web.
        Your main job is to help users find information by using the search tool available to you.
        Always provide comprehensive and accurate answers based on the search results.
        If you don't know something or can't find information, be honest about it.
        """),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "Task: {input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ]
)


# Create the agent with tool calling
agent = create_tool_calling_agent(llm, tools, prompt)

# Create agent executor with verbose output in debug mode
agent_executor = AgentExecutor(
    agent=agent, 
    tools=tools, 
    verbose=True,
    return_intermediate_steps=args.debug,
)

# Define example questions for the UI
examples = {
    "General Knowledge": "How many meters taller is the Burj Khalifa compared to the Empire State Building?",
    "Latest Developments": "What are the latest developments in quantum computing and AI chips?",
    "Current Events": "What's happening with AI regulations globally?",
    "Technical Question": "Explain how transformer models work."
}

# Launch the Gradio UI
if __name__ == "__main__":
    logger.info(f"Starting Gradio server on port {args.server_port}...")
    
    # Add a callback to log invocations
    def log_callback(input_data):
        logger.info(f"Agent received query: {input_data}")
        return input_data
    
    # Create an agent wrapper with logging
    class LoggingAgentExecutor:
        def __init__(self, executor):
            self.executor = executor
            
        def invoke(self, input_data):
            logger.info(f"Agent invoked with: {input_data}")
            try:
                result = self.executor.invoke(input_data)
                logger.info(f"Agent result: {result}")
                return result
            except Exception as e:
                logger.error(f"Error in agent execution: {e}")
                raise
    
    # Create the wrapped agent
    wrapped_agent = LoggingAgentExecutor(agent_executor)
    
    # Create and launch the Gradio UI
    gradio_ui = LangGraphGradioUI(
        agent=wrapped_agent,
        name="OpenDeepSearch Powered by LangGraph",
        examples=examples
    )
    
    gradio_ui.launch(
        server_name="0.0.0.0",
        server_port=args.server_port,
        share=args.share
    )

