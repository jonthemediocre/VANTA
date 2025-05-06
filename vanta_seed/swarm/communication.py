"""
Defines the communication layer for the distributed swarm.

Provides an abstraction for different communication backends (e.g., ZeroMQ, WebSockets, gRPC)
to facilitate message passing between the orchestrator and agent nodes.

Message Structure (Example):
{
    'type': 'task_assignment' | 'state_update' | 'result_report' | 'control_signal',
    'source_id': 'orchestrator' | 'node_id',
    'target_id': 'node_id' | 'orchestrator' | 'broadcast',
    'timestamp': 'iso_timestamp',
    'payload': { ... specific data ... }
}
"""

import abc
import asyncio
import json
import time
from typing import Dict, Any, Callable, Awaitable
import zmq
import zmq.asyncio
from datetime import datetime

# ----------------------------------------
# Message Schema Definitions (Draft)
# ----------------------------------------
# TASK_ASSIGNMENT:
# {
#     'type': 'task_assignment',
#     'source_id': 'orchestrator',
#     'target_id': 'node_id',       # Specific agent node ID
#     'timestamp': 'iso_timestamp',
#     'payload': {
#         'task_id': 'unique_task_id',
#         'agent_id': 'agent_to_run_on_node', # e.g., 'DataUnifierAgent-1'
#         'ritual_name': 'e.g., deduplicate_and_merge',
#         'input_data': { ... },    # Data needed for the agent's ritual
#         'policy_version': 'optional_policy_version_to_use'
#     }
# }
#
# RESULT_REPORT:
# {
#     'type': 'result_report',
#     'source_id': 'node_id',       # ID of the reporting agent node
#     'target_id': 'orchestrator',
#     'timestamp': 'iso_timestamp',
#     'payload': {
#         'task_id': 'original_task_id',
#         'status': 'completed' | 'failed' | 'in_progress',
#         'result_data': { ... },   # Output data from the agent's ritual
#         'metrics': { ... },       # Performance metrics (duration, reward, etc.)
#         'error_message': 'optional_error_details_if_failed'
#     }
# }
#
# POLICY_UPDATE:
# {
#     'type': 'policy_update',
#     'source_id': 'orchestrator',
#     'target_id': 'broadcast',     # Or specific node_id
#     'timestamp': 'iso_timestamp',
#     'payload': {
#         'policy_version': 'new_policy_version_id',
#         'policy_data': { ... }    # Serialized policy data (e.g., model weights)
#     }
# }
#
# NODE_STATUS: # Node informs orchestrator about its state
# {
#     'type': 'node_status',
#     'source_id': 'node_id',
#     'target_id': 'orchestrator',
#     'timestamp': 'iso_timestamp',
#     'payload': {
#         'status': 'idle' | 'busy' | 'error' | 'starting' | 'stopping',
#         'available_agents': ['agent_id_1', 'agent_id_2'],
#         'load': {'cpu': 0.5, 'memory': 0.6}, # Optional load info
#         'current_task_id': 'task_id_if_busy'
#     }
# }
# ----------------------------------------

class CommunicationBus(abc.ABC):
    """Abstract base class for a communication bus using explicit patterns."""
    def __init__(self, node_id: str):
        self.node_id = node_id
        self._message_callback = None # Renamed for clarity

    def set_message_callback(self, callback: Callable[[Dict[str, Any]], Awaitable[None]]):
        """Sets the callback function for processing incoming messages via listen()."""
        self._message_callback = callback

    async def _process_incoming_message(self, message_data: bytes): # Renamed for clarity
        """Internal helper to decode and process a received message via listen()."""
        if not self._message_callback:
            print(f"Warning ({self.node_id}): No callback set for received message.")
            return
        try:
            message = json.loads(message_data.decode('utf-8'))
            # Basic validation (can be expanded)
            if not all(k in message for k in ['type', 'source_id', 'target_id', 'timestamp', 'payload']):
                 print(f"Warning ({self.node_id}): Received malformed message: {message}")
                 return
            # Pass the full message dictionary to the callback
            await self._message_callback(message)
        except json.JSONDecodeError:
            print(f"Error ({self.node_id}): Could not decode received message: {message_data[:100]}...")
        except Exception as e:
            print(f"Error ({self.node_id}): Exception processing message: {e}")


    @abc.abstractmethod
    async def connect(self):
        """Establish connection to the communication infrastructure."""
        raise NotImplementedError

    @abc.abstractmethod
    async def disconnect(self):
        """Disconnect from the communication infrastructure."""
        raise NotImplementedError

    # --- Pattern-Based Sending Methods ---

    @abc.abstractmethod
    async def publish(self, topic: str, message_type: str, payload: Dict[str, Any]):
        """Publish a message to a topic (Pub/Sub pattern). Usually Orchestrator -> Nodes."""
        raise NotImplementedError

    @abc.abstractmethod
    async def push(self, message_type: str, payload: Dict[str, Any]):
        """Push a message to a destination (Push/Pull pattern). Usually Node -> Orchestrator."""
        raise NotImplementedError

    # --- Receiving Method ---

    @abc.abstractmethod
    async def listen(self):
        """Start listening for incoming messages (blocking or runs in background).
        Uses the message_callback set via set_message_callback()."""
        raise NotImplementedError

    # --- Helper ---

    def _create_message(self, target_id: str, message_type: str, payload: Dict[str, Any]) -> bytes:
        """Helper to construct a standardized message."""
        message = {
            'type': message_type,
            'source_id': self.node_id,
            'target_id': target_id, # Target for pub/sub is the topic/broadcast, target for push is orchestrator
            'timestamp': datetime.utcnow().isoformat(),
            'payload': payload
        }
        return json.dumps(message).encode('utf-8')


