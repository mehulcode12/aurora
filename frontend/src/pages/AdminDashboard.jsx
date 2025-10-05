import React, { useState, useEffect, useRef, createContext, useContext } from 'react';
import { Shield, MessageSquare, FileText, Archive, Settings, MessageCircle, Clock, Users, TrendingUp, RefreshCw, User, Phone, X, ArrowLeft } from 'lucide-react';
import { UserContext } from '../App';
import { fetchConversationUsingId } from '../services/conversationServices/conversationServices';
import { fetchConversations } from '../services/conversationServices/conversationServices';
import { useNavigate } from 'react-router-dom';

// Conversation Card Component
const ConversationCard = ({ conversation, onOpenConversation }) => {
  const getPriorityStyles = (urgency) => {
    switch (urgency) {
      case 'CRITICAL':
        return 'bg-red-50 border-red-200';
      case 'HIGH':
        return 'bg-yellow-50 border-yellow-200';
      case 'MEDIUM':
        return 'bg-blue-50 border-blue-200';
      case 'LOW':
      default:
        return 'bg-white border-gray-200';
    }
  };

  const getDurationColor = (urgency) => {
    switch (urgency) {
      case 'CRITICAL':
        return 'text-red-600';
      case 'HIGH':
        return 'text-yellow-600';
      case 'MEDIUM':
        return 'text-blue-600';
      default:
        return 'text-gray-600';
    }
  };

  const getUrgencyBadge = (urgency) => {
    const colors = {
      CRITICAL: 'bg-red-100 text-red-800 border-red-300',
      HIGH: 'bg-yellow-100 text-yellow-800 border-yellow-300',
      MEDIUM: 'bg-blue-100 text-blue-800 border-blue-300',
      LOW: 'bg-gray-100 text-gray-800 border-gray-300'
    };
    return colors[urgency] || colors.LOW;
  };

  const calculateDuration = (timestamp, lastMessageAt) => {
    const start = new Date(timestamp);
    const end = new Date(lastMessageAt);
    const diffMs = end - start;
    const diffMins = Math.floor(diffMs / 60000);
    const diffSecs = Math.floor((diffMs % 60000) / 1000);
    return `${diffMins}m ${diffSecs}s`;
  };

  const duration = calculateDuration(conversation.timestamp, conversation.last_message_at);

  return (
    <div className={`${getPriorityStyles(conversation.urgency)} border rounded-lg p-4 mb-3 transition hover:shadow-md`}>
      <div className="flex items-start justify-between">
        <div className="flex items-start space-x-3 flex-1">
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-400 to-blue-600 flex items-center justify-center text-white font-semibold shadow">
            <User size={20} />
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <h3 className="font-semibold text-gray-900">Conversation {conversation.conversation_id}</h3>
              <span className={`px-2 py-0.5 text-xs font-medium rounded-full border ${getUrgencyBadge(conversation.urgency)}`}>
                {conversation.urgency}
              </span>
            </div>
            <div className="flex items-center gap-3 text-sm text-gray-600">
              <span className="flex items-center gap-1">
                <Phone size={14} />
                {conversation.mobile_no}
              </span>
              <span className="flex items-center gap-1">
                <span className={`w-2 h-2 rounded-full ${conversation.status === 'ACTIVE' ? 'bg-green-500' : 'bg-gray-400'}`}></span>
                {conversation.status}
              </span>
            </div>
            <p className="text-xs text-gray-500 mt-1">
              Worker: {conversation.worker_id}
            </p>
          </div>
        </div>
        
        <div className="text-right ml-4">
          <p className={`text-sm font-medium mb-1 flex items-center justify-end gap-1 ${getDurationColor(conversation.urgency)}`}>
            <Clock size={14} />
            {duration}
          </p>
          <p className="text-xs text-gray-500 mb-2">{conversation.medium}</p>
          <button 
            onClick={() => onOpenConversation(conversation.conversation_id)}
            className="px-3 py-1.5 bg-blue-600 text-white rounded-md text-sm font-semibold hover:bg-blue-700 transition"
          >
            Open Conversation
          </button>
        </div>
      </div>
    </div>
  );
};

