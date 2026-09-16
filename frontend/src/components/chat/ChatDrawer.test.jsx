import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ChatDrawer from './ChatDrawer';
import { chatService } from '../../api/chatService';

vi.mock('../../api/chatService', () => ({
  chatService: {
    getContacts: vi.fn(),
    getConversation: vi.fn(),
    sendMessage: vi.fn(),
    markRead: vi.fn(),
  },
}));

vi.mock('../../context/AuthContext', () => ({
  useAuth: () => ({
    user: { id: 1, name: 'Alice Patient', role: 'PATIENT' },
    isAuthenticated: true,
  }),
}));

describe('ChatDrawer Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders chat header, fetches conversation, and renders messages in order', async () => {
    vi.mocked(chatService.getContacts).mockResolvedValue([
      {
        user_id: 2,
        name: 'Dr. Bob Caregiver',
        employee_id: 'CG000002',
        role: 'CAREGIVER',
        email: 'bob@caregiver.test',
        unread_count: 0,
      },
    ]);

    vi.mocked(chatService.getConversation).mockResolvedValue([
      {
        id: 101,
        sender_id: 1,
        sender_name: 'Alice Patient',
        sender_role: 'PATIENT',
        sender_employee_id: 'PT000001',
        recipient_id: 2,
        recipient_name: 'Dr. Bob Caregiver',
        recipient_role: 'CAREGIVER',
        recipient_employee_id: 'CG000002',
        message: 'Hello, I have a question about my medication.',
        is_read: true,
        created_at: '2026-08-21T10:00:00Z',
      },
      {
        id: 102,
        sender_id: 2,
        sender_name: 'Dr. Bob Caregiver',
        sender_role: 'CAREGIVER',
        sender_employee_id: 'CG000002',
        recipient_id: 1,
        recipient_name: 'Alice Patient',
        recipient_role: 'PATIENT',
        recipient_employee_id: 'PT000001',
        message: 'Sure, I am here to help you.',
        is_read: true,
        created_at: '2026-08-21T10:02:00Z',
      },
    ]);

    render(
      <ChatDrawer
        isOpen={true}
        onClose={vi.fn()}
        targetUser={{ id: 2, name: 'Dr. Bob Caregiver' }}
        currentUser={{ id: 1, name: 'Alice Patient', role: 'PATIENT' }}
      />
    );

    await waitFor(
      () => {
        expect(screen.getByText('Care Communication Chat')).toBeInTheDocument();
        expect(screen.getByText('LIVE CHAT')).toBeInTheDocument();
        expect(screen.getAllByText('Dr. Bob Caregiver').length).toBeGreaterThan(0);
        expect(screen.getByText('Hello, I have a question about my medication.')).toBeInTheDocument();
        expect(screen.getByText('Sure, I am here to help you.')).toBeInTheDocument();
      },
      { timeout: 4000 }
    );
  });

  it('allows sending a message, submits to chatService, and updates message list', async () => {
    vi.mocked(chatService.getContacts).mockResolvedValue([
      {
        user_id: 2,
        name: 'Dr. Bob Caregiver',
        role: 'CAREGIVER',
        unread_count: 0,
      },
    ]);
    vi.mocked(chatService.getConversation).mockResolvedValue([]);
    vi.mocked(chatService.sendMessage).mockResolvedValue({
      id: 103,
      sender_id: 1,
      sender_name: 'Alice Patient',
      sender_role: 'PATIENT',
      recipient_id: 2,
      recipient_name: 'Dr. Bob Caregiver',
      recipient_role: 'CAREGIVER',
      message: 'I took my morning pills.',
      is_read: false,
      created_at: '2026-08-21T10:05:00Z',
    });

    render(
      <ChatDrawer
        isOpen={true}
        onClose={vi.fn()}
        targetUser={{ id: 2, name: 'Dr. Bob Caregiver' }}
        currentUser={{ id: 1, name: 'Alice Patient', role: 'PATIENT' }}
      />
    );

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Message Dr\. Bob Caregiver\.\.\./i)).toBeInTheDocument();
    });

    const input = screen.getByPlaceholderText(/Message Dr\. Bob Caregiver\.\.\./i);
    const sendButton = screen.getByRole('button', { name: /Send/i });

    fireEvent.change(input, { target: { value: 'I took my morning pills.' } });
    fireEvent.click(sendButton);

    await waitFor(() => {
      expect(chatService.sendMessage).toHaveBeenCalledWith(2, 'I took my morning pills.');
      expect(screen.getByText('I took my morning pills.')).toBeInTheDocument();
    });
  });

  it('allows sender to delete their message via confirmation modal', async () => {
    vi.mocked(chatService.getContacts).mockResolvedValue([
      {
        user_id: 2,
        name: 'Dr. Bob Caregiver',
        role: 'CAREGIVER',
        unread_count: 0,
      },
    ]);
    vi.mocked(chatService.getConversation).mockResolvedValue([
      {
        id: 201,
        sender_id: 1, // Mine
        sender_name: 'Alice Patient',
        sender_role: 'PATIENT',
        recipient_id: 2,
        recipient_name: 'Dr. Bob Caregiver',
        message: 'Message to be deleted',
        is_deleted: false,
        created_at: '2026-08-21T10:00:00Z',
      },
    ]);
    vi.mocked(chatService.deleteMessage = vi.fn()).mockResolvedValue({
      success: true,
      message: 'Message deleted successfully.',
    });

    render(
      <ChatDrawer
        isOpen={true}
        onClose={vi.fn()}
        targetUser={{ id: 2, name: 'Dr. Bob Caregiver' }}
        currentUser={{ id: 1, name: 'Alice Patient', role: 'PATIENT' }}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Message to be deleted')).toBeInTheDocument();
    });

    const deleteBtn = screen.getByRole('button', { name: /Delete message/i });
    fireEvent.click(deleteBtn);

    // Modal appears
    expect(screen.getByText('Delete this message?')).toBeInTheDocument();
    const confirmBtn = screen.getAllByRole('button', { name: /Delete Message/i })[1];
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(chatService.deleteMessage).toHaveBeenCalledWith(201);
      expect(screen.getByText('This message was deleted.')).toBeInTheDocument();
    });
  });

  it('allows clearing conversation via confirmation modal without affecting records', async () => {
    vi.mocked(chatService.getContacts).mockResolvedValue([
      {
        user_id: 2,
        name: 'Dr. Bob Caregiver',
        role: 'CAREGIVER',
        unread_count: 0,
      },
    ]);
    vi.mocked(chatService.getConversation).mockResolvedValue([
      {
        id: 301,
        sender_id: 1,
        sender_name: 'Alice Patient',
        recipient_id: 2,
        message: 'Old chat message',
        created_at: '2026-08-21T10:00:00Z',
      },
    ]);
    vi.mocked(chatService.deleteConversation = vi.fn()).mockResolvedValue({
      success: true,
      message: 'Conversation cleared successfully.',
    });

    render(
      <ChatDrawer
        isOpen={true}
        onClose={vi.fn()}
        targetUser={{ id: 2, name: 'Dr. Bob Caregiver' }}
        currentUser={{ id: 1, name: 'Alice Patient', role: 'PATIENT' }}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Old chat message')).toBeInTheDocument();
    });

    const deleteChatBtn = screen.getByRole('button', { name: /Delete Conversation/i });
    fireEvent.click(deleteChatBtn);

    expect(screen.getByText('Delete this conversation?')).toBeInTheDocument();
    expect(
      screen.getByText('Your medication and patient records will not be affected.')
    ).toBeInTheDocument();

    const confirmBtn = screen.getAllByRole('button', { name: /Delete Conversation/i })[1];
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(chatService.deleteConversation).toHaveBeenCalledWith(2);
      expect(screen.queryByText('Old chat message')).not.toBeInTheDocument();
    });
  });
});

