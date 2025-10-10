import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { apiService } from '../../services/apiService';
import './StudentMessages.css';

const StudentMessages = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);

  // Helper function to check if current user owns the message
  const isMessageOwner = (message, currentUser) => {
    // If message has sender object, use that for comparison
    if (message.sender && message.sender.id) {
      return message.sender.id === currentUser?.id;
    }
    
    // If message has sender_id, use that
    if (message.sender_id) {
      return message.sender_id === currentUser?.id;
    }
    
    // Fallback: check if this is a sent message type
    return message.type === 'sent';
  };
  const [conversations, setConversations] = useState([]);
  const [selectedConversation, setSelectedConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [sending, setSending] = useState(false);
  const [availableUsers, setAvailableUsers] = useState([]);
  const [showNewChatModal, setShowNewChatModal] = useState(false);
  const [newChatUser, setNewChatUser] = useState('');
  const [hasNewMessages, setHasNewMessages] = useState(false);
  const [lastMessageCount, setLastMessageCount] = useState(0);
  const [isPageVisible, setIsPageVisible] = useState(true);
  const [originalTitle, setOriginalTitle] = useState('');
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [messageToDelete, setMessageToDelete] = useState(null);
  const [deletingMessage, setDeletingMessage] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [messageToEdit, setMessageToEdit] = useState(null);
  const [editingMessage, setEditingMessage] = useState(false);
  const [editedContent, setEditedContent] = useState('');
  const [showDeleteConversationModal, setShowDeleteConversationModal] = useState(false);
  const [conversationToDelete, setConversationToDelete] = useState(null);
  const [deletingConversation, setDeletingConversation] = useState(false);
  const messagesEndRef = useRef(null);
  const refreshIntervalRef = useRef(null);
  const notificationSoundRef = useRef(null);

  useEffect(() => {
    // Save original title
    setOriginalTitle(document.title);
    
    // Request notification permission
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission();
    }
    
    loadConversations();
    loadAvailableUsers();
    startAutoRefresh();

    // Page visibility change handler
    const handleVisibilityChange = () => {
      setIsPageVisible(!document.hidden);
      if (!document.hidden) {
        // Reset title and new message indicator when page becomes visible
        document.title = originalTitle;
        setHasNewMessages(false);
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);

    // Cleanup on unmount
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      if (refreshIntervalRef.current) {
        clearInterval(refreshIntervalRef.current);
      }
      document.title = originalTitle;
    };
  }, [originalTitle]);

  useEffect(() => {
    if (selectedConversation) {
      loadConversationMessages(selectedConversation.userId);
    }
  }, [selectedConversation]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);


  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // Silent version for auto-refresh (doesn't show loading)
  const loadConversationsQuietly = useCallback(async () => {
    try {
      const [inboxResponse, sentResponse] = await Promise.all([
        apiService.getInboxMessages(),
        apiService.getSentMessages()
      ]);

      const allMessages = [
        ...inboxResponse.messages.map(m => ({ ...m, type: 'received' })),
        ...sentResponse.messages.map(m => ({ ...m, type: 'sent' }))
      ];

      const conversationMap = new Map();
      
      allMessages.forEach(message => {
        const partnerId = message.type === 'received' ? message.sender.id : message.recipient.id;
        const partnerInfo = message.type === 'received' ? message.sender : message.recipient;
        
        if (!conversationMap.has(partnerId)) {
          conversationMap.set(partnerId, {
            userId: partnerId,
            userInfo: partnerInfo,
            lastMessage: message,
            unreadCount: 0,
            messages: []
          });
        }
        
        const conversation = conversationMap.get(partnerId);
        if (new Date(message.created_at) > new Date(conversation.lastMessage.created_at)) {
          conversation.lastMessage = message;
        }
        
        if (message.type === 'received' && !message.is_read) {
          conversation.unreadCount++;
        }
      });

      const conversationList = Array.from(conversationMap.values())
        .sort((a, b) => new Date(b.lastMessage.created_at) - new Date(a.lastMessage.created_at));

      // Check for new messages
      const currentMessageCount = allMessages.length;

      setLastMessageCount(currentMessageCount);
      setConversations(conversationList);

      // Update page title with unread count
      const totalUnread = conversationList.reduce((sum, conv) => sum + conv.unreadCount, 0);
      if (totalUnread > 0 && document.hidden) {
        document.title = `(${totalUnread}) New message${totalUnread > 1 ? 's' : ''} - Chat`;
      } else if (!document.hidden) {
        document.title = 'Chat';
      }

      // Auto-refresh current conversation if needed
      // We'll handle this in a separate effect to avoid dependency issues

    } catch (err) {
      console.error('Failed to refresh conversations:', err);
    }
  }, []);

  // Auto refresh conversations for new messages
  const startAutoRefresh = useCallback(() => {
    refreshIntervalRef.current = setInterval(() => {
      loadConversationsQuietly();
    }, 5000); // Check every 5 seconds
  }, [loadConversationsQuietly]);

  const playNotificationSound = () => {
    try {
      // Create a subtle notification sound using Web Audio API
      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();
      
      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);
      
      oscillator.frequency.setValueAtTime(800, audioContext.currentTime);
      oscillator.frequency.setValueAtTime(600, audioContext.currentTime + 0.1);
      
      gainNode.gain.setValueAtTime(0, audioContext.currentTime);
      gainNode.gain.linearRampToValueAtTime(0.1, audioContext.currentTime + 0.01);
      gainNode.gain.exponentialRampToValueAtTime(0.001, audioContext.currentTime + 0.2);
      
      oscillator.start(audioContext.currentTime);
      oscillator.stop(audioContext.currentTime + 0.2);
    } catch (error) {
      console.log('Audio notification not available');
    }
  };

  const showDesktopNotification = (message) => {
    if ('Notification' in window && Notification.permission === 'granted' && !isPageVisible) {
      const senderName = message.sender?.nickname || message.sender?.name || 'Someone';
      const notification = new Notification(`New message from ${senderName}`, {
        body: message.message.substring(0, 100) + (message.message.length > 100 ? '...' : ''),
        icon: '/favicon.ico',
        tag: 'chat-message'
      });

      notification.onclick = () => {
        window.focus();
        notification.close();
      };

      // Auto close after 5 seconds
      setTimeout(() => notification.close(), 5000);
    }
  };

  const updatePageTitle = (unreadCount) => {
    if (unreadCount > 0 && !isPageVisible) {
      document.title = `(${unreadCount}) New message${unreadCount > 1 ? 's' : ''} - Chat`;
      setHasNewMessages(true);
    } else if (isPageVisible) {
      document.title = originalTitle || 'Chat';
      setHasNewMessages(false);
    }
  };

  const loadConversations = async () => {
    try {
      setLoading(true);
      const [inboxResponse, sentResponse] = await Promise.all([
        apiService.getInboxMessages(),
        apiService.getSentMessages()
      ]);

      // Combine and group messages by conversation partner
      const allMessages = [
        ...inboxResponse.messages.map(m => ({ ...m, type: 'received' })),
        ...sentResponse.messages.map(m => ({ ...m, type: 'sent' }))
      ];

      // Group by conversation partner
      const conversationMap = new Map();
      
      allMessages.forEach(message => {
        const partnerId = message.type === 'received' ? message.sender.id : message.recipient.id;
        const partnerInfo = message.type === 'received' ? message.sender : message.recipient;
        
        if (!conversationMap.has(partnerId)) {
          conversationMap.set(partnerId, {
            userId: partnerId,
            userInfo: partnerInfo,
            lastMessage: message,
            unreadCount: 0,
            messages: []
          });
        }
        
        const conversation = conversationMap.get(partnerId);
        if (new Date(message.created_at) > new Date(conversation.lastMessage.created_at)) {
          conversation.lastMessage = message;
        }
        
        if (message.type === 'received' && !message.is_read) {
          conversation.unreadCount++;
        }
      });

      const conversationList = Array.from(conversationMap.values())
        .sort((a, b) => new Date(b.lastMessage.created_at) - new Date(a.lastMessage.created_at));

      setConversations(conversationList);

      // Calculate total unread count
      const totalUnread = conversationList.reduce((sum, conv) => sum + conv.unreadCount, 0);
      updatePageTitle(totalUnread);
    } catch (err) {
      console.error('Failed to load conversations:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadConversationMessages = useCallback(async (partnerId) => {
    try {
      const [inboxResponse, sentResponse] = await Promise.all([
        apiService.getInboxMessages(),
        apiService.getSentMessages()
      ]);

      // Filter messages for this conversation
      const partnerMessages = [
        ...inboxResponse.messages
          .filter(m => m.sender.id === partnerId)
          .map(m => ({ ...m, type: 'received' })),
        ...sentResponse.messages
          .filter(m => m.recipient.id === partnerId)
          .map(m => ({ ...m, type: 'sent' }))
      ];

      // Sort by creation time
      partnerMessages.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
      
      // 🐛 DEBUG: Log message structure and ownership check
      console.log('🔍 Message structure check:', {
        user: user,
        currentUserId: user?.id,
        sampleMessage: partnerMessages[0],
        messageOwnershipCheck: partnerMessages.slice(0, 3).map(m => ({
          id: m.id,
          type: m.type,
          sender_id: m.sender_id,
          sender: m.sender,
          message: m.message?.substring(0, 30) + '...',
          isOwner: isMessageOwner(m, user),
          oldCheck: m.type === 'sent'
        }))
      });
      
      setMessages(partnerMessages);

      // Mark received messages as read
      const unreadMessages = partnerMessages.filter(m => m.type === 'received' && !m.is_read);
      for (const message of unreadMessages) {
        try {
          await apiService.markMessageAsRead(message.id);
        } catch (err) {
          console.error('Failed to mark message as read:', err);
        }
      }

      // Update conversation unread count
      setConversations(prev => prev.map(conv => 
        conv.userId === partnerId ? { ...conv, unreadCount: 0 } : conv
      ));

    } catch (err) {
      console.error('Failed to load conversation messages:', err);
    }
  }, []);

  // Separate effect to handle conversation message refreshing
  useEffect(() => {
    if (selectedConversation && conversations.length > 0) {
      const currentConversation = conversations.find(c => c.userId === selectedConversation.userId);
      if (currentConversation && currentConversation.unreadCount > 0) {
        loadConversationMessages(selectedConversation.userId);
      }
    }
  }, [conversations, selectedConversation?.userId, loadConversationMessages]);



  const loadAvailableUsers = async () => {
    try {
      const users = await apiService.getAvailableUsers();
      setAvailableUsers(users);
    } catch (err) {
      console.error('Failed to load available users:', err);
      setAvailableUsers([]);
    }
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!newMessage.trim() || !selectedConversation) return;

    setSending(true);
    try {
      const messageData = {
        recipient_nickname: selectedConversation.userInfo.nickname,
        subject: `Chat with ${selectedConversation.userInfo.nickname}`,
        message: newMessage,
        priority: 'NORMAL'
      };

      const sentMessage = await apiService.sendMessageByNickname(messageData);
      
      // Add message to current conversation
      setMessages(prev => [...prev, { ...sentMessage, type: 'sent' }]);
      setNewMessage('');

      // Update conversation list
      await loadConversations();
      
    } catch (err) {
      console.error('Failed to send message:', err);
      alert('Failed to send message. Please try again.');
    } finally {
      setSending(false);
    }
  };

  const startNewChat = async () => {
    if (!newChatUser) return;

    const selectedUser = availableUsers.find(u => u.nickname === newChatUser);
    if (!selectedUser) return;

    // Check if conversation already exists
    const existingConversation = conversations.find(c => c.userId === selectedUser.id);
    if (existingConversation) {
      setSelectedConversation(existingConversation);
      setShowNewChatModal(false);
      setNewChatUser('');
      return;
    }

    // Create new conversation
    const newConversation = {
      userId: selectedUser.id,
      userInfo: selectedUser,
      lastMessage: { created_at: new Date().toISOString(), message: '' },
      unreadCount: 0,
      messages: []
    };

    setSelectedConversation(newConversation);
    setMessages([]);
    setShowNewChatModal(false);
    setNewChatUser('');
  };

  const handleDeleteMessage = (message) => {
    setMessageToDelete(message);
    setShowDeleteModal(true);
  };

  const confirmDeleteMessage = async () => {
    if (!messageToDelete) return;

    setDeletingMessage(true);
    try {
      await apiService.deleteMessage(messageToDelete.id);
      
      // Remove message from local state immediately
      setMessages(prev => prev.filter(m => m.id !== messageToDelete.id));
      
      // Force reload conversations and current conversation to sync with server
      await loadConversations();
      if (selectedConversation) {
        await loadConversationMessages(selectedConversation.userId);
      }
      
      // Force refresh for auto-update mechanism
      await loadConversationsQuietly();
      
    } catch (err) {
      console.error('Failed to delete message:', err);
      alert('Failed to delete message. Please try again.');
    } finally {
      setDeletingMessage(false);
      setShowDeleteModal(false);
      setMessageToDelete(null);
    }
  };

  const cancelDeleteMessage = () => {
    setShowDeleteModal(false);
    setMessageToDelete(null);
  };

  const handleEditMessage = (message) => {
    setMessageToEdit(message);
    setEditedContent(message.message);
    setShowEditModal(true);
  };

  const confirmEditMessage = async () => {
    if (!messageToEdit || !editedContent.trim()) return;
    if (editedContent.trim() === messageToEdit.message) {
      // No changes made
      cancelEditMessage();
      return;
    }

    setEditingMessage(true);
    try {
      const updatedMessage = await apiService.editMessage(messageToEdit.id, editedContent.trim());
      
      // Update message in local state
      setMessages(prev => prev.map(m => 
        m.id === messageToEdit.id 
          ? { ...m, message: editedContent.trim(), edited_at: new Date().toISOString(), is_edited: true }
          : m
      ));
      
      // Force reload conversations and current conversation to sync with server
      await loadConversations();
      if (selectedConversation) {
        await loadConversationMessages(selectedConversation.userId);
      }
      
      // Force refresh for auto-update mechanism
      await loadConversationsQuietly();
      
    } catch (err) {
      console.error('Failed to edit message:', err);
      alert('Failed to edit message. Please try again.');
    } finally {
      setEditingMessage(false);
      setShowEditModal(false);
      setMessageToEdit(null);
      setEditedContent('');
    }
  };

  const cancelEditMessage = () => {
    setShowEditModal(false);
    setMessageToEdit(null);
    setEditedContent('');
  };

  const handleDeleteConversation = (conversation) => {
    setConversationToDelete(conversation);
    setShowDeleteConversationModal(true);
  };

  const confirmDeleteConversation = async () => {
    if (!conversationToDelete) return;

    try {
      setDeletingConversation(true);
      await apiService.deleteConversation(conversationToDelete.userId);
      
      // Remove conversation from list
      setConversations(prev => prev.filter(conv => conv.userId !== conversationToDelete.userId));
      
      // Clear selected conversation if it was the deleted one
      if (selectedConversation?.userId === conversationToDelete.userId) {
        setSelectedConversation(null);
        setMessages([]);
      }
      
    } catch (err) {
      console.error('Failed to delete conversation:', err);
      alert('Failed to delete conversation. Please try again.');
    } finally {
      setDeletingConversation(false);
      setShowDeleteConversationModal(false);
      setConversationToDelete(null);
    }
  };

  const cancelDeleteConversation = () => {
    setShowDeleteConversationModal(false);
    setConversationToDelete(null);
  };

  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffHours = Math.abs(now - date) / 36e5;
    
    if (diffHours < 24) {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
    return date.toLocaleDateString();
  };

  const getMessagePreview = (message) => {
    if (!message || !message.message) return 'No messages yet...';
    return message.message.length > 50 
      ? message.message.substring(0, 50) + '...'
      : message.message;
  };

  if (loading) {
    return (
      <div className="student-messages">
        <div className="loading-state">
          <div className="loading-spinner"></div>
          <p>Loading conversations...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="student-messages chat-layout">
      <div className={`chat-header ${hasNewMessages ? 'has-new-messages' : ''}`}>
        <div>
          <button onClick={() => navigate('/student/dashboard')} className="back-btn">
            ← Dashboard
          </button>
          <h1>💬 Chat</h1>
          <p>Chat with your instructors and classmates</p>
        </div>
        <div className="header-actions">
          <button className="btn-primary new-chat-btn" onClick={() => setShowNewChatModal(true)}>
            ✏️ New Chat
          </button>
        </div>
      </div>

      <div className="chat-container">
        {/* Conversations Sidebar */}
        <div className="conversations-sidebar">
          <div className="conversations-header">
            <h3>Conversations</h3>
            <span className="conversations-count">({conversations.length})</span>
          </div>
          
          <div className="conversations-list">
            {conversations.length === 0 ? (
              <div className="empty-conversations">
                <p>No conversations yet</p>
                <button className="btn-secondary" onClick={() => setShowNewChatModal(true)}>
                  Start your first chat
                </button>
              </div>
            ) : (
              conversations.map(conversation => (
                <div
                  key={conversation.userId}
                  className={`conversation-item ${selectedConversation?.userId === conversation.userId ? 'active' : ''}`}
                >
                  <div className="conversation-content" onClick={() => setSelectedConversation(conversation)}>
                    <div className="conversation-avatar">
                      {conversation.userInfo.nickname?.[0]?.toUpperCase() || '👤'}
                    </div>
                    <div className="conversation-info">
                      <div className="conversation-name">
                        {conversation.userInfo.nickname || conversation.userInfo.name}
                        {conversation.unreadCount > 0 && (
                          <span className="unread-badge">{conversation.unreadCount}</span>
                        )}
                      </div>
                      <div className="conversation-preview">
                        {getMessagePreview(conversation.lastMessage)}
                      </div>
                      <div className="conversation-time">
                        {formatTime(conversation.lastMessage.created_at)}
                      </div>
                    </div>
                  </div>
                  <button 
                    className="delete-conversation-btn"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteConversation(conversation);
                    }}
                    title="Delete conversation"
                  >
                    🗑️
                  </button>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Chat Area */}
        <div className="chat-area">
          {selectedConversation ? (
            <>
              {/* Chat Header */}
              <div className="chat-conversation-header">
                <div className="chat-partner-info">
                  <div className="chat-partner-avatar">
                    {selectedConversation.userInfo.nickname?.[0]?.toUpperCase() || '👤'}
                  </div>
                  <div>
                    <h3>{selectedConversation.userInfo.nickname || selectedConversation.userInfo.name}</h3>
                    <p>{selectedConversation.userInfo.email}</p>
                  </div>
                </div>
              </div>

              {/* Messages Area */}
              <div className="messages-area">
                {messages.length === 0 ? (
                  <div className="empty-messages">
                    <div className="empty-icon">💬</div>
                    <h3>Start the conversation</h3>
                    <p>Send a message to begin chatting with {selectedConversation.userInfo.nickname}</p>
                  </div>
                ) : (
                  messages.map(message => (
                    <div
                      key={message.id}
                      className={`message-bubble ${message.type === 'sent' ? 'sent' : 'received'}`}
                    >
                      <div className="message-content">
                        <span className="message-text">
                          {message.message}
                          {message.is_edited && <span className="edited-indicator"> (edited)</span>}
                        </span>
                        <div className="message-actions">
                          {isMessageOwner(message, user) && (
                            <button 
                              className="edit-message-btn"
                              onClick={() => handleEditMessage(message)}
                              title="Edit message"
                            >
                              ✏️
                            </button>
                          )}
                          <button 
                            className="delete-message-btn"
                            onClick={() => handleDeleteMessage(message)}
                            title="Delete message"
                          >
                            🗑️
                          </button>
                        </div>
                      </div>
                      <div className="message-time">
                        {formatTime(message.created_at)}
                        {message.type === 'sent' && (
                          <span className="message-status">
                            {message.is_read ? '✓✓' : '✓'}
                          </span>
                        )}
                      </div>
                    </div>
                  ))
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* Message Input */}
              <div className="message-input-area">
                <form onSubmit={handleSendMessage} className="message-form">
                  <input
                    type="text"
                    value={newMessage}
                    onChange={(e) => setNewMessage(e.target.value)}
                    placeholder={`Message ${selectedConversation.userInfo.nickname}...`}
                    className="message-input"
                    disabled={sending}
                  />
                  <button
                    type="submit"
                    className="send-btn"
                    disabled={!newMessage.trim() || sending}
                  >
                    {sending ? '⏳' : '➤'}
                  </button>
                </form>
              </div>
            </>
          ) : (
            <div className="no-conversation-selected">
              <div className="empty-icon">💬</div>
              <h3>Select a conversation</h3>
              <p>Choose a conversation from the list or start a new chat</p>
              <button className="btn-primary" onClick={() => setShowNewChatModal(true)}>
                Start New Chat
              </button>
            </div>
          )}
        </div>
      </div>

      {/* New Chat Modal */}
      {showNewChatModal && (
        <div className="modal-overlay" onClick={() => setShowNewChatModal(false)}>
          <div className="modal new-chat-modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Start New Chat</h3>
              <button className="close-btn" onClick={() => setShowNewChatModal(false)}>×</button>
            </div>
            
            <div className="modal-body">
              <div className="form-group">
                <label>Select person to chat with</label>
                <select
                  value={newChatUser}
                  onChange={(e) => setNewChatUser(e.target.value)}
                  className="user-select"
                >
                  <option value="">Choose someone...</option>
                  {availableUsers.map(user => (
                    <option key={user.id} value={user.nickname}>
                      {user.nickname} ({user.name})
                    </option>
                  ))}
                </select>
              </div>

              <div className="modal-actions">
                <button 
                  type="button" 
                  className="btn-secondary"
                  onClick={() => setShowNewChatModal(false)}
                >
                  Cancel
                </button>
                <button 
                  type="button" 
                  className="btn-primary"
                  onClick={startNewChat}
                  disabled={!newChatUser}
                >
                  Start Chat
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Delete Message Confirmation Modal */}
      {showDeleteModal && (
        <div className="modal-overlay" onClick={cancelDeleteMessage}>
          <div className="modal delete-modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Delete Message</h3>
              <button className="close-btn" onClick={cancelDeleteMessage}>×</button>
            </div>
            
            <div className="modal-body">
              <p>Are you sure you want to delete this message?</p>
              <div className="message-preview">
                <em>"{messageToDelete?.message}"</em>
              </div>
              <p className="warning-text">⚠️ This action cannot be undone.</p>
            </div>

            <div className="modal-actions">
              <button 
                type="button" 
                className="btn-secondary"
                onClick={cancelDeleteMessage}
                disabled={deletingMessage}
              >
                Cancel
              </button>
              <button 
                type="button" 
                className="btn-danger"
                onClick={confirmDeleteMessage}
                disabled={deletingMessage}
              >
                {deletingMessage ? 'Deleting...' : 'Delete Message'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Message Modal */}
      {showEditModal && (
        <div className="modal-overlay" onClick={cancelEditMessage}>
          <div className="modal edit-modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Edit Message</h3>
              <button className="close-btn" onClick={cancelEditMessage}>×</button>
            </div>
            
            <div className="modal-body">
              <div className="form-group">
                <label>Edit your message</label>
                <textarea
                  value={editedContent}
                  onChange={(e) => setEditedContent(e.target.value)}
                  className="edit-textarea"
                  rows={4}
                  placeholder="Type your message..."
                  disabled={editingMessage}
                />
              </div>
              <div className="character-count">
                {editedContent.length}/500 characters
              </div>
            </div>

            <div className="modal-actions">
              <button 
                type="button" 
                className="btn-secondary"
                onClick={cancelEditMessage}
                disabled={editingMessage}
              >
                Cancel
              </button>
              <button 
                type="button" 
                className="btn-primary"
                onClick={confirmEditMessage}
                disabled={editingMessage || !editedContent.trim() || editedContent.trim() === messageToEdit?.message}
              >
                {editingMessage ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Conversation Confirmation Modal */}
      {showDeleteConversationModal && (
        <div className="modal-overlay" onClick={cancelDeleteConversation}>
          <div className="modal delete-modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Delete Conversation</h3>
              <button className="close-btn" onClick={cancelDeleteConversation}>×</button>
            </div>
            
            <div className="modal-body">
              <p>Are you sure you want to delete the entire conversation with:</p>
              <div className="conversation-preview">
                <strong>{conversationToDelete?.userInfo.nickname || conversationToDelete?.userInfo.name}</strong>
              </div>
              <p className="warning-text">⚠️ This will delete ALL messages in this conversation and cannot be undone.</p>
            </div>

            <div className="modal-actions">
              <button 
                type="button" 
                className="btn-secondary"
                onClick={cancelDeleteConversation}
                disabled={deletingConversation}
              >
                Cancel
              </button>
              <button 
                type="button" 
                className="btn-danger"
                onClick={confirmDeleteConversation}
                disabled={deletingConversation}
              >
                {deletingConversation ? 'Deleting...' : 'Delete Conversation'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default StudentMessages;