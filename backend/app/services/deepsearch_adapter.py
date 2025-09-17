import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
import sys
import os

# Add the project root to Python path to import from src
project_root = os.path.join(os.path.dirname(__file__), "../../../")
sys.path.insert(0, project_root)
src_path = os.path.join(project_root, "src")
sys.path.insert(0, src_path)

try:
    from deepsearch.graph import graph
    from deepsearch.utils import extract_content
    DEEPSEARCH_AVAILABLE = True
    print("✅ DeepSearch modules imported successfully")
except ImportError as e:
    print(f"⚠️  Warning: Could not import deepsearch modules: {e}")
    print("🔧 Running in mock mode - UI will work but use simulated responses")
    graph = None
    extract_content = None
    DEEPSEARCH_AVAILABLE = False

from ..models.search import ThinkingStep, StepType, StepStatus, StepMetadata, SourceInfo
from ..services.websocket_service import WebSocketManager
from ..services.session_manager import SessionManager
from ..utils.exceptions import DeepSearchIntegrationException, SearchException, SessionException
from ..utils.logging import get_logger

logger = get_logger("deepsearch.adapter")

class DeepSearchAdapter:
    """Adapter service to interface with the existing DeepSearch system."""
    
    def __init__(self, websocket_manager: WebSocketManager, session_manager: SessionManager):
        self.websocket_manager = websocket_manager
        self.session_manager = session_manager
        self.current_search_id: Optional[str] = None
        self._processed_llm_steps: set = set()
        
        if not DEEPSEARCH_AVAILABLE:
            logger.warning("DeepSearch graph module not available - running in mock mode")
    
    async def execute_search(self, query: str, search_id: str) -> str:
        """Execute a search using the DeepSearch system."""
        self.current_search_id = search_id
        # Clear processed LLM steps for new search
        self._processed_llm_steps.clear()
        
        try:
            # Initialize state similar to test_deepsearch.py
            initial_state = {
                "task": query,
                "plan_string": None,
                "steps": [],
                "results": {},
                "sources": None,
                "result": None,
                "intermediate_result": None,
                "search_query": None,
                "needs_replan": False,
                "reflection": None,
                "explaination": None,
                "replan_iter": 0,
                "max_replan_iter": 1,
                "messages": []
            }
            
            logger.info(f"Starting DeepSearch execution for query: {query}")
            
            step_counter = 0
            processed_nodes = set()
            final_state = {}
            
            # Process graph events
            async for event in graph.astream(initial_state, {"recursion_limit": 50}):
                if not (event and isinstance(event, dict) and event):
                    continue
                    
                event_keys = list(event.keys())
                if not event_keys:
                    logger.debug("Received empty event keys, skipping event")
                    continue
                
                try:
                    node_name = event_keys[0]
                    current_state = event.get(node_name, {})
                except (IndexError, KeyError) as e:
                    logger.error(f"Error processing event keys {event_keys}: {e}. Full event: {event}")
                    continue
                
                if current_state:
                    final_state.update(current_state)
                
                if node_name in ['__start__', '__end__']:
                    continue
                
                # Handle master node - check for inline LLM processing  
                if node_name == 'master':
                    previous_llm_count = len(self._processed_llm_steps)
                    await self._handle_master_node(final_state, search_id, step_counter)
                    new_llm_count = len(self._processed_llm_steps)
                    # Increment step counter by number of new LLM steps created
                    step_counter += (new_llm_count - previous_llm_count)
                    continue
                
                step_key = f"{node_name}_{step_counter}"
                if step_key not in processed_nodes:
                    await self._create_step(node_name, final_state, search_id, step_counter)
                    processed_nodes.add(step_key)
                    step_counter += 1
            
            logger.info(f"DeepSearch execution completed for search {search_id}")

            # Create final answer step and collect sources using accumulated final_state
            if final_state and final_state.get("result"):
                try:
                    await self._create_final_step(final_state, search_id, step_counter)
                    await self._collect_sources(search_id)

                    # Extract answer and explanation with better error handling
                    result_content = final_state.get("result", "")
                    answer = None
                    
                    if extract_content and result_content:
                        try:
                            answer = extract_content(result_content, "answer")
                        except Exception as e:
                            logger.warning(f"Failed to extract answer content: {e}")
                            answer = result_content
                    else:
                        answer = result_content
                    
                    explanation = final_state.get("explaination", "")

                    # Return both answer and explanation
                    if explanation and explanation.strip():
                        return explanation
                    elif answer and answer.strip():
                        return answer
                    else:
                        return result_content or "Search completed successfully."
                        
                except Exception as e:
                    logger.error(f"Error processing final result: {e}")
                    # Try to return something useful even if final processing fails
                    return final_state.get("result", "Search completed but encountered issues processing the final result.")

            logger.warning("No result found in final_state")
            return "Search completed but no answer was generated."
            
        except Exception as e:
            logger.error(f"DeepSearch execution failed for search {search_id}: {e}")
            raise DeepSearchIntegrationException(f"Failed to execute search: {str(e)}", graph_error=e)
    
    async def _create_step(self, node_name: str, state: Dict[str, Any], search_id: str, step_counter: int):
        """Create and broadcast a step based on node type and state."""
        try:
            # Map node to step type and generate content
            step_type = {'plan': StepType.PLAN, 'search': StepType.SEARCH, 'code': StepType.CODE, 
                        'llm': StepType.LLM, 'solve': StepType.SOLVE, 'replan': StepType.REPLAN}.get(node_name, StepType.PLAN)
            
            title, content = self._get_step_info(node_name, state)
            metadata = self._get_metadata(node_name, state)
            
            step = ThinkingStep(
                id=f"{search_id}_{node_name}_{step_counter}",
                type=step_type,
                status=StepStatus.RUNNING,
                title=title,
                content=content,
                timestamp=datetime.utcnow(),
                metadata=metadata
            )
            
            # Add and broadcast step
            self.session_manager.add_step(search_id, step)
            await self.websocket_manager.send_step_update(step, search_id)
            
            # Simulate processing time
            await asyncio.sleep(1.0)
            
            # Update with detailed content and mark complete
            step.content = self._get_detailed_content(node_name, state)
            step.status = StepStatus.COMPLETED
            self.session_manager.add_step(search_id, step)
            await self.websocket_manager.send_step_update(step, search_id)
            
        except Exception as e:
            logger.error(f"Error creating step for {node_name}: {e}")
            await self.websocket_manager.send_error(f"Error processing {node_name} step: {str(e)}", search_id=search_id)
    
    def _get_step_info(self, node_name: str, state: Dict[str, Any]) -> tuple[str, str]:
        """Generate step title and initial content."""
        if node_name == 'plan':
            return 'Creating step-by-step research plan', self._format_plan(state.get('plan_string', ''), state.get('steps', []))
        elif node_name == 'search':
            query = state.get('search_query', '')
            title = f"Searching: {query[:50]}{'...' if len(query) > 50 else ''}" if query else 'Performing web search'
            content = f"Executing web search to find information about:\n{query}" if query else "Conducting web research to gather relevant information."
            return title, content
        elif node_name == 'code':
            return 'Executing calculations and data processing', f"Running Python code to process data and perform calculations:\n\nQuery: {state.get('search_query', '')}"
        elif node_name == 'llm':
            query = state.get('search_query', state.get('task', ''))
            title = f"Processing: {query[:50]}{'...' if len(query) > 50 else ''}" if query else 'Processing with AI'
            content = f"Using AI to analyze and process information:\n{query}" if query else "Analyzing information using AI language model."
            return title, content
        elif node_name == 'solve':
            results_count = len(state.get('results', {}))
            return 'Synthesizing final answer from research', f"Analyzing and combining information from {results_count} research steps to generate comprehensive answer."
        elif node_name == 'replan':
            return 'Adjusting research strategy', 'Re-evaluating approach and creating an improved research plan based on current findings.'
        else:
            return f"Processing {node_name.replace('_', ' ').title()}", f"Executing {node_name} step in the research workflow."
    
    def _format_plan(self, plan_string: str, steps: list) -> str:
        """Format plan content concisely."""
        if not plan_string and not steps:
            return "Analyzing the question to determine the best research approach."
        
        if steps:
            step_descriptions = []
            for i, step in enumerate(steps, 1):
                try:
                    if isinstance(step, (list, tuple)) and len(step) >= 4:
                        _, step_name, tool, tool_input = step[0], step[1], step[2], step[3]
                        step_descriptions.append(f"{step_name}. {tool} - {tool_input}")
                    else:
                        logger.warning(f"Step {i} has unexpected format: {step} (type: {type(step)}, length: {len(step) if hasattr(step, '__len__') else 'N/A'})")
                except (IndexError, TypeError) as e:
                    logger.error(f"Error processing step {i}: {step} - Error: {e}")
                    continue
            if step_descriptions:
                return "Research plan created with the following steps:\n" + "\n".join(step_descriptions)
        
        if plan_string:
            return "Research plan:\n" + "\n".join(plan_string.split('\n'))
        
        return "Created a comprehensive research plan to answer your question systematically."
    
    def _get_metadata(self, node_name: str, state: Dict[str, Any]) -> Optional[StepMetadata]:
        """Extract relevant metadata from state."""
        metadata = StepMetadata()
        
        if node_name == 'search':
            metadata.search_query = state.get('search_query')
            sources = state.get('sources')
            if sources:
                processed_sources = []
                for source in sources:
                    if isinstance(source, dict):
                        processed_sources.append({
                            'title': source.get('title', source.get('url', source.get('link', 'Unknown Source'))),
                            'link': source.get('url', source.get('link', ''))
                        })
                    else:
                        processed_sources.append({
                            'title': str(source),
                            'link': str(source) if str(source).startswith('http') else ''
                        })
                metadata.sources = processed_sources
        elif node_name == 'code':
            results = state.get('results')
            if results and len(results) > 0:
                try:
                    results_values = list(results.values())
                    if results_values:
                        latest_result = results_values[-1]
                        if latest_result:
                            metadata.code_result = str(latest_result)
                except (IndexError, KeyError, TypeError) as e:
                    logger.error(f"Error processing code metadata results: {e}. Results: {results}")
                    metadata.code_result = "Code execution completed but results could not be displayed"
        elif node_name == 'llm':
            # Handle LLM results
            llm_result = state.get('result')
            if llm_result:
                metadata.llm_result = str(llm_result)
            intermediate = state.get('intermediate_result')
            if intermediate:
                metadata.code_result = str(intermediate)
            # Also store the search query for LLM steps
            metadata.search_query = state.get('search_query')
        elif node_name == 'plan':
            steps = state.get('steps', [])
            if steps:
                plan_steps = []
                for i, step in enumerate(steps):
                    try:
                        if isinstance(step, (list, tuple)) and len(step) >= 4:
                            step_plan, step_name, tool, tool_input = step[0], step[1], step[2], step[3]
                            plan_steps.append(f"{step_plan} - {step_name} [{tool}]")
                        elif isinstance(step, (list, tuple)) and len(step) >= 3:
                            step_plan, step_name, tool = step[0], step[1], step[2]
                            plan_steps.append(f"{step_plan} - {step_name} [{tool}]")
                        else:
                            logger.warning(f"Plan step {i} has unexpected format: {step} (type: {type(step)}, length: {len(step) if hasattr(step, '__len__') else 'N/A'})")
                    except (IndexError, TypeError) as e:
                        logger.error(f"Error processing plan step {i}: {step} - Error: {e}")
                        continue
                
                metadata.plan_steps = plan_steps
                logger.info(f"Extracted {len(plan_steps)} plan steps for UI progress tracking: {[step[:50] + '...' if len(step) > 50 else step for step in plan_steps]}")
        
        return metadata if any(getattr(metadata, field) for field in metadata.model_fields.keys()) else None
    
    def _get_detailed_content(self, node_name: str, state: Dict[str, Any]) -> str:
        """Get detailed content after processing."""
        if node_name == 'plan':
            steps = state.get('steps', [])
            if steps:
                content = "Research Plan Created:\n\n"
                for i, step in enumerate(steps, 1):
                    try:
                        if isinstance(step, (list, tuple)) and len(step) >= 4:
                            step_plan, step_name, tool, tool_input = step[0], step[1], step[2], step[3]
                            content += f"{i}. {step_name} - Use {tool}\n   └ {tool_input}\n\n"
                        else:
                            logger.warning(f"Detailed content step {i} has unexpected format: {step}")
                    except (IndexError, TypeError) as e:
                        logger.error(f"Error processing detailed content step {i}: {step} - Error: {e}")
                        continue
                return content
            return f"Research Plan:\n\n{state.get('plan_string', 'Creating comprehensive research plan...')}"
        
        elif node_name == 'search':
            search_query = state.get('search_query', '')
            results = state.get('results', {})
            content = f"Search Query: {search_query}\n\n"
            if results and len(results) > 0:
                try:
                    results_keys = list(results.keys())
                    if results_keys:
                        latest_key = results_keys[-1]
                        if latest_key and latest_key in results:
                            result_content = str(results[latest_key])
                            content += f"Search Results:\n{result_content}"
                except (IndexError, KeyError, TypeError) as e:
                    logger.error(f"Error processing search results: {e}. Results: {results}")
                    content += "Search completed but encountered issues displaying results."
            else:
                content += "Gathering and processing search results..."
            return content
        
        elif node_name == 'code':
            task_query = state.get('search_query', '')
            results = state.get('results', {})
            content = f"Code Execution Task: {task_query}\n\n"
            if results and len(results) > 0:
                try:
                    results_keys = list(results.keys())
                    if results_keys:
                        latest_key = results_keys[-1]
                        if latest_key and latest_key in results:
                            result_content = str(results[latest_key])
                            content += f"Code Output:\n{result_content}"
                except (IndexError, KeyError, TypeError) as e:
                    logger.error(f"Error processing code results: {e}. Results: {results}")
                    content += "Code execution completed but encountered issues displaying results."
            else:
                content += "Executing Python code and processing results..."
            return content
        
        elif node_name == 'llm':
            task_query = state.get('search_query', state.get('task', ''))
            result = state.get('result', '')
            intermediate = state.get('intermediate_result', '')
            content = f"LLM Processing Task: {task_query}\n\n" if task_query else "AI Processing:\n\n"
            if result:
                content += f"AI Response:\n{str(result)}\n\n"
            if not result:
                content += "Processing request using AI language model..."
            return content
        
        elif node_name == 'solve':
            research_results = state.get('results', {})
            final_result = state.get('result', '')
            task = state.get('task', '')
            content = f"Question: {task}\n\n"
            if research_results:
                content += f"Synthesizing from {len(research_results)} research steps:\n\n"
                for i, (step_name, result) in enumerate(research_results.items(), 1):
                    result_preview = str(result)
                    content += f"{i}. {step_name}: {result_preview}\n"
                content += "\n"
            content += f"Final Answer:\n{str(final_result)}" if final_result else "Generating comprehensive final answer..."
            return content
        
        elif node_name == 'replan':
            reflection = state.get('reflection', '')
            return f"Reflection on Current Plan:\n\n{reflection}" if reflection else "Analyzing current progress and adjusting research strategy..."
        
        else:
            return f"Processing {node_name} step with current state..."
    
    async def _handle_master_node(self, state: Dict[str, Any], search_id: str, step_counter: int):
        """Handle master node events and detect inline LLM processing."""
        try:
            steps = state.get('steps', [])
            results = state.get('results', {})
            
            if not steps or not results:
                return
            
            # Check all steps to see if any new LLM steps have been completed
            for i, step_info in enumerate(steps):
                if isinstance(step_info, (list, tuple)) and len(step_info) >= 4:
                    _, step_name, tool, tool_input = step_info[0], step_info[1], step_info[2], step_info[3]
                    
                    # If this is an LLM step that has been processed inline and we haven't shown it in UI yet
                    if tool == "LLM" and step_name in results:
                        llm_step_id = f"{search_id}_llm_{step_name}"
                        
                        if llm_step_id not in self._processed_llm_steps:
                            # Create a synthetic state for the LLM step
                            llm_state = {
                                'search_query': tool_input,
                                'task': state.get('task', ''),
                                'result': results.get(step_name, ''),
                                'intermediate_result': results.get(step_name, ''),
                                'results': results,
                                'steps': steps
                            }
                            
                            await self._create_step('llm', llm_state, search_id, step_counter + len(self._processed_llm_steps))
                            self._processed_llm_steps.add(llm_step_id)
                            logger.info(f"Created LLM UI step for {step_name}: {tool_input}")
                        
        except Exception as e:
            logger.error(f"Error handling master node for LLM detection: {e}")

    async def _create_final_step(self, final_state: Dict[str, Any], search_id: str, step_counter: int):
        """Create final result step."""
        try:
            task = final_state.get('task', '')
            result = final_state.get('result', '')
            explanation = final_state.get('explaination', '')

            # Extract clean answer from result
            answer = extract_content(result, "answer") if extract_content else result

            # Create comprehensive content with both answer and explanation
            content = f"Question: {task}\n\n"
            if answer:
                content += f"**Answer:**\n{answer}\n\n"
            if explanation:
                content += f"**Explanation:**\n{explanation}"

            step = ThinkingStep(
                id=f"{search_id}_final_result_{step_counter}",
                type=StepType.SOLVE,
                status=StepStatus.COMPLETED,
                title="Final Answer with Explanation",
                content=content,
                timestamp=datetime.utcnow(),
                metadata=StepMetadata()
            )

            self.session_manager.add_step(search_id, step)
            await self.websocket_manager.send_step_update(step, search_id)
            logger.info(f"Created final result step for search {search_id}")

        except Exception as e:
            logger.error(f"Error creating final result step: {e}")
    
    async def _collect_sources(self, search_id: str):
        """Collect and store all sources from search steps."""
        try:
            search_result = self.session_manager.get_session(search_id)
            if not search_result:
                return
            
            all_sources = []
            seen_links = set()
            
            for step in search_result.steps:
                if step.metadata and step.metadata.sources:
                    for source in step.metadata.sources:
                        if isinstance(source, dict) and 'link' in source:
                            link = source['link']
                            if link and link not in seen_links:
                                all_sources.append(SourceInfo(
                                    title=source.get('title', link),
                                    link=link,
                                    snippet=source.get('snippet')
                                ))
                                seen_links.add(link)
            
            if all_sources:
                search_result.sources = all_sources
                logger.info(f"Collected {len(all_sources)} unique sources for search {search_id}")
        
        except Exception as e:
            logger.error(f"Error collecting sources: {e}")
    
    async def cancel_search(self, search_id: str):
        """Cancel an active search."""
        try:
            self.session_manager.cancel_search(search_id, "User cancelled")
            await self.websocket_manager.send_error("Search was cancelled by user", search_id=search_id)
            logger.info(f"Search {search_id} cancelled successfully")
        except Exception as e:
            logger.error(f"Error cancelling search {search_id}: {e}")
            raise SearchException(f"Failed to cancel search: {str(e)}", search_id=search_id)
    
    async def clear_session(self):
        """Clear the current session for new chat."""
        try:
            self.session_manager.clear_all_sessions()
            await self.websocket_manager.send_session_reset("New chat started")
            self.current_search_id = None
            logger.info("Session cleared successfully")
        except Exception as e:
            logger.error(f"Error clearing session: {e}")
            raise SessionException(f"Failed to clear session: {str(e)}")

def create_adapter(websocket_manager: WebSocketManager, session_manager: SessionManager) -> DeepSearchAdapter:
    return DeepSearchAdapter(websocket_manager, session_manager)