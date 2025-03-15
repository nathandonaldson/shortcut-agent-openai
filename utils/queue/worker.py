"""
Worker implementation for the Shortcut Enhancement System.

This module provides a background worker that processes tasks from the queue.
"""

import os
import sys
import json
import time
import asyncio
import logging
import signal
import platform
import traceback
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable, Coroutine, Union, Set

from agents import (
    trace, Runner, set_tracing_disabled, 
    set_default_openai_key, set_tracing_export_api_key
)

# Import task queue
from utils.queue.task_queue import task_queue, Task, TaskType, TaskStatus, TaskPriority

# Import workspace context
from context.workspace.workspace_context import WorkspaceContext, WorkflowType

# Import storage utilities
from utils.storage.local_storage import local_storage, get_trace_info

# Import agent functions
from shortcut_agents.triage.triage_agent import process_webhook
from shortcut_agents.analysis.analysis_agent import create_analysis_agent
from shortcut_agents.update.update_agent import create_update_agent

# Import tools
from tools.shortcut.shortcut_tools import get_story_details, add_comment, update_story

# Set up logging
logger = logging.getLogger("task_worker")

class TaskWorker:
    """
    Background worker for processing tasks from the queue.
    
    This class implements a worker that polls the task queue for new tasks
    and processes them using the appropriate agents.
    """
    
    def __init__(
        self,
        worker_id: str = None,
        polling_interval: float = 1.0,
        shutdown_timeout: float = 10.0,
        task_types: Optional[List[str]] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the task worker.
        
        Args:
            worker_id: Worker ID for tracking, defaults to hostname
            polling_interval: Seconds between queue polls
            shutdown_timeout: Seconds to wait for tasks to complete on shutdown
            task_types: List of task types to process, defaults to all
            config: Additional configuration options
        """
        # Generate worker ID if not provided
        self.worker_id = worker_id or f"{platform.node()}-{os.getpid()}"
        
        # Configuration
        self.polling_interval = polling_interval
        self.shutdown_timeout = shutdown_timeout
        self.task_types = task_types or [
            TaskType.TRIAGE,
            TaskType.ANALYSIS,
            TaskType.ENHANCEMENT,
            TaskType.UPDATE
        ]
        self.config = config or {}
        
        # State
        self.running = False
        self.active_tasks: Set[str] = set()
        self.stats = {
            "tasks_processed": 0,
            "tasks_succeeded": 0,
            "tasks_failed": 0,
            "start_time": None,
            "last_task_time": None,
        }
        
        # Set up tracing if Agent SDK is available
        self.setup_tracing()
        
        # Register signal handlers
        self._setup_signal_handlers()
        
        logger.info(f"Initialized TaskWorker {self.worker_id}")
        logger.info(f"Processing task types: {self.task_types}")
    
    def setup_tracing(self):
        """Set up tracing for the worker process."""
        try:
            # Ensure tracing is enabled
            set_tracing_disabled(False)
            
            # Set API keys
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                logger.error("OPENAI_API_KEY not found, tracing will not work")
                raise ValueError("OPENAI_API_KEY environment variable not set")
                
            set_default_openai_key(api_key)
            set_tracing_export_api_key(api_key)
            
            # Import and register the trace processor
            from utils.logging.trace_processor import EnhancementTraceProcessor, setup_trace_processor
            setup_trace_processor()
            logger.info("Registered EnhancementTraceProcessor with OpenAI Agent SDK")
            
            logger.info("Worker tracing configured with OpenAI Agent SDK")
        except Exception as e:
            logger.error(f"Error setting up tracing: {str(e)}")
            raise  # Re-raise the exception to make errors visible
    
    def _setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown"""
        if platform.system() == "Windows":
            # Windows only supports SIGINT and SIGBREAK
            signal.signal(signal.SIGINT, self._handle_shutdown_signal)
            signal.signal(signal.SIGBREAK, self._handle_shutdown_signal)
        else:
            # Unix-like systems support more signals
            signal.signal(signal.SIGINT, self._handle_shutdown_signal)
            signal.signal(signal.SIGTERM, self._handle_shutdown_signal)
            signal.signal(signal.SIGHUP, self._handle_shutdown_signal)
    
    def _handle_shutdown_signal(self, sig, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received shutdown signal {sig}, initiating graceful shutdown")
        self.running = False
    
    async def start(self):
        """Start the worker process"""
        if self.running:
            logger.warning("Worker already running")
            return
        
        self.running = True
        self.stats["start_time"] = datetime.utcnow().isoformat()
        
        logger.info(f"Starting worker {self.worker_id}")
        
        try:
            await self._run_worker()
        except Exception as e:
            logger.error(f"Worker error: {str(e)}")
            traceback.print_exc()
        finally:
            # Cleanup
            logger.info("Worker cleanup")
            await task_queue.close()
    
    async def stop(self):
        """Stop the worker process"""
        if not self.running:
            logger.warning("Worker not running")
            return
        
        logger.info(f"Stopping worker {self.worker_id}")
        self.running = False
        
        # Wait for active tasks to complete
        if self.active_tasks:
            logger.info(f"Waiting for {len(self.active_tasks)} active tasks to complete")
            
            for _ in range(int(self.shutdown_timeout)):
                if not self.active_tasks:
                    break
                await asyncio.sleep(1)
            
            if self.active_tasks:
                logger.warning(f"Shutdown timeout reached with {len(self.active_tasks)} tasks still active")
    
    async def _run_worker(self):
        """Main worker loop"""
        logger.info(f"Worker {self.worker_id} running, polling interval: {self.polling_interval}s")
        
        # Initialize Redis connection early to avoid event loop issues
        redis = await task_queue.get_redis()
        logger.debug("Pre-initialized Redis connection for worker")
        
        while self.running:
            try:
                # Debug: First check if there are any tasks in the queue
                redis = await task_queue.get_redis()
                queue_key = task_queue._get_queue_key("pending")  # Just use pending directly
                pending_count = await redis.zcard(queue_key)
                logger.info(f"Queue {queue_key} has {pending_count} tasks pending")
                
                # Get the next task
                task = await task_queue.get_next_task(self.task_types, self.worker_id)
                
                if task:
                    # Process the task inline instead of creating a new task
                    # This avoids event loop issues
                    self.active_tasks.add(task.task_id)
                    try:
                        logger.info(f"Processing task: {task.task_id} of type {task.task_type}")
                        await self._process_task(task)
                    finally:
                        self.active_tasks.discard(task.task_id)
                else:
                    # No tasks available, wait before polling again
                    logger.debug(f"No tasks available, waiting {self.polling_interval}s...")
                    await asyncio.sleep(self.polling_interval)
            
            except Exception as e:
                logger.error(f"Error in worker loop: {str(e)}")
                # Continue running despite errors
                await asyncio.sleep(self.polling_interval)
    
    async def _process_task(self, task: Task):
        """
        Process a task with the appropriate agent.
        
        Args:
            task: The task to process
        """
        logger.info(f"Processing task {task.task_id} of type {task.task_type}")
        self.stats["tasks_processed"] += 1
        self.stats["last_task_time"] = datetime.utcnow().isoformat()
        
        # Process the task with tracing if available
        try:
            # Get saved trace info if available for cross-process correlation
            trace_info = get_trace_info(task.workspace_id, task.story_id)
            
            # Use saved trace info or create new trace context
            if trace_info and "trace_id" in trace_info:
                # Use the same trace ID from the webhook handler
                trace_id = trace_info["trace_id"]
                workflow_name = trace_info.get("workflow_name", f"Background-{task.task_type}-{task.workspace_id}")
                group_id = trace_info.get("group_id", task.workspace_id)
                
                # Merge metadata from the saved trace with task-specific metadata
                metadata = trace_info.get("metadata", {}).copy()
                metadata.update({
                    "story_id": task.story_id,
                    "task_type": task.task_type,
                    "task_id": task.task_id,
                    "worker_id": self.worker_id
                })
                
                logger.info(f"Using existing trace ID for correlation: {trace_id}")
            else:
                # Create new trace info
                trace_id = f"trace_{task.task_id}"
                workflow_name = f"Background-{task.task_type}-{task.workspace_id}"
                group_id = task.workspace_id
                metadata = {
                    "story_id": task.story_id,
                    "task_type": task.task_type,
                    "task_id": task.task_id,
                    "worker_id": self.worker_id
                }
                
                logger.info(f"Creating new trace for task: {trace_id}")
            
            # Create proper trace for the entire background task process
            with trace(
                workflow_name=workflow_name,
                trace_id=trace_id,
                group_id=group_id,  # Group by workspace
                metadata=metadata
            ):
                # Create the workspace context
                context = self._create_context_from_task(task)
                
                # Process the task based on its type
                if task.task_type == TaskType.TRIAGE:
                    result = await self._process_triage_task(task, context)
                elif task.task_type == TaskType.ANALYSIS:
                    result = await self._process_analysis_task(task, context)
                elif task.task_type == TaskType.ENHANCEMENT:
                    result = await self._process_enhancement_task(task, context)
                else:
                    raise ValueError(f"Unsupported task type: {task.task_type}")
                
                # For simplicity, convert any non-dict results to dict
                if not isinstance(result, dict):
                    if hasattr(result, "model_dump") and callable(getattr(result, "model_dump")):
                        result = result.model_dump() 
                    elif hasattr(result, "dict") and callable(getattr(result, "dict")):
                        result = result.dict()
                    else:
                        result = {"result": str(result)}
                
                # Add task completion metadata
                result["completed_at"] = datetime.utcnow().isoformat()
                result["worker_id"] = self.worker_id
                
                try:
                    # Mark the task as completed
                    await task_queue.complete_task(task, result, self.worker_id)
                    self.stats["tasks_succeeded"] += 1
                    logger.info(f"Task {task.task_id} completed successfully")
                except Exception as completion_error:
                    logger.error(f"Error marking task {task.task_id} as complete: {str(completion_error)}")
                    # Continue since the task was processed
        except Exception as e:
            logger.error(f"Error processing task {task.task_id}: {str(e)}")
            traceback.print_exc()
            self.stats["tasks_failed"] += 1
            
            try:
                # Mark the task as failed
                await task_queue.fail_task(task, str(e), True, self.worker_id)
            except Exception as fail_error:
                logger.error(f"Error marking task {task.task_id} as failed: {str(fail_error)}")
                # Continue execution
    
    def _create_context_from_task(self, task: Task) -> WorkspaceContext:
        """
        Create a workspace context from a task.
        
        Args:
            task: The task to create context for
            
        Returns:
            Workspace context
        """
        # Get API key from environment - try multiple case variations for reliability
        api_key = None
        
        # Try exact case as provided in URL
        if not api_key:
            api_key = os.environ.get(f"SHORTCUT_API_KEY_{task.workspace_id}")
            
        # Try uppercase version
        if not api_key:
            api_key = os.environ.get(f"SHORTCUT_API_KEY_{task.workspace_id.upper()}")
            
        # Try lowercase version
        if not api_key:
            api_key = os.environ.get(f"SHORTCUT_API_KEY_{task.workspace_id.lower()}")
            
        # Fall back to the default API key
        if not api_key:
            api_key = os.environ.get("SHORTCUT_API_KEY")
        
        # Log which key we're using
        if api_key:
            logger.info(f"Using API key for workspace: {task.workspace_id}")
        else:
            raise ValueError(f"No API key found for workspace {task.workspace_id}")
        
        # Create context
        context = WorkspaceContext(
            workspace_id=task.workspace_id,
            api_key=api_key,
            story_id=task.story_id
        )
        
        # Set story data if available
        if "story_data" in task.payload:
            context.set_story_data(task.payload["story_data"])
        
        # Set the workflow type if specified
        if "workflow_type" in task.payload:
            workflow_type = task.payload["workflow_type"]
            if workflow_type == "enhance":
                context.set_workflow_type(WorkflowType.ENHANCE)
            elif workflow_type in ["analyse", "analyze"]:
                context.set_workflow_type(WorkflowType.ANALYSE)
        
        # Set request ID for tracing
        context.request_id = task.task_id
        
        return context
    
    async def _process_triage_task(self, task: Task, context: WorkspaceContext) -> Dict[str, Any]:
        """
        Process a triage task.
        
        Args:
            task: The task to process
            context: The workspace context
            
        Returns:
            Processing result
        """
        # Extract webhook data from task
        webhook_data = task.payload.get("webhook_data", {})
        
        # Log the webhook data
        logger.info(f"Processing triage task for story {context.story_id}")
        
        try:
            # First try to import the new triage agent
            from shortcut_agents.triage.triage_agent import create_triage_agent, process_webhook
            agent = create_triage_agent()
            
            # Check if webhook_data contains a nested 'data' field (common in webhook logs)
            if "data" in webhook_data and isinstance(webhook_data["data"], dict):
                # Extract story ID from the outer structure for context
                if "story_id" in webhook_data and not context.story_id:
                    context.story_id = webhook_data["story_id"]
            
            # Use the process_webhook function instead of calling run directly on the agent
            result = await process_webhook(webhook_data, context)
            
            # Extract the actual result from the nested structure if needed
            triage_result = result.get("result", result)
            
            # Log the extracted result for debugging
            logger.info(f"Triage result: {triage_result}")
            
            # Check if the result indicates processing is needed
            processed = triage_result.get("processed", False)
            workflow = triage_result.get("workflow")
            
            # Check if a handoff was already processed
            handoff = triage_result.get("handoff")
            if handoff:
                logger.info(f"Handoff already processed by triage agent to {handoff.get('target', 'unknown agent')}")
                # Skip creating additional tasks since the handoff has already been handled
                return triage_result
            
            if processed and workflow:
                if workflow == "enhance":
                    logger.info(f"Enhancement workflow determined for story {context.story_id} - scheduling enhancement task")
                    context.set_workflow_type(WorkflowType.ENHANCE)
                    await self._schedule_enhancement_task(context)
                elif workflow in ["analyse", "analyze"]:
                    logger.info(f"Analysis workflow determined for story {context.story_id} - scheduling analysis task")
                    context.set_workflow_type(WorkflowType.ANALYSE)
                    await self._schedule_analysis_task(context)
            
            return triage_result
        
        except Exception as e:
            logger.error(f"Error in triage: {str(e)}")
            
            # Try the fallback implementation if there was an error
            try:
                logger.info("Trying fallback triage implementation")
                # Create a simplified triage result
                from context.workspace.workspace_context import WorkflowType
                
                # Check for analyse/analyze label in webhook data
                has_analyse_label = False
                has_enhance_label = False
                
                # Extract the actual webhook data if it's nested
                actual_webhook_data = webhook_data
                if "data" in webhook_data and isinstance(webhook_data["data"], dict):
                    actual_webhook_data = webhook_data["data"]
                
                # Check in references section
                if "references" in actual_webhook_data:
                    for ref in actual_webhook_data.get("references", []):
                        if ref.get("entity_type") == "label" and ref.get("name", "").lower() in ["analyse", "analyze"]:
                            has_analyse_label = True
                            logger.info(f"Found analyse label in references: {ref.get('name')}")
                        elif ref.get("entity_type") == "label" and ref.get("name", "").lower() == "enhance":
                            has_enhance_label = True
                            logger.info(f"Found enhance label in references: {ref.get('name')}")
                
                # Also check in actions if available
                if "actions" in actual_webhook_data and isinstance(actual_webhook_data["actions"], list):
                    for action in actual_webhook_data["actions"]:
                        if action.get("action") == "update" and "changes" in action:
                            changes = action.get("changes", {})
                            
                            # Check for label_ids format
                            if "label_ids" in changes and "adds" in changes["label_ids"]:
                                adds = changes["label_ids"]["adds"]
                                if isinstance(adds, list) and "references" in actual_webhook_data:
                                    for reference in actual_webhook_data["references"]:
                                        if (reference.get("entity_type") == "label" and 
                                            reference.get("id") in adds):
                                            label_name = reference.get("name", "").lower()
                                            if label_name in ["analyse", "analyze"]:
                                                has_analyse_label = True
                                                logger.info(f"Found analyse label in label_ids: {reference.get('name')}")
                                            elif label_name == "enhance":
                                                has_enhance_label = True
                                                logger.info(f"Found enhance label in label_ids: {reference.get('name')}")
                
                if has_analyse_label:
                    logger.info(f"Analysis workflow determined for story {context.story_id} - scheduling analysis task")
                    context.set_workflow_type(WorkflowType.ANALYSE)
                    await self._schedule_analysis_task(context)
                    return {
                        "processed": True,
                        "workflow": "analyse",
                        "next_workflow": "analysis",
                        "story_id": context.story_id,
                        "workspace_id": context.workspace_id
                    }
                elif has_enhance_label:
                    logger.info(f"Enhancement workflow determined for story {context.story_id} - scheduling enhancement task")
                    context.set_workflow_type(WorkflowType.ENHANCE)
                    await self._schedule_enhancement_task(context)
                    return {
                        "processed": True,
                        "workflow": "enhance",
                        "next_workflow": "enhancement",
                        "story_id": context.story_id,
                        "workspace_id": context.workspace_id
                    }
                else:
                    logger.info(f"No relevant labels found for story {context.story_id}")
                    return {
                        "processed": False,
                        "reason": "No relevant labels found",
                        "story_id": context.story_id,
                        "workspace_id": context.workspace_id
                    }
            except Exception as fallback_error:
                logger.error(f"Error in fallback triage: {str(fallback_error)}")
                raise
        
        return result
    
    async def _process_analysis_task(self, task: Task, context: WorkspaceContext) -> Dict[str, Any]:
        """
        Process an analysis task.
        
        Args:
            task: Analysis task
            context: Workspace context
            
        Returns:
            Analysis result
        """
        logger.info(f"Processing analysis task for story {context.story_id}")
        
        # Check if this story already has analysis results
        existing_analysis = context.get_analysis_results()
        if existing_analysis:
            logger.warning(f"Story {context.story_id} already has analysis results, skipping duplicate analysis")
            return {
                "status": "skipped",
                "reason": "Duplicate analysis detected",
                "story_id": context.story_id,
                "workspace_id": context.workspace_id
            }
        
        # Get story data if not in context
        if not context.story_data:
            logger.info(f"Fetching story data for {context.story_id}")
            story_data = await get_story_details(context.story_id, context.api_key)
            context.set_story_data(story_data)
        
        # Create analysis agent
        analysis_agent = create_analysis_agent()
        
        # Run analysis
        analysis_result = await analysis_agent.run(context.story_data, context)
        
        # Format the analysis as a comment
        logger.info(f"Adding analysis results as a comment to story {context.story_id}")
        comment_text = self._format_analysis_comment(analysis_result.get("result", {}), context)
        
        # Add comment to story
        comment_result = await add_comment(context.story_id, context.api_key, comment_text)
        
        # Update story labels
        if context.workflow_type == WorkflowType.ANALYSE:
            logger.info(f"Updating labels for story {context.story_id} (analysis workflow)")
            label_update = {
                "labels": {
                    "adds": [{"name": "analysed"}],
                    "removes": [{"name": "analyse"}, {"name": "analyze"}]
                }
            }
            
            try:
                await update_story(context.story_id, context.api_key, label_update)
            except Exception as e:
                logger.error(f"Error updating labels: {str(e)}")
                # Continue despite label update errors
        
        # Return combined results
        return {
            "status": "completed",
            "story_id": context.story_id,
            "workspace_id": context.workspace_id,
            "result": analysis_result,
            "comment": comment_result
        }
    
    async def _process_enhancement_task(self, task: Task, context: WorkspaceContext) -> Dict[str, Any]:
        """
        Process an enhancement task.
        
        Args:
            task: Enhancement task
            context: Workspace context
            
        Returns:
            Enhancement result
        """
        logger.info(f"Processing enhancement task for story {context.story_id}")
        
        # Get story data if not in context
        if not context.story_data:
            logger.info(f"Fetching story data for {context.story_id}")
            story_data = await get_story_details(context.story_id, context.api_key)
            context.set_story_data(story_data)
        
        # Step 1: Run analysis if not already done
        if not context.analysis_results:
            logger.info(f"Running analysis for story {context.story_id}")
            analysis_agent = create_analysis_agent()
            analysis_result = await analysis_agent.run(context.story_data, context)
            analysis_data = analysis_result.get("result", {})
            
            # Set analysis results in context
            context.set_analysis_results(analysis_data)
            
            # Add analysis comment
            logger.info(f"Adding analysis results as a comment to story {context.story_id}")
            analysis_comment = self._format_analysis_comment(analysis_data, context)
            await add_comment(context.story_id, context.api_key, analysis_comment)
        else:
            analysis_data = context.analysis_results
        
        # Step 2: Run update agent to generate enhancements
        logger.info(f"Running update agent for story {context.story_id}")
        update_agent = create_update_agent()
        enhancement_input = {
            "story_data": context.story_data,
            "analysis_results": context.analysis_results
        }
        update_result = await update_agent.run(enhancement_input, context)
        enhancement_data = update_result.get("result", {})
        
        # Step 3: Apply enhancements to the story
        logger.info(f"Applying enhancements to story {context.story_id}")
        
        # Prepare update data
        update_data = {}
        if "enhanced_title" in enhancement_data and enhancement_data["enhanced_title"]:
            update_data["name"] = enhancement_data["enhanced_title"]
        
        if "enhanced_description" in enhancement_data and enhancement_data["enhanced_description"]:
            update_data["description"] = enhancement_data["enhanced_description"]
        
        # Update the story if we have changes
        update_story_result = None
        if update_data:
            logger.info(f"Updating story content: {update_data.keys()}")
            try:
                update_story_result = await update_story(context.story_id, context.api_key, update_data)
            except Exception as e:
                logger.error(f"Error updating story content: {str(e)}")
                # Continue despite update errors
        
        # Step 4: Add enhancement comment
        logger.info(f"Adding enhancement summary comment to story {context.story_id}")
        enhancement_comment = self._format_enhancement_comment(enhancement_data)
        comment_result = await add_comment(context.story_id, context.api_key, enhancement_comment)
        
        # Step 5: Update story labels
        logger.info(f"Updating labels for story {context.story_id} (enhancement workflow)")
        label_update = {
            "labels": {
                "adds": [{"name": "enhanced"}],
                "removes": [{"name": "enhance"}, {"name": "enhancement"}]
            }
        }
        
        try:
            await update_story(context.story_id, context.api_key, label_update)
        except Exception as e:
            logger.error(f"Error updating labels: {str(e)}")
            # Continue despite label update errors
        
        # Return results
        return {
            "analysis": analysis_data,
            "enhancement": enhancement_data,
            "updated_fields": list(update_data.keys()) if update_data else [],
            "comment_id": comment_result.get("id") if comment_result else None
        }
    
    async def _schedule_analysis_task(self, context: WorkspaceContext):
        """
        Schedule an analysis task.
        
        Args:
            context: Workspace context
        """
        task = Task(
            workspace_id=context.workspace_id,
            story_id=context.story_id,
            task_type=TaskType.ANALYSIS,
            priority=TaskPriority.NORMAL,
            payload={
                "story_data": context.story_data,
                "workflow_type": "analyse"
            }
        )
        
        await task_queue.add_task(task)
    
    async def _schedule_enhancement_task(self, context: WorkspaceContext):
        """
        Schedule an enhancement task.
        
        Args:
            context: Workspace context
        """
        task = Task(
            workspace_id=context.workspace_id,
            story_id=context.story_id,
            task_type=TaskType.ENHANCEMENT,
            priority=TaskPriority.NORMAL,
            payload={
                "story_data": context.story_data,
                "workflow_type": "enhance"
            }
        )
        
        await task_queue.add_task(task)
    
    def _format_analysis_comment(self, analysis_results: Dict[str, Any], context: WorkspaceContext) -> str:
        """
        Format analysis results as a Markdown comment.
        
        Args:
            analysis_results: Analysis results
            context: Workspace context
            
        Returns:
            Formatted comment text
        """
        # Start building the comment
        comment = f"## 📊 Story Analysis Results\n\n"
        
        # Overall score
        overall_score = analysis_results.get('overall_score', 'N/A')
        comment += f"**Overall Quality Score**: {overall_score}/10\n\n"
        
        # Summary
        summary = analysis_results.get('summary', 'No summary provided')
        comment += f"### Summary\n{summary}\n\n"
        
        # Title analysis
        title_analysis = analysis_results.get('title_analysis', {})
        if title_analysis:
            title_score = title_analysis.get('score', 'N/A')
            comment += f"### Title Analysis\n**Score**: {title_score}/10\n\n"
            
            strengths = title_analysis.get('strengths', [])
            if strengths:
                comment += "**Strengths**:\n"
                for strength in strengths:
                    comment += f"- {strength}\n"
                comment += "\n"
                
            weaknesses = title_analysis.get('weaknesses', [])
            if weaknesses:
                comment += "**Weaknesses**:\n"
                for weakness in weaknesses:
                    comment += f"- {weakness}\n"
                comment += "\n"
                
            recommendations = title_analysis.get('recommendations', [])
            if recommendations:
                comment += "**Recommendations**:\n"
                for rec in recommendations:
                    comment += f"- {rec}\n"
                comment += "\n"
        
        # Description analysis
        desc_analysis = analysis_results.get('description_analysis', {})
        if desc_analysis:
            desc_score = desc_analysis.get('score', 'N/A')
            comment += f"### Description Analysis\n**Score**: {desc_score}/10\n\n"
            
            strengths = desc_analysis.get('strengths', [])
            if strengths:
                comment += "**Strengths**:\n"
                for strength in strengths:
                    comment += f"- {strength}\n"
                comment += "\n"
                
            weaknesses = desc_analysis.get('weaknesses', [])
            if weaknesses:
                comment += "**Weaknesses**:\n"
                for weakness in weaknesses:
                    comment += f"- {weakness}\n"
                comment += "\n"
                
            recommendations = desc_analysis.get('recommendations', [])
            if recommendations:
                comment += "**Recommendations**:\n"
                for rec in recommendations:
                    comment += f"- {rec}\n"
                comment += "\n"
        
        # Acceptance criteria analysis
        ac_analysis = analysis_results.get('acceptance_criteria_analysis', {})
        if ac_analysis:
            ac_score = ac_analysis.get('score', 'N/A')
            comment += f"### Acceptance Criteria Analysis\n**Score**: {ac_score}/10\n\n"
            
            strengths = ac_analysis.get('strengths', [])
            if strengths:
                comment += "**Strengths**:\n"
                for strength in strengths:
                    comment += f"- {strength}\n"
                comment += "\n"
                
            weaknesses = ac_analysis.get('weaknesses', [])
            if weaknesses:
                comment += "**Weaknesses**:\n"
                for weakness in weaknesses:
                    comment += f"- {weakness}\n"
                comment += "\n"
                
            recommendations = ac_analysis.get('recommendations', [])
            if recommendations:
                comment += "**Recommendations**:\n"
                for rec in recommendations:
                    comment += f"- {rec}\n"
                comment += "\n"
        
        # Priority areas
        priority_areas = analysis_results.get('priority_areas', [])
        if priority_areas:
            comment += "### Priority Areas for Improvement\n"
            for area in priority_areas:
                comment += f"- {area}\n"
            comment += "\n"
        
        # Add footer
        comment += "\n---\n"
        comment += "Powered by Shortcut Enhancement System | "
        comment += f"[View Story](https://app.shortcut.com/{context.workspace_id}/story/{context.story_id})"
        
        return comment
    
    def _format_enhancement_comment(self, enhancement_data: Dict[str, Any]) -> str:
        """
        Format enhancement results as a Markdown comment.
        
        Args:
            enhancement_data: Enhancement data
            
        Returns:
            Formatted comment text
        """
        # Start building the comment
        comment = "## ✨ Story Enhancement Applied\n\n"
        comment += "This story has been enhanced to improve clarity, structure, and completeness.\n\n"
        
        # List changes made
        changes = enhancement_data.get("changes_made", [])
        if changes:
            comment += "### Changes Made\n"
            for change in changes:
                if change:  # Only add non-empty changes
                    comment += f"- {change}\n"
            comment += "\n"
        
        # Add footer
        comment += "\n_Enhanced by the Shortcut Enhancement System_"
        
        return comment
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get worker statistics.
        
        Returns:
            Dictionary with worker statistics
        """
        # Calculate uptime
        uptime_seconds = 0
        if self.stats["start_time"]:
            start_time = datetime.fromisoformat(self.stats["start_time"])
            uptime_seconds = (datetime.utcnow() - start_time).total_seconds()
        
        # Add real-time stats
        stats = self.stats.copy()
        stats.update({
            "worker_id": self.worker_id,
            "running": self.running,
            "active_tasks": len(self.active_tasks),
            "uptime_seconds": uptime_seconds,
            "task_types": self.task_types
        })
        
        return stats

async def run_worker(worker_id: str = None, polling_interval: float = 1.0):
    """
    Run a worker process.
    
    Args:
        worker_id: Worker ID for tracking
        polling_interval: Seconds between queue polls
    """
    worker = TaskWorker(worker_id=worker_id, polling_interval=polling_interval)
    
    try:
        await worker.start()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, stopping worker")
    finally:
        await worker.stop()

def main():
    """Main entry point for the worker process"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Task Worker for Shortcut Enhancement System")
    parser.add_argument("--worker-id", help="Worker ID for tracking")
    parser.add_argument("--polling-interval", type=float, default=1.0, help="Seconds between queue polls")
    parser.add_argument("--task-types", help="Comma-separated list of task types to process")
    
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Parse task types
    task_types = None
    if args.task_types:
        task_types = [t.strip() for t in args.task_types.split(",")]
    
    # Run the worker
    asyncio.run(run_worker(args.worker_id, args.polling_interval))

if __name__ == "__main__":
    main()