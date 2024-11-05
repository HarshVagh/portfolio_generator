import React, { useState, useEffect, useContext, useRef } from "react";
import {
  Button,
  Label,
  Textarea,
  TextInput,
  Avatar,
  Badge,
  Modal,
  FileInput,
  Spinner,
} from "flowbite-react";
import placeholder from "../assets/placeholder.png";
import SendIcon from "../assets/circle-chevron-right-solid.svg";
import MessageIcon from "../assets/message-circle.svg";
import AxiosInstance from "../auth/AxiosInstance";
import DOMPurify from "dompurify";
import { UserContext } from "../auth/UserContext";
import { useNavigate } from "react-router-dom";

export default function Chat() {
  const [showCreatePopup, setShowCreatePopup] = useState(false);
  const [chats, setChats] = useState([]);
  const [currentChat, setCurrentChat] = useState({});
  const [form, setForm] = useState({
    title: "",
    resume: null,
    additionalDescription: "",
  });
  const [formErrors, setFormErrors] = useState({});
  const [newMessage, setNewMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const { setUser } = useContext(UserContext);
  const messagesEndRef = useRef(null); // Create a ref for the end of the messages
  const navigate = useNavigate();

  useEffect(() => {
    fetchChats();
  }, []);

  useEffect(() => {
    if (currentChat.id) {
      // Poll for new messages every 5 seconds
      const interval = setInterval(() => {
        const messages = currentChat.messages || [];
        const isNewChat = messages.length === 0;
        const isNewUserMessage =
          messages.length > 0 && messages[messages.length - 1].sender === "user";
        if (isNewChat || isNewUserMessage) {
          fetchMessages(currentChat.id);
        }
      }, 5000);

      // Cleanup interval on component unmount or when chat changes
      return () => clearInterval(interval);
    }
  }, [currentChat.id, currentChat.messages]);

  // Scroll to the bottom of the chat when messages change
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [currentChat.messages]);

  const fetchChats = async () => {
    try {
      setLoading(true); // Start loader
      const response = await AxiosInstance.get("/api/chats");
      setChats(response.data.chats);
      setLoading(false); // Stop loader
    } catch (error) {
      setError("Error fetching chats. Please try again later."); // Set error message
      setLoading(false); // Stop loader
    }
  };

  const handleInputChange = (e) => {
    const { id, value } = e.target;
    setForm({ ...form, [id]: value });
  };

  const handleFileChange = (e) => {
    setForm({ ...form, resume: e.target.files[0] });
  };

  const validateForm = () => {
    const errors = {};
    if (!form.title) errors.title = "Title is required.";
    if (!form.resume) errors.resume = "Resume file is required.";
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleCreateChat = async (e) => {
    e.preventDefault();
    if (!validateForm()) return;

    setShowCreatePopup(false);

    const formData = new FormData();
    formData.append("title", form.title);
    formData.append("resume", form.resume);
    formData.append("additionalDescription", form.additionalDescription);

    try {
      setLoading(true); // Start loader
      const response = await AxiosInstance.post("/api/chats", formData);
      const newChat = response.data.chat;

      // Set the new chat as the current chat
      setCurrentChat({ ...newChat, messages: [] });
      setChats([...chats, newChat]);
      setForm({ title: "", resume: null, additionalDescription: "" });
      setFormErrors({});
      setError(null); // Clear any previous errors

      // Fetch initial messages for the new chat
      fetchMessages(newChat.id);
      setLoading(false); // Stop loader
    } catch (error) {
      setError("Error creating chat. Please try again later."); // Set error message
      setLoading(false); // Stop loader
    }
  };

  const handleSelectChat = (chat) => {
    // Join the new chat room
    setCurrentChat({ ...chat, messages: [] });
    fetchMessages(chat.id);
  };

  const fetchMessages = async (chatId) => {
    try {
      setLoading(true); // Start loader
      const response = await AxiosInstance.get(`/api/chats/${chatId}/messages`);
      const messages = response.data.messages;

      setCurrentChat((prevChat) => ({
        ...prevChat,
        messages: messages,
      }));

      setLoading(false); // Stop loader

      // Check if the last message is from the user, and then poll for bot response
      if (
        messages.length > 0 &&
        messages[messages.length - 1].sender === "user"
      ) {
        // Optionally handle logic if the last message was from the user
        // Maybe trigger another fetch after a delay if necessary
      }
    } catch (error) {
      setError("Error fetching messages. Please try again later."); // Set error message
      setLoading(false); // Stop loader
    }
  };

  const handleSendMessage = async () => {
    if (newMessage?.trim() === "") return;

    try {
      setLoading(true); // Start loader
      await AxiosInstance.post(`/api/chats/${currentChat.id}/messages`, {
        chat_id: currentChat.id,
        message: newMessage,
      });

      setCurrentChat((prevChat) => ({
        ...prevChat,
        messages: [
          ...prevChat.messages,
          {
            sender: "user",
            text: newMessage,
            time: new Date().toLocaleTimeString(),
          },
        ],
      }));

      setNewMessage("");
      setError(null); // Clear any previous errors

      // Immediately fetch messages after sending to update the chat
      fetchMessages(currentChat.id);
      setLoading(false); // Stop loader
    } catch (error) {
      setError("Error sending message. Please try again later."); // Set error message
      setLoading(false); // Stop loader
    }
  };

  const handleDeploy = async () => {
    try {
      setLoading(true); // Start loader

      const botMessages = currentChat.messages.filter(
        (msg) => msg.sender === "bot"
      );

      if (botMessages.length === 0) {
        setError("No bot messages to deploy.");
        setLoading(false);
        return;
      }

      const lastBotMessage = botMessages[botMessages.length - 1].text;
      const cleanHTML = cleanHTMLString(lastBotMessage);

      const response = await AxiosInstance.post(`/api/deploy`, {
        chat_id: currentChat.id,
        content: cleanHTML,
      });

      const pageUrl = response.data.page_url;

      setCurrentChat((prevChat) => ({
        ...prevChat,
        page_url: pageUrl,
      }));

      setError(null); // Clear any previous errors
      setLoading(false); // Stop loader
    } catch (error) {
      setError("Error deploying page. Please try again later."); // Set error message
      setLoading(false); // Stop loader
    }
  };

  const handleLogout = async () => {
    setUser(null)
    localStorage.removeItem('authToken');
    navigate('/login');
  };

  const cleanHTMLString = (str) => {
    if (str) {
      let cleanedStr = str.trim();

      if (cleanedStr.startsWith("```html")) {
        cleanedStr = cleanedStr.slice(7);
      }

      if (cleanedStr.endsWith("```")) {
        cleanedStr = cleanedStr.slice(0, -3);
      }

      return cleanedStr.trim();
    }
    return str;
  };

  const isHTML = (str) => {
    const cleanedHTML = cleanHTMLString(str);
    const sanitizedHTML = DOMPurify.sanitize(cleanedHTML);
    const doc = new DOMParser().parseFromString(sanitizedHTML, "text/html");
    return Array.from(doc.body.childNodes).some((node) => node.nodeType === 1);
  };

  const getDate = (dateString) => {
    if (dateString) {
      const dateElements = dateString.split(" ");
      if (dateElements.length >= 4) {
        return dateElements[4].slice(0, 5);
      }
    }
    return "";
  };

  return (
    <div className="grid min-h-screen w-full grid-cols-[300px_1fr] bg-background">
      {loading && (
        <div className="fixed inset-0 flex items-center justify-center bg-gray-800 bg-opacity-50 z-50">
          <Spinner size="lg" color="purple" aria-label="Loading..." />
        </div>
      )}
      <Modal
        show={showCreatePopup}
        size="2xl"
        onClose={() => setShowCreatePopup(false)}
        popup
      >
        <Modal.Header className="pl-6">Create New Chat</Modal.Header>
        <hr />
        <Modal.Body className="mt-2">
          {error && (
            <div className="text-red-500 text-center mb-4">{error}</div>
          )}
          <form className="space-y-4" onSubmit={handleCreateChat}>
            <div className="space-y-2">
              <Label htmlFor="title">Title</Label>
              <TextInput
                id="title"
                placeholder="Enter title"
                color="purple"
                onChange={handleInputChange}
                value={form.title}
              />
              {formErrors.title && (
                <div className="text-red-500">{formErrors.title}</div>
              )}
            </div>
            <div className="space-y-2 p-0">
              <Label htmlFor="resume">Resume</Label>
              <FileInput
                id="resume"
                type="file"
                color="purple"
                onChange={handleFileChange}
              />
              {formErrors.resume && (
                <div className="text-red-500">{formErrors.resume}</div>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="additionalDescription">
                Additional Description
              </Label>
              <Textarea
                id="additionalDescription"
                placeholder="Enter additional description"
                color="purple"
                className="min-h-[80px]"
                onChange={handleInputChange}
                value={form.additionalDescription}
              />
            </div>
            <div className="flex mt-4 justify-end gap-4">
              <Button type="submit" color="purple">
                Create Chat
              </Button>
              <Button color="failure" onClick={() => setShowCreatePopup(false)}>
                Cancel
              </Button>
            </div>
          </form>
        </Modal.Body>
      </Modal>
      {/* Left section - Chat List */}
      <div className="border-r bg-muted/40 flex flex-col h-full">
        <div className="flex h-[60px] items-center border-b px-4 sticky top-0 bg-white z-50">
          <div className="flex items-center gap-2 font-semibold">
            <img src={MessageIcon} className="h-6 w-6" alt="Message Icon" />
            <span>Chats</span>
          </div>
          <div className="ml-auto flex items-center gap-2">
            <Button
              className="px-4"
              color="purple"
              size="sm"
              onClick={() => setShowCreatePopup(true)}
            >
              Create
            </Button>
          </div>
        </div>
        <div className="flex-1 overflow-auto">
          <div className="grid gap-2 p-4">
            {chats.map((chat) => (
              <div
                key={chat.id}
                onClick={() => handleSelectChat(chat)}
                className={`${
                  currentChat && currentChat.id === chat.id
                    ? "bg-purple-600 text-white"
                    : "bg-muted"
                } flex items-center gap-3 rounded-md p-2 transition-colors hover:bg-muted/50 border cursor-pointer`}
              >
                <Avatar
                  src={placeholder}
                  placeholderInitials={chat.title[0]}
                  rounded
                ></Avatar>
                <div className="flex-1 overflow-hidden">
                  <div className="font-medium">{chat.title}</div>
                  <div className="text-sm text-muted-foreground line-clamp-1">
                    {isHTML(chat?.lastMessage)
                      ? "Your portfolio page"
                      : chat.lastMessage?.slice(0, 20)}
                  </div>
                </div>
                <div className="text-xs text-muted-foreground">
                  {getDate(chat.lastUpdated)}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
      {/* Right section - Chat Messages */}
      <div className="flex flex-col h-full">
        {currentChat && currentChat.messages ? (
          <>
            <div className="flex h-[60px] justify-between items-center border-b bg-muted/40 px-4 sticky top-0 bg-white z-50">
              <div className="flex items-center gap-3">
                <Avatar
                  className="h-10 w-10 border"
                  src={placeholder}
                  placeholderInitials="AC"
                ></Avatar>
                <div>
                  <div className="font-medium">{currentChat.title}</div>
                  <div className="text-sm text-muted-foreground">Online</div>
                </div>
              </div>
              <div className="flex gap-4">
                {currentChat.page_url ? 
                  <a href={currentChat.page_url} target="_blank" rel="noreferrer">
                    <Button className="px-4" color="purple" size="sm">Open Portfolio page</Button>
                  </a> : 
                  <Button className="px-4" color="purple" size="sm" onClick={handleDeploy}>Deploy</Button>
                }
                <Button className="px-4" color="purple" size="sm" onClick={handleLogout}>Logout</Button>
              </div>
              
            </div>
            <div className="flex-1 overflow-auto p-4">
              <div className="grid gap-4">
                {currentChat.messages?.map((msg, index) => (
                  <div
                    key={index}
                    className={`flex items-start gap-3 ${
                      msg.sender === "bot" ? "" : "justify-end"
                    }`}
                  >
                    <Avatar
                      src={placeholder}
                      rounded
                      placeholderInitials="AC"
                    ></Avatar>
                    <div>
                      {isHTML(msg.text) ? (
                        <iframe
                          srcDoc={cleanHTMLString(msg.text)}
                          title={`message-${index}`}
                          className="w-[940px] h-[560px] border rounded"
                        />
                      ) : (
                        <Badge
                          color="purple"
                          size="md"
                          className="bg-purple-600 text-white rounded px-4 py-1"
                        >
                          {msg.text}
                        </Badge>
                      )}
                      <div className="mt-2 flex items-center gap-2">
                        <div className="text-xs text-muted-foreground">
                          {msg.time}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
                <div ref={messagesEndRef} /> {/* Add this element */}
              </div>
            </div>
            {(!currentChat?.page_url || currentChat?.page_url?.length === 0) &&
            <div className="sticky bottom-0 bg-background px-4 py-2 mx-12">
              <div className="relative">
                <TextInput
                  className="py-2"
                  placeholder="Type your message..."
                  value={newMessage}
                  onChange={(e) => setNewMessage(e.target.value)}
                />
                <button
                  type="submit"
                  onClick={handleSendMessage}
                  className="absolute right-3 top-3"
                >
                  <img src={SendIcon} className="h-6 w-6 mt-1" alt="Send Icon" />
                  <span className="sr-only">Send</span>
                </button>
              </div>
            </div>}
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <h2 className="text-2xl font-semibold">
                Select a chat to start messaging
              </h2>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
