"""
Gradio UI for LangGraph agent interface.
"""
import uuid
import gradio as gr
from typing import Optional, List, Dict, Any, Callable, Tuple, Generator
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from opendeepsearch.lg_agent import OpenDeepSearchAgentLanggraph

class LangGraphGradioUI:
    """Gradio UI for LangGraph agents."""
    
    def __init__(self, agent: Any, name: str = "OpenDeepSearch LangGraph", examples: Dict[str, str] = None):
        """
        Initialize the Gradio UI for a LangGraph agent.
        
        Args:
            agent: The LangGraph agent to use
            name: The name of the UI
            examples: Dictionary of example questions {button_text: question}
        """
        self.agent = agent
        self.name = name
        self.examples = examples or {
            "Example 1: Web Search": "What were the major tech announcements in 2023?",
            "Example 2: Current Events": "What's happening with AI regulations globally?",
            "Example 3: Technical Question": "Explain how transformer models work."
        }
        
    def format_chat_history(self, chat_history: List[Tuple[str, str]]) -> List[Dict[str, Any]]:
        """Format chat history from Gradio format to LangChain format."""
        messages = []
        for human_msg, ai_msg in chat_history:
            if human_msg:
                messages.append({"type": "human", "content": human_msg})
            if ai_msg:
                messages.append({"type": "ai", "content": ai_msg})
        return messages
        
    def _process_query(self, query: str, chat_history: List[Tuple[str, str]]) -> Generator[List[Tuple[str, str]], None, None]:
        """Process a query and update chat history with streaming updates."""
        if not query.strip():
            return chat_history
        
        # Format chat history for the agent
        formatted_history = []
        for human, ai in chat_history:
            if human:
                formatted_history.append(HumanMessage(content=human))
            if ai:
                formatted_history.append(AIMessage(content=ai))
                
        # Add placeholder for response
        chat_history.append((query, ""))
        yield chat_history
        
        # Update with "searching" message
        chat_history[-1] = (query, "Searching for information...")
        yield chat_history
        
        try:
            # Prepare the input for the agent
            input_data = {
                "input": query
            }
            
            # If the agent supports chat history, add it
            if hasattr(self.agent, "memory") or "history" in str(self.agent.__class__):
                input_data["chat_history"] = formatted_history
                
            # Get response from agent
            print(f"Invoking agent with input: {input_data}")
            response = self.agent.invoke(input_data)
            print(f"Agent response: {response}")
            
            # Extract the output text based on response format
            if isinstance(response, dict):
                if "output" in response:
                    response_text = response["output"]
                elif "result" in response:
                    response_text = response["result"]
                elif "response" in response:
                    response_text = response["response"]
                elif "answer" in response:
                    response_text = response["answer"]
                elif "content" in response:
                    response_text = response["content"]
                elif "text" in response:
                    response_text = response["text"]
                else:
                    # Fallback to string representation if no known keys
                    response_text = str(response)
            else:
                response_text = str(response)
                
            # Update chat history with the final response
            chat_history[-1] = (query, response_text)
            
        except Exception as e:
            print(f"Error processing query: {e}")
            error_message = f"Error: {str(e)}"
            chat_history[-1] = (query, error_message)
        
        yield chat_history
    
    def _reset(self) -> List[Tuple[str, str]]:
        """Reset the chat history."""
        return []
    
    def _load_example(self, example_text: str) -> str:
        """Load example text."""
        return example_text
    
    def launch(self, **kwargs):
        """Launch the Gradio interface."""
        # Define CSS for better styling
        css = """
        .contain { display: flex; flex-direction: column; }
        #component-0 { height: 100%; }
        #chatbot { flex-grow: 1; overflow: auto; }
        .message.user {
            background-color: #2b5a97;
        }
        .message.bot {
            background-color: #1f3d6d;
        }
        """
        
        with gr.Blocks(css=css, title=self.name) as demo:
            # Header
            gr.Markdown(f"""
            # 🔍 {self.name}
            
            A smart search assistant powered by LangGraph that provides accurate information by searching the web and analyzing results.
            
            Start by entering your question in the text box below or trying one of the examples.
            """)
            
            # State for tracking chat history
            state = gr.State([])
            
            # Chatbot component
            chatbot = gr.Chatbot(
                label="Search Assistant",
                height=500,
                show_copy_button=True,
                elem_id="chatbot",
                bubble_full_width=False,
            )
            
            # Input row
            with gr.Row():
                query = gr.Textbox(
                    label="Your Question",
                    placeholder="Ask anything...",
                    scale=9,
                    container=False,
                )
                submit_btn = gr.Button("Submit", scale=1)
            
            # Example and control buttons
            with gr.Row():
                example_buttons = []
                for button_text, example_text in self.examples.items():
                    example_btn = gr.Button(button_text)
                    example_btn.click(
                        fn=lambda text=example_text: text,
                        outputs=query
                    )
            
            with gr.Row():
                clear_btn = gr.Button("🧹 Clear History")
                
            # Set up event handlers
            submit_click = submit_btn.click(
                fn=self._process_query,
                inputs=[query, chatbot],
                outputs=chatbot,
                show_progress=True,
            ).then(
                fn=lambda: "",
                outputs=query
            )
            
            query_submit = query.submit(
                fn=self._process_query,
                inputs=[query, chatbot],
                outputs=chatbot,
                show_progress=True,
            ).then(
                fn=lambda: "",
                outputs=query
            )
            
            # Connect example buttons to submission
            for button_text, example_text in self.examples.items():
                button = [b for b in example_buttons if b.value == button_text]
                if button:
                    button[0].click(
                        fn=self._process_query,
                        inputs=[lambda text=example_text: text, chatbot],
                        outputs=chatbot,
                        show_progress=True,
                    )
            
            # Set up event handler for clear button
            clear_btn.click(
                fn=self._reset,
                outputs=chatbot
            )
            
            # Footer
            gr.Markdown("""
            ---
            This application uses various APIs for search and language processing. Use responsibly.
            """)
        
        # Launch the interface with provided kwargs
        return demo.launch(**kwargs)