class ZeroMQCommunicationBus(CommunicationBus):
    """Implementation of the CommunicationBus using ZeroMQ (PUB/SUB, PUSH/PULL)."""

    def __init__(self, node_id: str, orchestrator_pub_address: str, orchestrator_pull_address: str):
        """
        Initializes the ZeroMQ bus.

        Args:
            node_id: Unique identifier for this node/orchestrator.
            orchestrator_pub_address: Full address the orchestrator PUB socket binds/connects to (e.g., 'tcp://*:5555' for bind, 'tcp://localhost:5555' for connect).
            orchestrator_pull_address: Full address the orchestrator PULL socket binds/connects to (e.g., 'tcp://*:5556' for bind, 'tcp://localhost:5556' for connect).
        """
        super().__init__(node_id)
        self.orchestrator_pub_addr = orchestrator_pub_address
        self.orchestrator_pull_addr = orchestrator_pull_address
        self.is_orchestrator = node_id.lower() == 'orchestrator'

        # ZMQ Context and sockets
        self.context = zmq.asyncio.Context()
        self.sub_socket = self.context.socket(zmq.SUB) # Node: receives tasks/policy from Orchestrator PUB
        self.push_socket = self.context.socket(zmq.PUSH) # Node: sends results to Orchestrator PULL

        # Orchestrator-specific sockets (if this instance is the orchestrator)
        self.pub_socket = None # Orchestrator: publishes tasks/policy
        self.pull_socket = None # Orchestrator: pulls results from nodes

        # Configure based on role
        if self.is_orchestrator:
            self.pub_socket = self.context.socket(zmq.PUB)
            self.pull_socket = self.context.socket(zmq.PULL)
            print(f"Orchestrator ZeroMQ Bus Initialized: PUB on {self.orchestrator_pub_addr}, PULL on {self.orchestrator_pull_addr}")
        else: # Agent Node
             print(f"Agent Node ({self.node_id}) ZeroMQ Bus Initialized: SUB from {self.orchestrator_pub_addr}, PUSH to {self.orchestrator_pull_addr}")


    async def connect(self):
        """Connect sockets based on role."""
        try:
            if self.is_orchestrator:
                self.pub_socket.bind(self.orchestrator_pub_addr)
                self.pull_socket.bind(self.orchestrator_pull_addr)
                print(f"Orchestrator sockets bound.")
            else: # Agent Node
                # Connect to Orchestrator's PUB socket for tasks/policy
                self.sub_socket.connect(self.orchestrator_pub_addr)
                # Subscribe to messages targeted specifically at this node ID OR broadcast
                self.sub_socket.subscribe(self.node_id.encode('utf-8')) # Specific topic = node_id
                self.sub_socket.subscribe(b'broadcast') # General broadcast topic
                print(f"Node {self.node_id}: Subscribed to {self.orchestrator_pub_addr} for topics '{self.node_id}' and 'broadcast'")

                # Connect to Orchestrator's PULL socket for sending results
                self.push_socket.connect(self.orchestrator_pull_addr)
                print(f"Node {self.node_id}: Connected PUSH socket to {self.orchestrator_pull_addr}")

            print(f"{self.node_id} ZeroMQ connection established.")
            # Short delay for connections/subscriptions to establish reliably
            await asyncio.sleep(0.5)

        except zmq.ZMQError as e:
            print(f"Error ({self.node_id}) connecting ZeroMQ sockets: {e}")
            # Potentially add retry logic or specific error handling here
            raise # Re-raise for higher level handling


    async def disconnect(self):
        """Close all sockets."""
        print(f"Disconnecting {self.node_id} ZeroMQ sockets...")
        sockets_to_close = [self.sub_socket, self.push_socket, self.pub_socket, self.pull_socket]
        for sock in sockets_to_close:
            if sock and not sock.closed:
                sock.close()
        # Only terminate context after all sockets are closed
        if not self.context.closed:
             self.context.term()
        print(f"{self.node_id} ZeroMQ disconnected.")

    async def publish(self, topic: str, message_type: str, payload: Dict[str, Any]):
        """Publish a message using the PUB socket (Orchestrator only)."""
        if not self.is_orchestrator:
            print(f"Warning (Node {self.node_id}): Cannot publish messages.")
            return

        # Target ID for publish messages is the topic itself (e.g., 'broadcast' or specific 'node_id')
        message_bytes = self._create_message(topic, message_type, payload)
        try:
            # Publish with topic as the routing key
            await self.pub_socket.send_multipart([topic.encode('utf-8'), message_bytes])
            # print(f"Orchestrator published to topic '{topic}': {message_type}") # Verbose
        except zmq.ZMQError as e:
             print(f"Error (Orchestrator) publishing message: {e}")


    async def push(self, message_type: str, payload: Dict[str, Any]):
        """Push a message to the orchestrator using the PUSH socket (Node only)."""
        if self.is_orchestrator:
             print(f"Warning (Orchestrator): Orchestrator should not use push(). Use publish() instead.")
             return

        # Target ID for push messages is always the orchestrator
        message_bytes = self._create_message('orchestrator', message_type, payload)
        try:
             await self.push_socket.send(message_bytes)
             # print(f"Node {self.node_id} pushed to orchestrator: {message_type}") # Verbose
        except zmq.ZMQError as e:
             print(f"Error (Node {self.node_id}) pushing message: {e}")


    async def listen(self):
        """Listen for incoming messages on SUB (for Nodes) or PULL (for Orchestrator) sockets."""
        listener_socket = None
        role = "Orchestrator" if self.is_orchestrator else f"Node {self.node_id}"

        if self.is_orchestrator:
            listener_socket = self.pull_socket # Orchestrator listens on PULL socket for results from nodes
            print(f"{role} starting PULL listener loop on {self.orchestrator_pull_addr}...")
        else:
            listener_socket = self.sub_socket # Node listens on SUB socket for tasks/policy from orchestrator
            print(f"{role} starting SUB listener loop from {self.orchestrator_pub_addr}...")

        if not listener_socket:
             print(f"Error ({role}): Listener socket not initialized.")
             return # Cannot listen

        try:
            while True:
                if self.is_orchestrator:
                    # PULL socket receives single part messages
                    message_data = await listener_socket.recv()
                    await self._process_incoming_message(message_data)
                else:
                    # SUB socket receives multipart messages [topic, message_body]
                    topic_bytes, message_data = await listener_socket.recv_multipart()
                    # print(f"{role} received on topic '{topic_bytes.decode()}': processing...") # Verbose
                    await self._process_incoming_message(message_data)

        except asyncio.CancelledError:
            print(f"{role} listener loop cancelled.")
        except zmq.ZMQError as e:
             # Handle common errors like context termination during shutdown
             if e.errno == zmq.ETERM:
                 print(f"{role} listener loop terminated due to ZeroMQ context termination.")
             else:
                 print(f"Error ({role}) in listener loop: {e}")
                 # Consider more robust error handling/reconnection logic here
        except Exception as e: # Catch other potential errors during processing
            print(f"Unexpected error in {role} listener loop: {e}")
        finally:
            print(f"{role} listener loop stopped.")