// Message Component
const MessageBubble = ({ message }) => {
  const isUser = message.role === 'user';
  const isAdmin = message.content.startsWith('Admin');
  
  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div className={`flex ${isUser ? 'flex-row-reverse' : 'flex-row'} items-start gap-2 max-w-[70%]`}>
        <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
          isUser ? 'bg-blue-600' : isAdmin ? 'bg-purple-600' : 'bg-gray-600'
        }`}>
          <User size={16} className="text-white" />
        </div>
        <div>
          <div className={`rounded-lg px-4 py-2 ${
            isUser 
              ? 'bg-blue-600 text-white' 
              : isAdmin 
                ? 'bg-purple-50 text-gray-900 border border-purple-200'
                : 'bg-gray-100 text-gray-900'
          }`}>
            {isAdmin && (
              <p className="text-xs font-semibold text-purple-700 mb-1">
                Admin Intervention
              </p>
            )}
            <p className="text-sm">{message.content}</p>
          </div>
          <p className={`text-xs text-gray-500 mt-1 ${isUser ? 'text-right' : 'text-left'}`}>
            {formatTime(message.timestamp)}
          </p>
        </div>
      </div>
    </div>
  );
};

// Conversation View Component
const ConversationView = ({ conversationData, onClose, token }) => {
  const [messages, setMessages] = useState(conversationData.messages || []);
  const [isLiveStreaming, setIsLiveStreaming] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const eventSourceRef = useRef(null);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const startLiveStream = async () => {
    if (eventSourceRef.current) {
      stopLiveStream();
    }

    // const conversationId = conversationData.conversation_id;
    // const url = ;

    try {
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Accept': 'text/event-stream',
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      setIsLiveStreaming(true);
      setConnectionStatus('connected');

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      const readStream = async () => {
        try {
          while (true) {
            const { done, value } = await reader.read();
            
            if (done) {
              console.log('Stream ended');
              setIsLiveStreaming(false);
              setConnectionStatus('disconnected');
              break;
            }

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
              if (line.startsWith('event:')) {
                const eventType = line.slice(6).trim();
                continue;
              }
              
              if (line.startsWith('data:')) {
                const data = line.slice(5).trim();
                
                try {
                  const parsedData = JSON.parse(data);
                  
                  // Handle different event types
                  if (parsedData?.messages) {
                    if (parsedData?.conversation_id) {
                      // Initial data or new messages
                      if (parsedData?.messages?.length > 0) {
                        setMessages(prevMessages => {
                          const existingIds = new Set(prevMessages.map(m => m.message_id));
                          const newMessages = parsedData.messages.filter(m => !existingIds.has(m.message_id));
                          return [...prevMessages, ...newMessages];
                        });
                      }
                    }
                  }
                  
                  // Handle heartbeat
                  if (parsedData.timestamp && parsedData.status === 'connected') {
                    setConnectionStatus('connected');
                  }
                } catch (e) {
                  console.log('Non-JSON data:', data);
                }
              }
            }
          }
        } catch (error) {
          console.error('Stream reading error:', error);
          setConnectionStatus('error');
          setIsLiveStreaming(false);
        }
      };

      eventSourceRef.current = { reader, abort: () => reader.cancel() };
      readStream();

    } catch (error) {
      console.error('SSE connection error:', error);
      setConnectionStatus('error');
      setIsLiveStreaming(false);
    }
  };

  const stopLiveStream = () => {
    if (eventSourceRef.current?.abort) {
      eventSourceRef.current.abort();
      eventSourceRef.current = null;
    }
    setIsLiveStreaming(false);
    setConnectionStatus('disconnected');
  };

  useEffect(() => {
    // Initial load of messages
    setMessages(conversationData.messages || []);
    
    return () => {
      if (eventSourceRef.current?.abort) {
        eventSourceRef.current.abort();
      }
    };
  }, [conversationData]);

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-4xl h-[90vh] flex flex-col">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-blue-700 text-white p-6 rounded-t-2xl">
          <div className="flex items-center justify-between mb-4">
            <button
              onClick={onClose}
              className="hover:bg-blue-500 p-2 rounded-lg transition"
            >
              <ArrowLeft size={20} />
            </button>
            <div className="flex items-center gap-3">
              {/* Live Stream Status */}
              <div className="flex items-center gap-2 px-3 py-1.5 bg-blue-500 bg-opacity-50 rounded-lg">
                <span className={`w-2 h-2 rounded-full ${
                  connectionStatus === 'connected' ? 'bg-green-400 animate-pulse' :
                  connectionStatus === 'error' ? 'bg-red-400' :
                  'bg-gray-400'
                }`}></span>
                <span className="text-sm font-medium">
                  {connectionStatus === 'connected' ? 'Live' :
                   connectionStatus === 'error' ? 'Error' :
                   'Offline'}
                </span>
              </div>
              
              {/* Live Stream Toggle Button */}
              <button
                onClick={isLiveStreaming ? stopLiveStream : startLiveStream}
                className={`px-4 py-2 rounded-lg font-semibold transition flex items-center gap-2 ${
                  isLiveStreaming 
                    ? 'bg-red-500 hover:bg-red-600' 
                    : 'bg-green-500 hover:bg-green-600'
                }`}
              >
                {isLiveStreaming ? (
                  <>
                    <span className="w-2 h-2 bg-white rounded-full animate-pulse"></span>
                    Stop Live
                  </>
                ) : (
                  <>
                    <Clock size={16} />
                    Start Live
                  </>
                )}
              </button>
              
              <button
                onClick={onClose}
                className="hover:bg-blue-500 p-2 rounded-lg transition"
              >
                <X size={20} />
              </button>
            </div>
          </div>
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <h2 className="text-2xl font-bold mb-2">
                Conversation {conversationData.conversation_id}
              </h2>
              <div className="flex items-center gap-4 text-sm text-blue-100">
                <span className="flex items-center gap-1">
                  <Phone size={14} />
                  {conversationData.mobile_no}
                </span>
                <span className="flex items-center gap-1">
                  <span className={`w-2 h-2 rounded-full ${
                    conversationData.status === 'ACTIVE' ? 'bg-green-400' : 'bg-gray-400'
                  }`}></span>
                  {conversationData.status}
                </span>
                <span>{conversationData.medium}</span>
              </div>
              <p className="text-xs text-blue-200 mt-2">
                Worker: {conversationData.worker_id}
              </p>
            </div>
            <div className={`px-3 py-1 rounded-full text-sm font-semibold ${
              conversationData.urgency === 'CRITICAL' ? 'bg-red-500' :
              conversationData.urgency === 'HIGH' ? 'bg-yellow-500 text-gray-900' :
              conversationData.urgency === 'MEDIUM' ? 'bg-blue-500' :
              'bg-gray-500'
            }`}>
              {conversationData.urgency}
            </div>
          </div>
        </div>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-6 bg-gray-50">
          {messages && messages?.length > 0 ? (
            <>
              {messages.map((message) => (
                <MessageBubble key={message.message_id} message={message} />
              ))}
              <div ref={messagesEndRef} />
            </>
          ) : (
            <div className="text-center text-gray-500 py-12">
              <MessageSquare size={48} className="mx-auto mb-4 text-gray-300" />
              <p>No messages yet</p>
            </div>
          )}
        </div>

        {/* Footer with Status */}
        <div className="border-t border-gray-200 p-4 bg-white rounded-b-2xl">
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-600">
              Total messages: <span className="font-semibold">{messages?.length || 0}</span>
            </p>
            {isLiveStreaming && (
              <div className="flex items-center gap-2 text-green-600">
                <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                <span className="text-sm font-semibold">Live updates active</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

// Metric Card Component
const MetricCard = ({ icon: Icon, label, value, color, trend }) => {
  return (
    <div className="bg-white rounded-lg p-4 border border-gray-200 shadow-sm w-1/3">
      <div className="flex items-start justify-between mb-2">
        <div className={`w-10 h-10 ${color} rounded-lg flex items-center justify-center`}>
          <Icon className="w-5 h-5 text-white" />
        </div>
        {trend && (
          <span className="text-xs text-green-600 font-semibold flex items-center">
            <TrendingUp className="w-3 h-3 mr-1" />
            +{trend}%
          </span>
        )}
      </div>
      <p className="text-sm text-gray-600 mb-1">{label}</p>
      <p className="text-2xl font-bold text-gray-900">{value}</p>
    </div>
  );
};

// Main Dashboard Component
export default function AdminDashboard() {
  const [activeTab, setActiveTab] = useState('conversations');
  const [selectedConversation, setSelectedConversation] = useState(null);
  
  // Mock token for demonstration - replace with actual token from your app
  const {token,user,setToken,setUser} =useContext(UserContext);
  const navigate = useNavigate();

  const [conversations,setConversation] = useState([
    {
      "call_id": "call_001",
      "worker_id": "A4648KcygjVxPQGk9vvP",
      "mobile_no": "+91-9876543210",
      "conversation_id": "conv_001",
      "urgency": "CRITICAL",
      "status": "ACTIVE",
      "timestamp": "2025-10-01T08:15:00+05:30",
      "medium": "Voice",
      "last_message_at": "2025-10-01T08:18:45+05:30",
      "admin_id": "T1R2Hg70TBbH3qthFBwBNZewlz53"
    },
    {
      call_id: "call_002",
      worker_id: "B91fPZL5qzT8SmjH7kUe",
      mobile_no: "+91-9988776655",
      conversation_id: "conv_002",
      urgency: "HIGH",
      status: "ACTIVE",
      timestamp: "2025-10-01T09:20:00+05:30",
      medium: "Voice",
      last_message_at: "2025-10-01T09:23:12+05:30",
      admin_id: "Y8kZsR42hQvLn9DxFc3PdWm0rT57"
    },
    {
      call_id: "call_005",
      worker_id: "E8bV5tRwQmS2yNzC3kHp",
      mobile_no: "+91-9822001100",
      conversation_id: "conv_005",
      urgency: "CRITICAL",
      status: "ACTIVE",
      timestamp: "2025-10-01T12:30:00+05:30",
      medium: "Video",
      last_message_at: "2025-10-01T12:34:58+05:30",
      admin_id: "K6vWq3Dn5RzF8xLyJ1bPpM4tG92E"
    },
    {
      call_id: "call_007",
      worker_id: "G5pM8cZwDfE1nRbS0qLx",
      mobile_no: "+91-9887766554",
      conversation_id: "conv_007",
      urgency: "MEDIUM",
      status: "ACTIVE",
      timestamp: "2025-10-01T14:05:00+05:30",
      medium: "Chat",
      last_message_at: "2025-10-01T14:08:17+05:30",
      admin_id: "R4mXq8VnJ5hK2dTwY1cLzP9fE63B"
    }
  ]);

  const handleOpenConversation = async (conversation_id) => {
    console.log('Opening conversation:', conversation_id);
    // In production, you would fetch the conversation data from your API here
    // For demo purposes, we're using the sample data

    const conversationData = await fetchConversationUsingId(conversation_id,token);
    console.log("Fetched Conversation Data:", conversationData);
    setSelectedConversation(conversationData?.conversation);
  };

  const handleLiveUpdate = async() => {
    const conversations = await fetchConversations(token,user);
    setConversation(conversations?.active_calls);
    console.log('Refreshing live data...');
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setToken(null);
    setUser(null);
    
    // Optionally clear context if needed
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-white to-slate-50">
      {/* Sidebar */}
      <div className="fixed z-0 left-0 h-full w-64 bg-white border-r border-gray-200 shadow-lg flex flex-col justify-between">
        <div>
          <div className="p-6 mt-6">
            <nav className="space-y-2">
              <button
                onClick={() => setActiveTab('conversations')}
                className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg transition ${
                  activeTab === 'conversations'
                    ? 'bg-blue-50 text-blue-600 font-semibold'
                    : 'text-gray-700 hover:bg-gray-50'
                }`}
              >
                <MessageSquare className="w-5 h-5" />
                <span>Active Conversations</span>
              </button>
            </nav>
          </div>
        </div>
        <div>
          <div className="absolute bottom-0 left-0 right-0 p-6 border-t border-gray-200 bg-gray-50">
            <button
              onClick={handleLogout}
              className="w-full px-4 py-3 bg-red-600 text-white rounded-lg font-semibold hover:bg-red-700 transition flex items-center justify-center gap-2"
            >
              <X className="w-5 h-5" />
              <span>Logout</span>
            </button>
          </div>
          <div className="absolute bottom-24 left-0 right-0 p-6 border-t border-gray-200 bg-gray-50">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-400 to-purple-600 flex items-center justify-center text-white font-semibold">
                <User size={20} />
              </div>
              <div>
                <p className="text-xs text-gray-500">{user.email}</p>
                <p className="text-sm font-semibold text-gray-900">{user.designation}</p>
              </div>
            </div>
          </div>
          
        </div>
      </div>

      {/* Main Content */}
      <div className="ml-64 p-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-2">
            <div>
              <h1 className="text-4xl font-bold text-gray-900 mb-2">Active Conversations</h1>
              <p className="text-gray-600">Real-time overview of all ongoing customer interactions</p>
            </div>
            <button 
              onClick={handleLiveUpdate}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition shadow-lg shadow-blue-600/30 flex items-center gap-2"
            >
              <RefreshCw className="w-5 h-5" />
              <span>Live Update</span>
            </button>
          </div>
        </div>
        
        <div className="flex justify-between mb-10">
          <div className='flex w-full gap-10'> 
            <div className="bg-white rounded-2xl shadow-xl p-6 border border-gray-200 w-[70%]">
              <h2 className="text-xl font-bold text-gray-900 mb-4">Dashboard Metrics</h2>
              <div className="space-y-4 flex justify-between">
                <MetricCard
                  icon={Users}
                  label="Agents Online"
                  value="15"
                  color="bg-blue-600"
                />
                
                <MetricCard
                  icon={Clock}
                  label="Average Handle Time"
                  value="03:45"
                  color="bg-green-600"
                  trend="12"
                />
                
                <div className="bg-white rounded-lg p-4 border border-gray-200 shadow-sm w-[25%]">
                  <div className="w-10 h-8 bg-red-600 rounded-lg flex items-center justify-center mb-2">
                    <MessageSquare className="w-5 h-5 text-white" />
                  </div>
                  <p className="text-sm text-gray-600 mb-1">Active Issues</p>
                  <p className="text-2xl font-bold text-gray-900">{conversations?.length}</p>
                </div>
              </div>
            </div>

            <div className="bg-gradient-to-br from-blue-600 to-blue-800 rounded-2xl shadow-xl p-6 text-white w-[25%]">
              <h2 className="text-xl font-bold mb-2">Queries Solved</h2>
              <p className="text-3xl font-bold">247</p>
              <div className="space-y-2 text-sm mt-4">
                <div className="flex justify-between">
                  <span className="text-blue-200">Today</span>
                  <span className="font-semibold">34</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-blue-200">This Week</span>
                  <span className="font-semibold">156</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-blue-200">This Month</span>
                  <span className="font-semibold">247</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-2xl shadow-xl p-6 border border-gray-200">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">Ongoing Conversations</h2>
          
          <div>
            {conversations && conversations.map((conversation) => (
              <ConversationCard
                key={conversation.conversation_id}
                conversation={conversation}
                onOpenConversation={handleOpenConversation}
              />
            ))}
          </div>

          {conversations?.length === 0 && (
            <div className="text-center py-12">
              <MessageSquare className="w-16 h-16 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500 font-medium">No active conversations</p>
              <p className="text-sm text-gray-400 mt-1">All clear! No emergencies at the moment.</p>
            </div>
          )}
        </div>
      </div>

      {/* Conversation Modal */}
      {selectedConversation && (
        <ConversationView
          conversationData={selectedConversation}
          onClose={() => setSelectedConversation(null)}
          token={token}
        />
      )}
    </div>
  );
}