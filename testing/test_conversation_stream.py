"""
Test client for the Conversation Streaming API
This script demonstrates how to connect to the SSE endpoint and receive real-time updates
"""

import requests
import json
import sys
from typing import Optional

class ConversationStreamClient:
    def __init__(self, base_url: str, auth_token: str):
        """
        Initialize the conversation stream client
        
        Args:
            base_url: Base URL of the API (e.g., "http://localhost:5000")
            auth_token: JWT authentication token
        """
        self.base_url = base_url.rstrip('/')
        self.headers = {
            'Authorization': f'Bearer {auth_token}',
            'Accept': 'text/event-stream'
        }
    
    def get_conversation_snapshot(self, conversation_id: str) -> Optional[dict]:
        """
        Get a snapshot of the conversation
        
        Args:
            conversation_id: The ID of the conversation
            
        Returns:
            Dictionary with conversation data or None if error
        """
        url = f'{self.base_url}/api/conversation/{conversation_id}'
        headers = {
            'Authorization': self.headers['Authorization'],
            'Accept': 'application/json'
        }
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            print(f"HTTP Error: {e}")
            print(f"Response: {e.response.text}")
            return None
        except Exception as e:
            print(f"Error: {e}")
            return None
    
    def stream_conversation(self, conversation_id: str):
        """
        Stream conversation updates in real-time
        
        Args:
            conversation_id: The ID of the conversation to stream
        """
        url = f'{self.base_url}/api/conversation/{conversation_id}/stream'
        
        print(f"\n{'='*80}")
        print(f"🔴 LIVE STREAMING: Conversation {conversation_id}")
        print(f"{'='*80}\n")
        
        try:
            with requests.get(url, headers=self.headers, stream=True) as response:
                response.raise_for_status()
                
                event_type = None
                
                for line in response.iter_lines():
                    if not line:
                        continue
                    
                    line = line.decode('utf-8')
                    
                    # Parse SSE format
                    if line.startswith('event:'):
                        event_type = line.split(':', 1)[1].strip()
                        
                    elif line.startswith('data:'):
                        data_str = line.split(':', 1)[1].strip()
                        
                        try:
                            data = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue
                        
                        # Handle different event types
                        if event_type == 'initial':
                            self._handle_initial(data)
                            
                        elif event_type == 'new_messages':
                            self._handle_new_messages(data)
                            
                        elif event_type == 'heartbeat':
                            self._handle_heartbeat(data)
                            
                        elif event_type == 'ended':
                            self._handle_ended(data)
                            print("\n🔴 Stream ended")
                            break
                            
                        elif event_type == 'error':
                            self._handle_error(data)
                            print("\n❌ Stream error, closing connection")
                            break
                        
                        event_type = None
                        
        except requests.exceptions.HTTPError as e:
            print(f"\n❌ HTTP Error: {e}")
            print(f"Response: {e.response.text}")
        except KeyboardInterrupt:
            print("\n\n⚠️  Stream interrupted by user")
        except Exception as e:
            print(f"\n❌ Error: {e}")
    
    def _handle_initial(self, data: dict):
        """Handle initial conversation data"""
        print("📩 INITIAL CONVERSATION DATA")
        print(f"   Conversation ID: {data.get('conversation_id')}")
        print(f"   Call ID: {data.get('call_id')}")
        print(f"   Worker: {data.get('worker_id')}")
        print(f"   Mobile: {data.get('mobile_no')}")
        print(f"   Urgency: {data.get('urgency')}")
        print(f"   Status: {data.get('status')}")
        print(f"   Medium: {data.get('medium')}")
        print(f"   Total Messages: {data.get('total_messages')}")
        
        messages = data.get('messages', [])
        if messages:
            print(f"\n   📝 Message History ({len(messages)} messages):")
            for i, msg in enumerate(messages, 1):
                role_icon = "👤" if msg['role'] == 'user' else "🤖"
                print(f"   {i}. {role_icon} [{msg['timestamp']}] {msg['role'].upper()}")
                print(f"      {msg['content']}")
                if msg.get('sources'):
                    print(f"      📚 Sources: {msg['sources']}")
                print()
    
    def _handle_new_messages(self, data: dict):
        """Handle new messages event"""
        messages = data.get('messages', [])
        print(f"\n🔔 NEW MESSAGE(S) ARRIVED ({len(messages)} new)")
        
        for msg in messages:
            role_icon = "👤" if msg['role'] == 'user' else "🤖"
            print(f"   {role_icon} [{msg['timestamp']}] {msg['role'].upper()}")
            print(f"   {msg['content']}")
            if msg.get('sources'):
                print(f"   📚 Sources: {msg['sources']}")
            print()
        
        print(f"   Total messages now: {data.get('total_messages')}")
        print(f"{'─'*80}")
    
    def _handle_heartbeat(self, data: dict):
        """Handle heartbeat event"""
        print(f"💓 Heartbeat - Connection alive at {data.get('timestamp')}")
    
    def _handle_ended(self, data: dict):
        """Handle conversation ended event"""
        print(f"\n✅ {data.get('message')}")
    
    def _handle_error(self, data: dict):
        """Handle error event"""
        print(f"\n❌ ERROR: {data.get('error')}")


def main():
    """Main function to run the test client"""
    
    # Configuration
    BASE_URL = "http://localhost:5000"
    
    # Get auth token and conversation ID from command line or use defaults
    if len(sys.argv) < 2:
        print("Usage: python test_conversation_stream.py <AUTH_TOKEN> [CONVERSATION_ID]")
        print("\nExample:")
        print("  python test_conversation_stream.py your_jwt_token conv_919325590143_20251003_115804")
        sys.exit(1)
    
    auth_token = sys.argv[1]
    conversation_id = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Create client
    client = ConversationStreamClient(BASE_URL, auth_token)
    
    # If no conversation ID provided, just show usage
    if not conversation_id:
        print("\n⚠️  Please provide a conversation ID as the second argument")
        print("\nExample:")
        print(f"  python test_conversation_stream.py {auth_token} conv_919325590143_20251003_115804")
        sys.exit(1)
    
    # First, get a snapshot (optional)
    print("\n" + "="*80)
    print("📸 FETCHING CONVERSATION SNAPSHOT")
    print("="*80)
    
    snapshot = client.get_conversation_snapshot(conversation_id)
    if snapshot:
        print(f"✅ Snapshot retrieved successfully")
        print(f"   Success: {snapshot.get('success')}")
        conv = snapshot.get('conversation', {})
        print(f"   Total messages: {conv.get('total_messages')}")
        print(f"   Status: {conv.get('status')}")
        print(f"   Urgency: {conv.get('urgency')}")
    else:
        print("❌ Failed to retrieve snapshot")
        print("⚠️  Continuing with streaming anyway...")
    
    # Now stream the conversation
    print("\n" + "="*80)
    print("Starting live stream in 2 seconds...")
    print("Press Ctrl+C to stop streaming")
    print("="*80)
    
    import time
    time.sleep(2)
    
    client.stream_conversation(conversation_id)


if __name__ == "__main__":
    main()