class WebSocketCommunicationBus(CommunicationBus):
    """Placeholder implementation for WebSockets."""

    async def connect(self):
        print(f"Connecting {self.node_id} via WebSockets (Placeholder)...")

    async def disconnect(self):
        print(f"Disconnecting {self.node_id} via WebSockets (Placeholder)...")

    async def publish(self, topic: str, message_type: str, payload: Dict[str, Any]):
        message_bytes = self._create_message(topic, message_type, payload)
        print(f"Publishing to topic '{topic}' via WebSockets (Placeholder): {message_type}")

    async def push(self, message_type: str, payload: Dict[str, Any]):
        message_bytes = self._create_message('orchestrator', message_type, payload)
        print(f"Pushing message via WebSockets (Placeholder): {message_type}")

    async def listen(self):
        print(f"Listening for WebSocket messages ({self.node_id}) (Placeholder - No actual listening)...")
        while True:
            # Simulate receiving messages for testing if callback is set
            # if self._message_callback:
            #    dummy_type = 'task_assignment' if self.node_id != 'orchestrator' else 'result_report'
            #    dummy_source = 'orchestrator' if self.node_id != 'orchestrator' else 'dummy_node_ws'
            #    dummy_target = self.node_id if self.node_id != 'orchestrator' else 'orchestrator'
            #    message = self._create_message(dummy_target, dummy_type, {'data': 'ws_ping'})
            #    # Need to encode/decode if simulating bytes
            #    await self._process_incoming_message(json.dumps(message).encode('utf-8'))
            await asyncio.sleep(10) # Check periodically


</rewritten_file> 