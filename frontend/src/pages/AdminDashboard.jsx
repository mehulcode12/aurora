import React, { useState } from 'react';
import { Shield, MessageSquare, FileText, Archive, Settings, MessageCircle, Clock, Users, TrendingUp, CheckCircle, RefreshCw } from 'lucide-react';

// Conversation Card Component
const ConversationCard = ({ conversation, onTakeOver }) => {
  const getPriorityStyles = (priority) => {
    switch (priority) {
      case 'critical':
        return 'bg-red-50 border-red-200';
      case 'urgent':
        return 'bg-yellow-50 border-yellow-200';
      case 'normal':
        return 'bg-white border-gray-200';
      default:
        return 'bg-white border-gray-200';
    }
  };

  const getDurationColor = (priority) => {
    switch (priority) {
      case 'critical':
        return 'text-red-600';
      case 'urgent':
        return 'text-yellow-600';
      default:
        return 'text-gray-600';
    }
  };

  return (
    <div className={`${getPriorityStyles(conversation.priority)} border rounded-lg p-4 mb-3 transition hover:shadow-md `}>
      <div className="flex items-start justify-between">
        <div className="flex items-start space-x-3 flex-1">
          <img 
            src={conversation.userAvatar} 
            alt={conversation.userName}
            className="w-10 h-10 rounded-full border-2 border-white shadow"
          />
          <div className="flex-1">
            <h3 className="font-semibold text-gray-900 mb-1">{conversation.title}</h3>
            <p className="text-sm text-gray-600">User: {conversation.userName}</p>
          </div>
        </div>
        
        <div className="text-right ml-4">
          <p className={`text-sm font-medium mb-2 ${getDurationColor(conversation.priority)}`}>
            Duration: {conversation.duration}
          </p>
          <button 
            onClick={() => onTakeOver(conversation.id)}
            className="px-4 py-1.5 bg-blue-600 text-white rounded-md text-sm font-semibold hover:bg-blue-700 transition"
          >
            Take Over
          </button>
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

export default function AdminDashboard() {
  const [activeTab, setActiveTab] = useState('conversations');
  const [conversations, setConversations] = useState([
    {
      id: 1,
      title: 'Routine Equipment Check',
      userName: 'Alex Chen',
      userAvatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=Alex',
      duration: '00:05:12',
      priority: 'normal'
    },
    {
      id: 2,
      title: 'Standard Procedure Inquiry',
      userName: 'Maria Rodriguez',
      userAvatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=Maria',
      duration: '00:08:45',
      priority: 'normal'
    },
    {
      id: 3,
      title: 'Urgent System Malfunction',
      userName: 'David Lee',
      userAvatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=David',
      duration: '00:02:30',
      priority: 'urgent'
    },
    {
      id: 4,
      title: 'Critical Safety Hazard',
      userName: 'Sarah Johnson',
      userAvatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=Sarah',
      duration: '00:01:15',
      priority: 'critical'
    }
  ]);

  const handleTakeOver = (conversationId) => {
    console.log('Taking over conversation:', conversationId);
    // Handle takeover logic here
  };

  const handleLiveUpdate = () => {
    console.log('Refreshing live data...');
    // Handle live update logic here
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-white to-slate-50">
      {/* Sidebar */}
      <div className="fixed z-0 left-0 h-full w-64 bg-white border-r border-gray-200 shadow-lg mt-6">
        <div className="p-6">
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

            <button
              onClick={() => setActiveTab('logs')}
              className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg transition ${
                activeTab === 'logs'
                  ? 'bg-blue-50 text-blue-600 font-semibold'
                  : 'text-gray-700 hover:bg-gray-50'
              }`}
            >
              <FileText className="w-5 h-5" />
              <span>Logs</span>
            </button>

            <button
              onClick={() => setActiveTab('archive')}
              className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg transition ${
                activeTab === 'archive'
                  ? 'bg-blue-50 text-blue-600 font-semibold'
                  : 'text-gray-700 hover:bg-gray-50'
              }`}
            >
              <Archive className="w-5 h-5" />
              <span>Compliance Archive</span>
            </button>

            <button
              onClick={() => setActiveTab('settings')}
              className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg transition ${
                activeTab === 'settings'
                  ? 'bg-blue-50 text-blue-600 font-semibold'
                  : 'text-gray-700 hover:bg-gray-50'
              }`}
            >
              <Settings className="w-5 h-5" />
              <span>Settings</span>
            </button>

            <button
              className="w-full flex items-center space-x-3 px-4 py-3 rounded-lg text-gray-700 hover:bg-gray-50 transition"
            >
              <MessageCircle className="w-5 h-5" />
              <span>Feedback</span>
            </button>
          </nav>
        </div>

        <div className="absolute bottom-0 left-0 right-0 p-6 border-t border-gray-200 bg-gray-50">
          <div className="flex items-center space-x-3">
            <img 
              src="https://api.dicebear.com/7.x/avataaars/svg?seed=Admin" 
              alt="Admin"
              className="w-10 h-10 rounded-full border-2 border-white shadow"
            />
            <div>
              <p className="text-sm font-semibold text-gray-900">Admin User</p>
              <p className="text-xs text-gray-500">supervisor@company.com</p>
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
              className="px-6 py-2 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition shadow-lg shadow-blue-600/30 flex items-center "
            >
              <RefreshCw className="w-5 h-5" />
              <span>Live Update</span>
            </button>
          </div>
        </div>
        
        <div className=" flex justify-between mb-10">
            {/* Dashboard Metrics */}
            <div className='flex w-full gap-10'> 
            <div className="bg-white rounded-2xl shadow-xl p-6 border border-gray-200  w-[70%] ">
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
                
                <div className="bg-white rounded-lg p-4 border border-gray-200 shadow-sm w-[25%] mb-4">
                  <div className="flex items-center justify-between ">
                    <div className="w-10 h-8 bg-red-600 rounded-lg flex items-center justify-center">
                      <MessageSquare className="w-5 h-5 text-white" />
                    </div>
                  </div>
                  <p className="text-sm text-gray-600 mb-1">Active Issues</p>
                  <div className="flex items-baseline space-x-2">
                    <div className="h-8 flex-1 bg-gray-100 rounded overflow-hidden">
                      <div 
                        className="h-full bg-gradient-to-r from-red-500 to-orange-500 transition-all"
                        style={{ width: `${(conversations.length / 10) * 100}%` }}
                      ></div>
                      <p className="text-2xl font-bold text-gray-900">{conversations.length}</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Queries Solved */}
            <div className="bg-gradient-to-br from-blue-600 to-blue-800 rounded-2xl shadow-xl p-6 text-white w-[25%]">
              <h2 className="text-xl font-bold mb-2">Queries Solved</h2>
              <p className="text-3xl font-bold">247</p>
              <div className="space-y-2 text-sm">
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
        <div className="grid grid-cols-2 gap-8">
          {/* Left Column - Conversations */}
          <div className="col-span-2">
            <div className="bg-white rounded-2xl shadow-xl p-6 border border-gray-200">
              <h2 className="text-2xl font-bold text-gray-900 mb-6">Ongoing Conversations</h2>
              
              <div>
                {conversations.map((conversation) => (
                  <ConversationCard
                    key={conversation.id}
                    conversation={conversation}
                    onTakeOver={handleTakeOver}
                  />
                ))}
              </div>

              {conversations.length === 0 && (
                <div className="text-center py-12">
                  <MessageSquare className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                  <p className="text-gray-500 font-medium">No active conversations</p>
                  <p className="text-sm text-gray-400 mt-1">All clear! No emergencies at the moment.</p>
                </div>
              )}
            </div>
          </div>

          {/* Right Column - Metrics */}
          
        </div>
      </div>
    </div>
  );
}